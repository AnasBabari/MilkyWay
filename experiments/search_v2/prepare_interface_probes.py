"""Prepare own search prototypes for interface tests; no tournament or promotion."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def main() -> None:
    base = ROOT / "experiments/compiled_ordered_01"
    manifest = json.loads((base / "manifest.json").read_text())
    for label, module, source in (
        ("lmr", "reduced_search", ROOT / "experiments/compiled_core_01/reduced_search.py"),
        ("staged", "staged_search", HERE / "staged_runtime_01/staged_search.py"),
    ):
        out = HERE / f"{label}_interface_runtime"
        out.mkdir(exist_ok=False)
        for name, digest in manifest["sha256"].items():
            data = (base / name).read_bytes()
            assert hashlib.sha256(data).hexdigest() == digest
            target = out / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        (out / f"{module}.py").write_bytes(source.read_bytes())
        if label == "staged":
            (out / "core.py").write_bytes((HERE / "staged_runtime_01/core.py").read_bytes())
        agent = (out / "agent.py").read_text()
        before = "from ordered_search import position_key, search"
        assert agent.count(before) == 1
        (out / "agent.py").write_text(
            agent.replace(before, f"from {module} import position_key, search")
        )
        (out / "probe_manifest.json").write_text(
            json.dumps(
                {
                    "purpose": "interface probe only; not yet a frozen tournament candidate",
                    "source_parent": str(base),
                    "mechanism": label,
                    "sha256": {
                        str(p.relative_to(out)).replace("\\", "/"): hashlib.sha256(
                            p.read_bytes()
                        ).hexdigest()
                        for p in list(out.glob("*.py")) + list((out / "weights").glob("*"))
                    },
                },
                indent=2,
            )
        )
        print(out)


if __name__ == "__main__":
    main()
