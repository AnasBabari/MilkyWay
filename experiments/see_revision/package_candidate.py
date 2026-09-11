"""Build and smoke a clearly experimental archive without replacing champion."""
import hashlib
import io
import json
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from harness.package import smoke  # noqa: E402
from tools.audit_candidate_package import audit  # noqa: E402

LAB = Path(__file__).resolve().parent
SRC = ROOT / 'experiments/search_v2_see_01'
OUT = LAB / 'agent.zip'
assert (LAB / 'verification.json').exists()
report = audit(SRC)
champion_hash = hashlib.sha256((ROOT / 'agent.zip').read_bytes()).hexdigest()


def archive_bytes():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in sorted(report['files']):
            entry = zipfile.ZipInfo(name, (2026, 9, 10, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, (SRC / name).read_bytes(), compresslevel=9)
    return buffer.getvalue()


payload = archive_bytes()
assert payload == archive_bytes()
OUT.write_bytes(payload)
with tempfile.TemporaryDirectory() as directory:
    with zipfile.ZipFile(OUT) as archive:
        archive.extractall(directory)
    actual = {p.relative_to(directory).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in Path(directory).rglob('*') if p.is_file()}
    assert actual == report['files']
print('Archive extraction verified; starting two-colour smoke', flush=True)
problems = smoke(OUT)
assert not problems, problems
digest = hashlib.sha256(payload).hexdigest()
(LAB / 'agent.sha256').write_text(f'{digest}  agent.zip\n')
assert hashlib.sha256((ROOT / 'agent.zip').read_bytes()).hexdigest() == champion_hash
report.update({'archive': str(OUT), 'sha256': digest, 'smoke_problems': problems,
               'deterministic': True, 'extraction_hashes_match': True,
               'qualified': False, 'status': 'experimental candidate; strength unproven',
               'remaining': ['50-game NMP screen', 'independent full-clock qualification']})
(LAB / 'package_verification.json').write_text(json.dumps(report, indent=2))
print(json.dumps({'archive': str(OUT), 'sha256': digest, 'qualified': False}), flush=True)
