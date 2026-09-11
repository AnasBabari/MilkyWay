"""Close the old campaign, freeze verified search variants, and run gated screens.

This local tournament driver does not train, promote, upload or build a ZIP.
It preserves immutable runs and explicitly reports candidates needing further work.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from tools.audit_recorded_screen import audit  # noqa: E402

PYTHON = ROOT / ".venv/Scripts/python.exe"
STATE = HERE / "candidate_tournament_01.json"
# User revision 2026-09-08 ~16:38: development games sped up to target ~30 seconds
# wall time each, moves played very quickly. Clock scaled to 1/5 of the previous
# 60s+0.5s development protocol. The 60s partial screen was preserved separately
# and is never pooled with fast-clock games. Final independent confirmation
# remains 120s+0.5s per opponent per the standing protocol.
BASE_MS = 12000
INCREMENT_MS = 100
CLOCK_TAG = "12s_50g"
# Concurrency revision: per-game wall time has a ~40s structural floor (two fresh
# runner processes per game, each paying Numba compilation; the harness sandbox
# points NUMBA_CACHE_DIR at a per-game scratch dir wiped between games, so
# compilation cannot be cached across games). To meet the user's ~30s-per-game
# speed target, three games run concurrently, yielding one completed game every
# ~25 seconds on average. Games remain independent; clocks, bank, seed and
# pairing are unchanged, so concurrent games are pooled with the same screen.
WORKERS = 3
# Goal revision 2026-09-08 ~17:05: user lowered the promotion bar. The live gate
# is no longer 70% actual wins; the minimum acceptable result is a candidate
# that beats the exact live silky_snow by at least 10 percentage points of
# score (>=0.55) while remaining superior to the three compiled challengers
# (>=0.55 score each). The live-screen futility stop now fires when reaching
# 27.5/50 points becomes mathematically impossible.
LIVE_GATE_SCORE = 0.55
LIVE_REQUIRED_POINTS = 27.5


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save(path: Path, data: Any) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, indent=2) + "\n")
    temporary.replace(path)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def processes() -> list[dict[str, Any]]:
    text = subprocess.check_output(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            "@(Get-CimInstance Win32_Process | Where-Object {$_.Name -match 'python'} "
            "| Select-Object ProcessId,ParentProcessId,CommandLine) | ConvertTo-Json -Compress",
        ],
        text=True,
    )
    data = json.loads(text) if text.strip() else []
    return data if isinstance(data, list) else [data]


def wait_and_close_old() -> None:
    closeout = ROOT / "experiments/compact_cycle_01/campaign_closeout_60s_01.json"
    if closeout.exists():
        print("Old campaign closeout already written; skipping wait_and_close_old.", flush=True)
        return
    parents = [
        ROOT / f"experiments/{name}_parent_60s_50g"
        for name in ("compiled_ordered_01", "compiled_sf7_rl_01")
    ]
    deadline = time.monotonic() + 7200
    print("Waiting for the two existing parent diagnostics to finish.", flush=True)
    while not all((p / "report_50.json").exists() for p in parents):
        assert time.monotonic() < deadline, "Old campaign wait exceeded two hours; inspect state"
        current = {p["ProcessId"]: p for p in processes()}
        for parent in parents:
            if (parent / "report_50.json").exists():
                continue
            owner = int((parent / "writer.lock").read_text())
            proc = current.get(owner)
            assert proc and parent.name in proc["CommandLine"], (
                parent,
                "Writer missing/mismatched",
            )
        time.sleep(20)
    campaign = load(ROOT / "experiments/compact_cycle_01/campaign_60s_50g.json")
    rows = []
    for spec in campaign["runs"]:
        path = ROOT / spec["out"]
        report = audit(path)
        complete = (path / "report_50.json").exists()
        decision = load(path / "futility_decision.json") if not complete else None
        if complete:
            assert (
                report["game_count"] == 50
                and not load(path / "report_50.json")["failed_terminations"]
            )
            assert len(load(path / "pairs.json")) == 25
        pairs = load(path / "pairs.json")
        committed = {p["pos_id"] for p in pairs}
        rows.append(
            {
                "run": str(path.relative_to(ROOT)),
                "complete_50": complete,
                "candidate": Path(spec["agent"]).name,
                "opponent": Path(spec["opponent"]).name,
                "planned_games": 50,
                "committed_pairs": len(pairs),
                "audit": report,
                "stop_decision": decision,
                "orphan_records": [
                    g["file"] for g in report["games"] if g["position_id"] not in committed
                ],
                "manifest_sha256": sha(path / "manifest.json"),
                "runtime_manifests": load(path / "manifest.json"),
            }
        )
    closeout = {
        "created_utc": datetime.now(UTC).isoformat(),
        "runs": rows,
        "status": "closed; generation rejected; no promotion",
        "gate_revision": "SF7 now diagnostic; all three live screens also fail "
        "the revised 70% actual-win gate.",
    }
    output = ROOT / "experiments/compact_cycle_01"
    assert not (output / "campaign_closeout_60s_01.json").exists()
    save(output / "campaign_closeout_60s_01.json", closeout)
    lines = [
        "# Candidate campaign closeout: rejected",
        "",
        "All eight runs are terminal. Stopped samples are truncated; no ZIP is qualified.",
        "",
        "| Candidate | Opponent | Games | W/D/L | Points | Actual wins | Status |",
        "|---|---|---:|---|---:|---:|---|",
    ]
    for row in rows:
        report = row["audit"]
        wdl = report["all_recorded_wdl"]
        w, d, losses = (wdl.get(k, 0) for k in ("win", "draw", "loss"))
        lines.append(
            f"| {row['candidate']} | {row['opponent']} | {report['game_count']} | "
            f"{w}/{d}/{losses} | {w + d / 2:g} | {w / report['game_count']:.1%} | "
            f"{'Complete' if row['complete_50'] else 'Futility stop'} |"
        )
    lines += [
        "",
        "All saved PGNs, clocks and frozen hashes passed the record auditor. "
        "Full provenance, terminations, failure checks and orphan records "
        "are in the JSON closeout.",
    ]
    (output / "CAMPAIGN_REJECTION_60S.md").write_text("\n".join(lines) + "\n")
    print("Closed all eight old comparisons; no old candidate qualifies.", flush=True)


def freeze_candidates() -> dict[str, Path]:
    baseline = ROOT / "experiments/compiled_ordered_01"
    parent = load(baseline / "manifest.json")
    parent_result = audit(ROOT / "experiments/compiled_ordered_01_parent_60s_50g")
    assert parent_result["game_count"] == 50 and parent_result["all_recorded_score"] > 0.5
    for name, digest in parent["sha256"].items():
        assert sha(baseline / name) == digest
    manifest = load(HERE / "BASELINE_MANIFEST.json")
    if manifest.get("status") != "selected and frozen":
        manifest.update(
            {
                "status": "selected and frozen",
                "selected_candidate": str(baseline),
                "selected_sha256": parent["sha256"],
                "selection_evidence": parent_result,
                "reason": "Completed direct-parent score exceeds 50%; quiet ordering already "
                "reduces equal-score work and retains original evaluation. RL weights remain "
                "a separate challenger, avoiding a simultaneous evaluation/search change. "
                "This selects an engineering baseline, not a promoted champion.",
            }
        )
        save(HERE / "BASELINE_MANIFEST.json", manifest)
    candidates = {}
    for label in ("lmr", "staged"):
        source = HERE / f"{label}_interface_runtime"
        verification = load(HERE / f"{label}_interface_verification.json")
        probe = load(source / "probe_manifest.json")
        out = ROOT / f"experiments/search_v2_{label}_01"
        if out.exists():
            existing_manifest = load(out / "manifest.json")
            for name, digest in probe["sha256"].items():
                assert sha(out / name) == digest, (label, name, "frozen candidate changed on disk")
            assert existing_manifest["sha256"] == probe["sha256"]
            candidates[label] = out
            continue
        out.mkdir(exist_ok=False)
        for name, digest in probe["sha256"].items():
            assert sha(source / name) == digest
            if name.endswith(".py"):
                assert verification["sha256"][name] == digest
            target = out / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((source / name).read_bytes())
        save(
            out / "manifest.json",
            {
                "status": "experimental; frozen for candidate tournament",
                "parent": str(baseline),
                "parent_sha256": parent["sha256"],
                "mechanism": label,
                "coefficient": 0.25,
                "sha256": probe["sha256"],
                "verification_sha256": sha(HERE / f"{label}_interface_verification.json"),
                "rules": "Own Python/Numba only; no external engine in runtime.",
            },
        )
        candidates[label] = out
    # Aspiration variant: frozen from its own verified runtime when its freeze
    # manifest exists (written by prepare_aspir_freeze.py after verification).
    aspir_manifest_path = HERE / "aspir_freeze_manifest.json"
    if aspir_manifest_path.exists():
        aspir_probe = load(aspir_manifest_path)
        out = ROOT / "experiments/search_v2_aspir_01"
        if out.exists():
            existing_manifest = load(out / "manifest.json")
            for name, digest in aspir_probe["sha256"].items():
                assert sha(out / name) == digest, (
                    "aspir",
                    name,
                    "frozen candidate changed on disk",
                )
            assert existing_manifest["sha256"] == aspir_probe["sha256"]
        else:
            source = HERE / "aspir_interface_runtime"
            out.mkdir(exist_ok=False)
            for name, digest in aspir_probe["sha256"].items():
                assert sha(source / name) == digest, (
                    "aspir",
                    name,
                    "runtime changed since verification",
                )
                target = out / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((source / name).read_bytes())
            save(
                out / "manifest.json",
                {
                    "status": "experimental; frozen for candidate tournament",
                    "parent": str(ROOT / "experiments/compiled_ordered_01"),
                    "parent_sha256": parent["sha256"],
                    "mechanism": "aspiration",
                    "aspiration_delta_cp": 45,
                    "verification": "aspir_verification_01.json",
                    "sha256": aspir_probe["sha256"],
                    "rules": "Own Python/Numba only; no external engine in runtime.",
                },
            )
        candidates["aspir"] = out
    # Combined staged+LMR variant: frozen from its own verified runtime when its
    # freeze manifest exists (written by prepare_combined_freeze.py after
    # verification). Queued after the proven mechanisms per the standing rule.
    combined_manifest_path = HERE / "combined_freeze_manifest.json"
    if combined_manifest_path.exists():
        combined_probe = load(combined_manifest_path)
        out = ROOT / "experiments/search_v2_combined_01"
        if out.exists():
            existing_manifest = load(out / "manifest.json")
            for name, digest in combined_probe["sha256"].items():
                assert sha(out / name) == digest, (
                    "combined",
                    name,
                    "frozen candidate changed on disk",
                )
            assert existing_manifest["sha256"] == combined_probe["sha256"]
        else:
            source = HERE / "combined_interface_runtime"
            out.mkdir(exist_ok=False)
            for name, digest in combined_probe["sha256"].items():
                assert sha(source / name) == digest, (
                    "combined",
                    name,
                    "runtime changed since verification",
                )
                target = out / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((source / name).read_bytes())
            save(
                out / "manifest.json",
                {
                    "status": "experimental; frozen for candidate tournament",
                    "parent": str(ROOT / "experiments/compiled_ordered_01"),
                    "parent_sha256": parent["sha256"],
                    "mechanism": "staged_lmr_combined",
                    "verification": "combined_verification_01.json",
                    "sha256": combined_probe["sha256"],
                    "rules": "Own Python/Numba only; no external engine in runtime.",
                },
            )
        candidates["combined"] = out
    return candidates


def run_comparison(candidate: Path, opponent: Path, output: Path, live: bool) -> dict[str, Any]:
    if (output / "report_50.json").exists():
        report = audit(output)
        report["complete_50"] = report["game_count"] == 50
        report["resumed_complete"] = True
        print(f"{output.name} already complete; reusing audit.", flush=True)
        return report
    if output.exists():
        print(
            f"Resuming existing screen {output.name}; completed games are reused as-is.",
            flush=True,
        )
    log_path = HERE / f"{output.name}.log"
    command = [
        str(PYTHON),
        "tools/candidate_screen.py",
        "--agent",
        str(candidate),
        "--opponent",
        str(opponent),
        "--out",
        str(output),
        "--pairs",
        "25",
        "--workers",
        str(WORKERS),
        "--bank",
        "screen",
        "--seed",
        "20260906",
        "--base-ms",
        str(BASE_MS),
        "--increment-ms",
        str(INCREMENT_MS),
        "--record-games",
    ]
    print(
        f"Starting {candidate.name} vs {opponent.name}: 50 games, "
        f"{BASE_MS / 1000:g}s+{INCREMENT_MS / 1000:g}s (fast development clock)",
        flush=True,
    )
    with log_path.open("a" if log_path.exists() else "x") as log:
        proc = subprocess.Popen(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        stopped = False
        while proc.poll() is None:
            time.sleep(10)
            if not live or not (output / "games").exists():
                continue
            games = [load(p) for p in (output / "games").glob("*.json")]
            points = sum(
                1.0 if g["result"] == g["candidate_color"]
                else 0.5 if g["result"] == "draw" else 0.0
                for g in games
            )
            if points + (50 - len(games)) >= LIVE_REQUIRED_POINTS:
                continue
            current = processes()
            process = next((p for p in current if p["ProcessId"] == proc.pid), None)
            if process is None:
                continue
            assert (
                str(output) in process["CommandLine"]
                and "candidate_screen.py" in process["CommandLine"]
            )
            descendants = []
            frontier = [proc.pid]
            while frontier:
                children = [p for p in current if p["ParentProcessId"] in frontier]
                descendants.extend(children)
                frontier = [p["ProcessId"] for p in children]
            # Recount immediately before stopping only our own verified child tree.
            games = [load(p) for p in (output / "games").glob("*.json")]
            points = sum(
                1.0 if g["result"] == g["candidate_color"]
                else 0.5 if g["result"] == "draw" else 0.0
                for g in games
            )
            if points + (50 - len(games)) >= LIVE_REQUIRED_POINTS:
                continue
            subprocess.run(
                ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                check=True,
                stdout=subprocess.DEVNULL,
            )
            proc.wait(timeout=30)
            save(
                output / "futility_decision.json",
                {
                    "action": "stopped_for_mathematical_futility",
                    "created_utc": datetime.now(UTC).isoformat(),
                    "planned_games": 50,
                    "completed_games": len(games),
                    "points": points,
                    "maximum_reachable_points": points + (50 - len(games)),
                    "required_points": LIVE_REQUIRED_POINTS,
                    "root": process,
                    "descendants": descendants,
                    "reason": "Cannot reach the 55% live score gate (27.5/50 points) "
                    "against the exact live candidate; preserve all records "
                    "and stale lock; do not resume.",
                },
            )
            stopped = True
        if not stopped:
            assert proc.returncode == 0, (output, proc.returncode, log_path)
    report = audit(output)
    report["stopped_for_futility"] = stopped
    report["complete_50"] = (output / "report_50.json").exists() and report["game_count"] == 50
    return report


def main() -> None:
    if STATE.exists():
        archive = HERE / "candidate_tournament_01_superseded.json"
        if archive.exists():
            archive = HERE / f"candidate_tournament_01_superseded_{int(time.time())}.json"
        STATE.rename(archive)
        print(f"Archived previous controller state to {archive.name}.", flush=True)
    state: dict[str, Any] = {"status": "waiting_for_old_parent_diagnostics", "results": []}
    save(STATE, state)
    try:
        wait_and_close_old()
        candidates = freeze_candidates()
        state["candidates"] = {k: str(v) for k, v in candidates.items()}
        state["status"] = "candidate_screens_running"
        save(STATE, state)
        # Sequential comparisons keep host load controlled and conserve compute.
        for name, candidate in candidates.items():
            opponents = [
                ("parent", ROOT / "experiments/compiled_ordered_01", False),
                ("live", ROOT / "experiments/silky_snow", True),
                ("pvs", ROOT / "experiments/compiled_pvs_01", False),
                ("rl", ROOT / "experiments/compiled_sf7_rl_01", False),
            ]
            for label, opponent, live in opponents:
                output = HERE / f"{name}_{label}_{CLOCK_TAG}"
                report = run_comparison(candidate, opponent, output, live)
                state["results"].append({"candidate": name, "opponent": label, "audit": report})
                save(STATE, state)
                good = report["complete_50"] and (
                    report["all_recorded_score"] >= LIVE_GATE_SCORE
                    if live
                    else report["all_recorded_score"] >= 0.55
                )
                if not good:
                    print(
                        f"{name} did not pass {label}; preserved results, testing next variant.",
                        flush=True,
                    )
                    break
        state["status"] = (
            "screens_finished; inspect evidence and continue development or confirmation"
        )
        save(STATE, state)
        print(state["status"], flush=True)
    except BaseException as error:
        state["status"] = "attention_required"
        state["error"] = repr(error)
        save(STATE, state)
        raise


if __name__ == "__main__":
    main()
