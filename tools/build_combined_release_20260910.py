"""Build the user-requested combined archive without claiming qualification."""
from __future__ import annotations

import hashlib
import io
import json
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Any

from harness.package import smoke
from tools.audit_candidate_package import audit as package_audit
from tools.audit_recorded_screen import audit as game_audit

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / 'experiments/search_v2'


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    candidate = ROOT / 'experiments/search_v2_combined_01'
    out = HERE / 'requested_archive_20260910'
    out.mkdir(exist_ok=False)
    report: dict[str, Any] = {
        'status': 'building; independent confirmation incomplete',
        'qualified': False, 'candidate': str(candidate),
        'authorization': 'Latest user request: make a new agent.zip',
        'preflight': package_audit(candidate),
    }
    report['development'] = []
    for label in ('parent', 'live', 'pvs', 'rl', 'staged', 'lmr', 'aspir'):
        audited = game_audit(HERE / f'combined_{label}_12s_50g')
        assert audited['game_count'] == 50
        report['development'].append({k: v for k, v in audited.items() if k != 'games'})
    expected = report['preflight']['files']

    def build() -> bytes:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_DEFLATED,
                             compresslevel=9) as archive:
            for name, sha in sorted(expected.items()):
                source = candidate / name
                assert digest(source) == sha
                member = zipfile.ZipInfo(name, date_time=(2026, 9, 10, 0, 0, 0))
                member.create_system = 3
                member.external_attr = 0o100644 << 16
                archive.writestr(member, source.read_bytes(),
                                 compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
        return buffer.getvalue()

    data = build()
    assert data == build(), 'Repeated archive builds differ'
    staged = out / 'agent.zip'
    staged.write_bytes(data)
    with tempfile.TemporaryDirectory(prefix='combined-extract-') as tmp:
        extracted = Path(tmp)
        with zipfile.ZipFile(staged) as archive:
            assert archive.testzip() is None
            assert set(archive.namelist()) == set(expected)
            assert all(not Path(n).is_absolute() and '..' not in Path(n).parts
                       for n in archive.namelist())
            archive.extractall(extracted)
        actual = {p.relative_to(extracted).as_posix(): digest(p)
                  for p in extracted.rglob('*') if p.is_file()}
        assert actual == expected
    report.update(archive_sha256=digest(staged), zipped_bytes=len(data),
                  extracted_hashes_match=True, repeated_build_identical=True)
    evidence = out / 'verification.json'
    evidence.write_text(json.dumps(report, indent=2))
    print('Frozen hashes, seven tournament audits, deterministic build and extraction passed.',
          flush=True)
    problems = smoke(staged)
    report['smoke_problems'] = problems
    evidence.write_text(json.dumps(report, indent=2))
    assert not problems, 'Artifact smoke failed; root archive not replaced'
    assert digest(staged) == report['archive_sha256']
    target = ROOT / 'agent.zip'
    if target.exists():
        backup = out / 'previous_agent.zip'
        shutil.copy2(target, backup)
        assert digest(backup) == digest(target)
        report['previous_archive_sha256'] = digest(backup)
        report['previous_archive_backup'] = str(backup)
    shutil.copyfile(staged, target)
    assert digest(target) == report['archive_sha256']
    report.update(status='requested archive built and smoke verified; unconfirmed candidate',
                  delivered_path=str(target), uploaded=False)
    evidence.write_text(json.dumps(report, indent=2))
    print(json.dumps({k: report[k] for k in ('status', 'delivered_path',
                                           'archive_sha256', 'zipped_bytes')}), flush=True)


if __name__ == '__main__':
    main()
