"""Installer settings must never overwrite an existing user's preferences."""
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from apps.backend.app.core import Store

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location('provision_runtime', ROOT / 'scripts/provision-runtime.py')
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)


class SetupSettingsTests(unittest.TestCase):
    def test_cpu_fresh_install_selects_cpu_and_offline_models(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory))
            with patch('apps.backend.app.core.Store', return_value=store):
                runtime.initialize_settings('cpu')
            self.assertEqual(store.settings()['tts_device'], 'cpu')
            self.assertEqual(store.settings()['stt_device'], 'cpu')
            self.assertTrue(store.settings()['offline'])

    def test_skipped_models_enable_first_online_download(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory))
            with patch('apps.backend.app.core.Store', return_value=store):
                runtime.initialize_settings('cuda', online=True)
            self.assertEqual(store.settings()['tts_device'], 'cuda')
            self.assertFalse(store.settings()['offline'])

    def test_existing_settings_preserved_exactly(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory))
            previous = store.put('settings', dict(id='app', tts_device='cuda',
                                                 llm_model='chosen-model', temperature=.25))
            with patch('apps.backend.app.core.Store', return_value=store):
                runtime.initialize_settings('cpu', online=True)
            self.assertEqual(store.get('settings', 'app'), previous)


if __name__ == '__main__':
    unittest.main()
