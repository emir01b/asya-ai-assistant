import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from apps.agents.admin import router
from apps.agents.installer import AgentRuntime

class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.runtime = AgentRuntime(Path(self.temp.name))
        self.runtime.is_running = Mock(return_value=False)
        self.app = FastAPI()
        self.app.include_router(router(Path(self.temp.name) / 'data/agents', self.runtime))

    def test_missing_and_broken_environment_not_reported_installed(self):
        self.assertFalse(self.runtime.refresh()['installed'])
        self.runtime.python.parent.mkdir(parents=True)
        self.runtime.python.touch()
        self.runtime.checked = 0
        with patch('apps.agents.installer.subprocess.run', return_value=Mock(returncode=1)):
            self.assertFalse(self.runtime.refresh()['installed'])

    def test_existing_install_does_not_run_pip(self):
        self.runtime.probe = Mock(return_value=True)
        self.runtime.run = Mock()
        result = self.runtime.install()
        self.assertTrue(result['installed'])
        self.assertEqual(result['status'], 'installed')
        self.runtime.run.assert_not_called()

    def test_install_progress_duplicate_click_and_permissions_unchanged(self):
        entered, release = threading.Event(), threading.Event()
        commands = []
        def run(command, log):
            commands.append(command)
            if 'venv' in command:
                entered.set()
                release.wait(5)
        self.runtime.run = run
        self.runtime.probe = Mock(side_effect=[False, True])
        self.runtime.ensure_running = Mock()
        with TestClient(self.app, client=('127.0.0.1', 1000)) as client:
            first = client.post('/api/v1/agent-admin/installation')
            self.assertEqual(first.status_code, 202)
            self.assertTrue(entered.wait(2))
            self.assertEqual(client.get('/api/v1/agent-admin/installation').json()['status'], 'installing')
            client.post('/api/v1/agent-admin/installation')
            release.set()
            self.runtime.worker.join(5)
            result = client.get('/api/v1/agent-admin/installation').json()
            self.assertEqual(result['status'], 'installed')
            self.assertEqual(result['progress'], 100)
            self.assertFalse(client.get('/api/v1/agent-admin').json()['enabled'])
        self.assertEqual(len(commands), 2)
        self.runtime.ensure_running.assert_called_once()

    def test_failure_can_be_retried(self):
        self.runtime.probe = Mock(return_value=False)
        self.runtime.run = Mock(side_effect=RuntimeError('network unavailable'))
        self.runtime.install()
        self.runtime.worker.join(5)
        self.assertEqual(self.runtime.snapshot()['status'], 'error')
        self.assertFalse(self.runtime.snapshot()['installed'])
        self.runtime.run = Mock()
        self.runtime.probe = Mock(return_value=True)
        self.runtime.ensure_running = Mock()
        self.runtime.install()
        self.runtime.worker.join(5)
        self.assertEqual(self.runtime.snapshot()['status'], 'installed')

    def test_remote_denied_and_enable_requires_installation(self):
        with TestClient(self.app, client=('192.168.1.5', 1000)) as client:
            self.assertEqual(client.post('/api/v1/agent-admin/installation').status_code, 403)
            self.assertEqual(client.get('/api/v1/agent-admin/installation').status_code, 403)
        with TestClient(self.app, client=('127.0.0.1', 1000)) as client:
            self.assertEqual(client.put('/api/v1/agent-admin/access', json={'enabled': True}).status_code, 409)
            self.assertEqual(client.put('/api/v1/agent-admin/access', json={'enabled': False}).status_code, 200)

    def test_enable_starts_installed_service(self):
        self.runtime.probe = Mock(return_value=True)
        self.runtime.ensure_running = Mock()
        with TestClient(self.app, client=('127.0.0.1', 1000)) as client:
            self.assertEqual(client.put('/api/v1/agent-admin/access', json={'enabled': True}).status_code, 200)
        self.runtime.ensure_running.assert_called_once()

if __name__ == '__main__':
    unittest.main()
