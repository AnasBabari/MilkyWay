"""Audit the active comparison and package only a passing revised runtime."""
import hashlib
import io
import json
import shutil
import sys
import tempfile
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from harness.package import smoke  # noqa: E402
from tools.audit_candidate_package import audit as package_audit  # noqa: E402
from tools.audit_recorded_screen import audit  # noqa: E402

HERE = Path(__file__).resolve().parent
STATE = HERE / 'completion_state.json'
RUN = HERE / 'king_safety_vs_combined_50g'
CANDIDATE = ROOT / 'experiments/r94_king_safety_01'


def save(state):
    tmp = STATE.with_suffix('.tmp')
    tmp.write_text(json.dumps(state, indent=2))
    tmp.replace(STATE)


def main():
    assert not STATE.exists(), 'Inspect existing continuation before restarting'
    state = {'status': 'waiting_for_active_match', 'qualified': False,
             'required_score': 0.60, 'runtime_changed': ['compiled_eval.py']}
    save(state)
    try:
        deadline = time.monotonic() + 7200
        while not (RUN / 'report_50.json').exists() or (RUN / 'writer.lock').exists():
            assert time.monotonic() < deadline, 'Observation expired; inspect active writer'
            for path in (RUN / 'games').glob('*.json'):
                game = json.loads(path.read_text())
                assert game['termination'] not in {'flag', 'crash', 'illegal', 'init',
                                                    'both_failed'}, path
            time.sleep(15)
        evidence = audit(RUN)
        assert evidence['game_count'] == 50
        (HERE / 'head_to_head_final_audit.json').write_text(json.dumps(evidence, indent=2))
        state['comparison'] = {k: v for k, v in evidence.items() if k != 'games'}
        if evidence['all_recorded_score'] < 0.60:
            state['status'] = 'rejected; further_engine_work_needed; old_zip_preserved'
            save(state)
            return
        critical = json.loads((HERE / 'actual_clock_probe.json').read_text())
        assert next(r for r in critical if r['ply'] == 50)['move'] == 'e1c1'
        preflight = package_audit(CANDIDATE)
        expected = preflight['files']

        def build():
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, 'w') as archive:
                for name, sha in sorted(expected.items()):
                    data = (CANDIDATE / name).read_bytes()
                    assert hashlib.sha256(data).hexdigest() == sha
                    item = zipfile.ZipInfo(name, (2026, 9, 10, 0, 0, 0))
                    item.create_system = 3
                    item.external_attr = 0o100644 << 16
                    archive.writestr(item, data, compress_type=zipfile.ZIP_DEFLATED,
                                     compresslevel=9)
            return buffer.getvalue()

        data = build()
        assert data == build()
        candidate_zip = HERE / 'agent_r94_king_safety.zip'
        assert not candidate_zip.exists()
        candidate_zip.write_bytes(data)
        with tempfile.TemporaryDirectory(prefix='r94-verify-') as tmp:
            directory = Path(tmp)
            with zipfile.ZipFile(candidate_zip) as archive:
                assert archive.testzip() is None
                assert set(archive.namelist()) == set(expected)
                archive.extractall(directory)
            actual = {p.relative_to(directory).as_posix():
                      hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in directory.rglob('*') if p.is_file()}
            assert actual == expected
        state.update(status='artifact_smoke_running', preflight=preflight)
        save(state)
        problems = smoke(candidate_zip)
        assert not problems, problems
        target = ROOT / 'agent.zip'
        if target.exists():
            backup = HERE / 'previous_agent.zip'
            assert not backup.exists()
            shutil.copy2(target, backup)
            assert backup.read_bytes() == target.read_bytes()
            state['backup'] = str(backup)
        shutil.copyfile(candidate_zip, target)
        assert target.read_bytes() == data
        state.update(status='revised_archive_delivered; independent_confirmation_incomplete',
                     delivered_path=str(target), sha256=hashlib.sha256(data).hexdigest(),
                     smoke_passed=True, extraction_hashes_match=True, zipped_bytes=len(data))
        save(state)
        print(json.dumps(state), flush=True)
    except BaseException as error:
        state.update(status='attention_required', error=repr(error))
        save(state)
        raise


if __name__ == '__main__':
    main()
