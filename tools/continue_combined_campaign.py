"""Continue the frozen combined candidate's development, never promote it."""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from tools.audit_recorded_screen import audit

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / 'experiments/search_v2'
STATE = HERE / 'combined_continuation_01.json'


def save(state: dict[str, Any]) -> None:
    temporary = STATE.with_suffix('.tmp')
    temporary.write_text(json.dumps(state, indent=2))
    temporary.replace(STATE)


def run(command: list[str], log: Path) -> None:
    with log.open('x') as stream:
        subprocess.run([sys.executable, *command], cwd=ROOT, stdout=stream,
                       stderr=subprocess.STDOUT, check=True)


def main() -> None:
    if STATE.exists():
        raise SystemExit('Continuation already exists; inspect it instead of duplicating')
    state: dict[str, Any] = {'status': 'waiting_for_existing_parent', 'qualified': False,
                             'results': [], 'live_required_score': 0.60}
    save(state)
    try:
        parent = HERE / 'combined_parent_12s_50g'
        deadline = time.monotonic() + 7200
        while not (parent / 'report_50.json').exists() or (parent / 'writer.lock').exists():
            if time.monotonic() > deadline:
                raise RuntimeError('Parent observation deadline; inspect owner, never auto-restart')
            for path in (parent / 'games').glob('*.json'):
                record = json.loads(path.read_text())
                if record['termination'] in {'flag', 'crash', 'init', 'illegal', 'both_failed'}:
                    raise RuntimeError(f'Parent reliability failure: {path}')
            time.sleep(15)
        result = audit(parent)
        state['results'].append(result)
        assert result['game_count'] == 50
        if result['all_recorded_score'] < 0.55:
            state['status'] = 'rejected_at_parent; further_development_needed'
            save(state)
            return
        for variant in ('staged', 'combined'):
            state['status'] = f'clock_replay_{variant}'
            save(state)
            output = HERE / f'{variant}_flag_replay_01.json'
            run(['-m', 'tools.replay_clock_failure', '--agent',
                 f'experiments/search_v2_{variant}_01', '--record',
                 str(HERE / 'confirm_staged_live_120s_100g/games/fresh_confirm_009_white.json'),
                 '--out', str(output)], HERE / f'{variant}_flag_replay_01.log')
            replay = json.loads(output.read_text())
            if variant == 'combined':
                assert replay['requests'][-1]['historical_move'] is None
                assert all(row.get('legal') and 'failure' not in row
                           and row['elapsed_s'] * 1000 < row['time_left_ms']
                           for row in replay['requests']), 'Combined clock replay failed'
        roster = [('live', 'silky_snow', 0.60), ('pvs', 'compiled_pvs_01', 0.55),
                  ('rl', 'compiled_sf7_rl_01', 0.55), ('staged', 'search_v2_staged_01', 0.55),
                  ('lmr', 'search_v2_lmr_01', 0.55), ('aspir', 'search_v2_aspir_01', 0.55)]
        for label, opponent, required in roster:
            state['status'] = f'screen_running_{label}'
            save(state)
            output = HERE / f'combined_{label}_12s_50g'
            assert not output.exists(), f'Existing evidence requires manual inspection: {output}'
            run(['tools/candidate_screen.py', '--agent', 'experiments/search_v2_combined_01',
                 '--opponent', f'experiments/{opponent}', '--out', str(output),
                 '--pairs', '25', '--workers', '3', '--bank', 'screen', '--seed', '20260906',
                 '--base-ms', '12000', '--increment-ms', '100', '--record-games'],
                HERE / f'combined_{label}_continuation_01.log')
            result = audit(output)
            state['results'].append(result)
            assert result['game_count'] == 50
            if result['all_recorded_score'] < required:
                state['status'] = f'rejected_at_{label}; further_development_needed'
                save(state)
                return
            save(state)
        state['status'] = 'development_passed; full_clock_tests_and_fresh_confirmation_required'
        save(state)
    except BaseException as error:
        state.update(status='attention_required', error=repr(error))
        save(state)
        raise


if __name__ == '__main__':
    main()
