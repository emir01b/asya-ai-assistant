"""Opt-in fresh install check in an isolated temporary project, without voice models."""
import shutil
import tempfile
import time
from pathlib import Path
from apps.agents.installer import AgentRuntime, ROOT

def main():
    staging = ROOT / '.setup-tests'
    staging.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='agent-install-', dir=staging) as directory:
        root = Path(directory)
        (root / 'apps/agents').mkdir(parents=True)
        shutil.copyfile(ROOT / 'apps/agents/requirements.txt', root / 'apps/agents/requirements.txt')
        runtime = AgentRuntime(root)
        runtime.ensure_running = lambda: None  # Do not start a second listener for this fixture.
        runtime.install()
        previous = None
        deadline = time.monotonic() + 300
        try:
            while runtime.worker.is_alive():
                state = runtime.snapshot()
                if state['progress'] != previous:
                    print(state['progress'], state['message'], flush=True)
                    previous = state['progress']
                if time.monotonic() > deadline:
                    raise RuntimeError('Fresh install test timed out')
                runtime.worker.join(1)
            state = runtime.snapshot()
            if not state['installed'] or state['status'] != 'installed':
                print((runtime.data / 'install.log').read_text(encoding='utf-8', errors='replace')[-5000:])
                raise RuntimeError(state['error'])
            print('Fresh venv + real pip installation + import/version verification: PASSED', flush=True)
        finally:
            runtime.close()

if __name__ == '__main__':
    main()
