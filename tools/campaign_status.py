"""Audited campaign snapshot with explicit score and actual-win screen gates."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.audit_recorded_screen import audit  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    assert not args.out.exists()
    campaign = json.loads(args.campaign.read_text())
    planned = campaign["games_per_comparison"]
    rows = []
    agents: dict[str, dict[str, bool | None]] = {}
    for spec in campaign["runs"]:
        root = Path(spec["out"])
        report = audit(root)
        assert report["base_ms"] == campaign["base_ms"]
        assert report["increment_ms"] == campaign["increment_ms"]
        n = report["game_count"]
        assert n <= planned, root
        complete = n == planned and (root / f"report_{planned}.json").exists()
        if complete:
            summary = json.loads((root / f"report_{planned}.json").read_text())
            assert not summary["failed_terminations"], root
        candidate = Path(spec["agent"]).name
        opponent = Path(spec["opponent"]).name
        row = {"candidate": candidate, "opponent": opponent, "completed_games": n,
               "planned_games": planned, "complete": complete,
               "wdl": report["all_recorded_wdl"], "score": report["all_recorded_score"],
               "actual_win_rate": report["all_recorded_win_rate"], "run": str(root)}
        rows.append(row)
        gates = agents.setdefault(candidate, {"silky_score_gate": None, "sf7_win_gate": None})
        if opponent == "silky_snow":
            gates["silky_score_gate"] = complete and row["score"] >= 0.70
        elif opponent == "stockfish" and spec["stockfish_level"] == 7:
            gates["sf7_win_gate"] = complete and row["actual_win_rate"] >= 0.50
    for gates in agents.values():
        gates["observed_screen_targets_passed"] = (
            gates["silky_score_gate"] is True and gates["sf7_win_gate"] is True)
    result = {"campaign": str(args.campaign), "base_ms": campaign["base_ms"],
              "increment_ms": campaign["increment_ms"], "runs": rows, "agents": agents,
              "not_a_promotion": True,
              "note": "Partial rates are descriptive only. Final independent confirmation and "
                      "reliability/archive verification remain separate requirements."}
    args.out.write_text(json.dumps(result, indent=2))
    for row in rows:
        print(json.dumps(row))


if __name__ == "__main__":
    main()
