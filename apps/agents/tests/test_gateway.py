import json
import tempfile
import unittest
import asyncio
from unittest.mock import AsyncMock, Mock
from pathlib import Path
import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient
from apps.agents.main import create_app
from apps.agents.admin import router
from apps.agents.serve import validate_lan
from apps.agents.store import SCOPES, AgentStore
from fastapi import HTTPException

class GatewayTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.calls = []
        def backend(request):
            self.calls.append(request)
            path = request.url.path
            if path.endswith('/settings'):
                return httpx.Response(200, json={'language': 'tr', 'default_voice': '', 'tts_device': 'cpu', 'offline': True})
            if path.endswith('/voices'):
                if request.method == 'POST':
                    return httpx.Response(201, json={'id': 'voice1', 'name': 'Test', 'language': 'tr', 'asset_id': 'secret'})
                return httpx.Response(200, json=[{'id': 'voice1', 'name': 'Test', 'language': 'tr', 'asset_id': 'secret'}])
            if path.endswith('/voices/voice1'):
                return httpx.Response(200, json={'id': 'voice1', 'name': 'Changed', 'language': 'tr', 'asset_id': 'secret'})
            if path.endswith('/stt/transcribe'):
                return httpx.Response(200, json={'text': 'Merhaba', 'language': 'tr', 'asset_id': 'secret'})
            if path.endswith('/tts/generate'):
                return httpx.Response(202, json={'id': 'upstream1', 'status': 'queued'})
            if '/tts/jobs/' in path:
                return httpx.Response(200, json={'id': 'upstream1', 'status': 'completed', 'asset_id': 'audio1'})
            if '/audio/' in path:
                return httpx.Response(200, content=b'RIFFtestaudio', headers={'content-type': 'audio/wav'})
            return httpx.Response(200, json={'tts': {'state': 'ready'}, 'stt': {}, 'network': {'lan_enabled': False}})
        self.app = create_app(Path(self.temp.name), httpx.MockTransport(backend))
        self.client = self.enterContext(TestClient(self.app, base_url='http://127.0.0.1:8002'))
        self.store = self.app.state.store
        self.ali = self.store.create_agent('Ali')
        self.headers = {'Authorization': 'Bearer ' + self.ali['token']}
    def enable(self):
        self.store.set_enabled(True)
    def test_disabled_default_and_persistent_switch(self):
        self.assertFalse(self.store.enabled())
        self.assertFalse(self.client.get('/.well-known/asya-agent.json').json()['enabled'])
        for path in ('/v1/audio/speech', '/mcp', '/api/v1/agent/speech'):
            self.assertEqual(self.client.post(path, json={'input': 'hello'}, headers=self.headers).status_code, 403)
        self.assertEqual(self.calls, [])
    def test_auth_revocation_origin(self):
        self.enable()
        self.assertEqual(self.client.post('/api/v1/agent/speech', json={'input': 'hello'}).status_code, 401)
        self.assertEqual(self.client.get('/.well-known/asya-agent.json', headers={'Origin': 'https://evil.example'}).status_code, 403)
        self.store.revoke(self.ali['id'])
        self.assertEqual(self.client.post('/api/v1/agent/speech', json={'input': 'hello'}, headers=self.headers).status_code, 401)
    def test_speech_idempotency_ownership_and_disable(self):
        self.enable()
        headers = self.headers | {'Idempotency-Key': 'once'}
        first = self.client.post('/api/v1/agent/speech', json={'input': 'Merhaba'}, headers=headers)
        self.assertEqual(first.status_code, 202, first.text)
        identity = first.json()['id']
        second = self.client.post('/api/v1/agent/speech', json={'input': 'Merhaba'}, headers=headers)
        self.assertEqual(identity, second.json()['id'])
        self.assertEqual(sum(r.url.path.endswith('/tts/generate') for r in self.calls), 1)
        conflict = self.client.post('/api/v1/agent/speech', json={'input': 'different'}, headers=headers)
        self.assertEqual(conflict.status_code, 409)
        other = self.store.create_agent('Ayse')
        url = '/api/v1/agent/jobs/' + identity
        self.assertEqual(self.client.get(url, headers={'Authorization': 'Bearer ' + other['token']}).status_code, 404)
        self.assertEqual(self.client.get(url + '/audio?format=wav', headers=headers).content, b'RIFFtestaudio')
        self.store.set_enabled(False)
        self.assertEqual(self.client.get(url + '/audio', headers=headers).status_code, 403)
    def test_openai_binary_and_validation(self):
        self.enable()
        response = self.client.post('/v1/audio/speech', json={'input': 'Hello', 'response_format': 'wav'}, headers=self.headers)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.headers['content-type'], 'audio/wav')
        for body in ({'input': ' '}, {'input': 'Hello', 'response_format': 'ogg'}, {'input': 'Hello', 'instructions': 'x'}):
            self.assertEqual(self.client.post('/v1/audio/speech', json=body, headers=self.headers).status_code, 400)
    def test_scope_filter_and_reference_privacy(self):
        self.enable()
        result = self.client.post('/api/v1/agent/operations/list_voices', json={}, headers=self.headers)
        self.assertNotIn('asset_id', result.json()[0])
        self.assertEqual(self.client.post('/api/v1/agent/operations/unload_tts', json={}, headers=self.headers).status_code, 403)
        names = [o['name'] for o in self.client.get('/.well-known/asya-agent.json', headers=self.headers).json()['operations']]
        self.assertNotIn('unload_tts', names)
        self.assertEqual(self.client.get('/.well-known/asya-agent.json').json()['operations'], [])
    def test_mcp_initialize_and_tools(self):
        self.enable()
        headers = self.headers | {'Accept': 'application/json, text/event-stream'}
        init = self.client.post('/mcp', headers=headers, json={'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {'protocolVersion': '2025-03-26', 'capabilities': {}, 'clientInfo': {'name': 'Ali', 'version': '1'}}})
        self.assertEqual(init.status_code, 200, init.text)
        listing = self.client.post('/mcp', headers=headers, json={'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list', 'params': {}})
        self.assertEqual(listing.status_code, 200, listing.text)
        self.assertIn('execute', [t['name'] for t in listing.json()['result']['tools']])
        called = self.client.post('/mcp', headers=headers, json={'jsonrpc': '2.0', 'id': 3, 'method': 'tools/call', 'params': {'name': 'execute', 'arguments': {'operation': 'list_voices'}}})
        self.assertNotEqual(called.json()['result'].get('isError'), True, called.text)
    def test_admin_remote_denied_and_switch_shared(self):
        app = FastAPI()
        runtime = Mock()
        runtime.refresh.return_value = {'installed': True}
        app.include_router(router(Path(self.temp.name), runtime))
        with TestClient(app, client=('192.168.1.4', 1000)) as client:
            self.assertEqual(client.put('/api/v1/agent-admin/access', json={'enabled': True}).status_code, 403)
        with TestClient(app, client=('127.0.0.1', 1000)) as client:
            self.assertEqual(client.put('/api/v1/agent-admin/access', json={'enabled': True}).status_code, 200)
        self.assertTrue(self.store.enabled())

    def test_lan_boundary(self):
        for host, cert, key, status in (
            ('0.0.0.0', 'cert', 'key', {'network': {'lan_enabled': False}}),
            ('8.8.8.8', 'cert', 'key', {'network': {'lan_enabled': False}}),
            ('192.168.1.20', '', '', {'network': {'lan_enabled': False}}),
            ('192.168.1.20', 'cert', 'key', {'network': {'lan_enabled': True}}),
        ):
            with self.assertRaises(ValueError):
                validate_lan(host, cert, key, status)
        validate_lan('192.168.1.20', 'cert', 'key', {'network': {'lan_enabled': False}})

    def test_management_scopes_and_arguments(self):
        self.enable()
        for operation in ('create_voice', 'transcribe', 'delete_voice', 'delete_job', 'update_settings', 'update_voice'):
            self.assertEqual(self.client.post('/api/v1/agent/operations/' + operation, json={}, headers=self.headers).status_code, 403)
        admin = self.store.create_agent('Manager', SCOPES)
        headers = {'Authorization': 'Bearer ' + admin['token']}
        for operation, args in [('create_voice', {'audio_base64': 'YQ=='}), ('transcribe', {'audio_base64': '!'}),
                                ('update_settings', {'lm_url': 'http://evil'}), ('delete_voice', {'voice_id': '../private'})]:
            self.assertEqual(self.client.post('/api/v1/agent/operations/' + operation, json=args, headers=headers).status_code, 400)
        self.assertEqual(self.client.post('/api/v1/agent/operations/generate_speech', json={}, headers=headers).status_code, 422)

    def test_uncertain_submission_is_not_repeated(self):
        self.enable()
        def broken(request):
            if request.url.path.endswith('/settings'):
                return httpx.Response(200, json={'language': 'tr'})
            raise httpx.ReadTimeout('lost connection')
        self.app.state.service.client._transport = httpx.MockTransport(broken)
        headers = self.headers | {'Idempotency-Key': 'uncertain'}
        self.assertEqual(self.client.post('/api/v1/agent/speech', json={'input': 'hello'}, headers=headers).status_code, 503)
        self.assertEqual(self.client.post('/api/v1/agent/speech', json={'input': 'hello'}, headers=headers).status_code, 409)

    def test_timeout_and_gate_during_wait(self):
        service = self.app.state.service
        service.job = AsyncMock(return_value={'status': 'running'})
        async def check():
            with self.assertRaises(HTTPException) as error:
                await service.wait(self.ali, 'test', timeout=.01)
            self.assertEqual(error.exception.status_code, 504)
            self.assertEqual(error.exception.detail['job_id'], 'test')
        asyncio.run(check())

    def test_credential_storage_and_switch_persistence(self):
        self.enable()
        self.assertTrue(AgentStore(Path(self.temp.name)).enabled())
        self.assertNotIn(self.ali['token'].encode(), self.store.path.read_bytes())
        self.assertNotIn('digest', self.store.list_agents()[0])

    def test_permitted_management_adapters(self):
        self.enable()
        agent = self.store.create_agent('Manager', SCOPES)
        headers = {'Authorization': 'Bearer ' + agent['token']}
        for operation, args in (
            ('create_voice', {'audio_base64': 'YQ==', 'name': 'Test', 'consent': True}),
            ('transcribe', {'audio_base64': 'YQ=='}),
            ('update_voice', {'voice_id': 'voice1', 'name': 'Changed'}),
            ('update_settings', {'language': 'tr'}),
            ('get_settings', {}), ('unload_tts', {}), ('unload_stt', {}),
        ):
            result = self.client.post('/api/v1/agent/operations/' + operation, json=args, headers=headers)
            self.assertEqual(result.status_code, 200, result.text)
            self.assertNotIn('asset_id', result.json())

    def test_disable_during_audio_does_not_return_bytes(self):
        self.enable()
        original = self.app.state.service.client._transport
        def disable_on_audio(request):
            result = original.handle_request(request)
            if '/audio/' in request.url.path:
                self.store.set_enabled(False)
            return result
        self.app.state.service.client._transport = httpx.MockTransport(disable_on_audio)
        result = self.client.post('/v1/audio/speech', json={'input': 'Hello'}, headers=self.headers)
        self.assertEqual(result.status_code, 403)
        self.assertNotIn(b'RIFFtestaudio', result.content)

if __name__ == '__main__':
    unittest.main()

