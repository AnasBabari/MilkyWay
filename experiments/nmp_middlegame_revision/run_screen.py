"""One frozen 50-game screen, followed by audit; never promotes automatically."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LAB = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from tools.audit_recorded_screen import audit  # noqa: E402

assert (LAB / 'package_verification.json').exists(), 'Finish smoke testing first'
OUT = LAB / 'vs_nmp_50g'
assert not OUT.exists(), 'Use a fresh output directory; no duplicate writers'
status_path = LAB / 'screen_status.json'


def save(status):
    temporary = status_path.with_suffix('.tmp')
    temporary.write_text(json.dumps(status, indent=2))
    temporary.replace(status_path)


save({'status': 'running', 'qualified': False, 'games_planned': 50,
      'opponent': 'search_v2_nmp_01', 'gate_points': 30})
try:
    command = [sys.executable, 'tools/candidate_screen.py',
               '--agent', 'experiments/search_v2_nmp_mg_01',
               '--opponent', 'experiments/search_v2_nmp_01',
               '--out', str(OUT), '--pairs', '25', '--workers', '3',
               '--bank', 'screen', '--seed', '20260906',
               '--base-ms', '12000', '--increment-ms', '100', '--record-games']
    with (LAB / 'screen.log').open('w') as log:
        result = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
    if result.returncode:
        raise RuntimeError(f'Screen exited {result.returncode}; inspect screen.log')
    report = audit(OUT)
    assert report['game_count'] == 50
    assert sum(report['complete_pairs_wdl'].values()) == 50
    passed = report['all_recorded_score'] >= 0.60
    (LAB / 'screen_audit.json').write_text(json.dumps(report, indent=2))
    save({'status': 'completed_and_audited', 'qualified': False,
          'development_gate_passed': passed,
          'note': '60% development gate only. No automatic promotion.',
          'audit': report})
except Exception as error:
    save({'status': 'failed', 'qualified': False, 'error': str(error)})
    raise
