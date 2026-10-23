import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from apps.backend.app.core import Store
from apps.backend.app.main import create_app
from apps.backend.app.network import NetworkAccess


class NetworkTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def client(self, lan=''):
        return TestClient(create_app(Store(Path(self.tmp.name)), network=NetworkAccess(lan)))

    def test_default_rejects_lan_host(self):
        with self.client() as client:
            self.assertEqual(client.get('/api/v1/health', headers={'host': '192.168.8.13:8000'}).status_code, 403)

    def test_lan_accepts_http_and_cors_preflight(self):
        with self.client('192.168.8.13') as client:
            headers = {'host': '192.168.8.13:8000', 'origin': 'http://192.168.8.13:8000'}
            self.assertEqual(client.get('/api/v1/health', headers=headers).status_code, 200)
            response = client.options('/api/v1/settings', headers={**headers,
                                      'access-control-request-method': 'PUT'})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers['access-control-allow-origin'], headers['origin'])
            self.assertEqual(client.get('/api/v1/health').status_code, 200)

    def test_lan_still_rejects_unknown_hosts_and_foreign_origins(self):
        with self.client('192.168.8.13') as client:
            for headers in ({'host': 'evil.example'}, {'host': '192.168.8.14:8000'},
                            {'origin': 'http://192.168.8.14:8000'},
                            {'origin': 'https://evil.example'}, {'sec-fetch-site': 'cross-site'}):
                with self.subTest(headers=headers):
                    self.assertEqual(client.get('/api/v1/health', headers=headers).status_code, 403)

    def test_lan_websocket_accepts_and_responds(self):
        with self.client('192.168.8.13') as client:
            with client.websocket_connect('/api/v1/realtime/voice', headers={
                'host': '192.168.8.13:8000', 'origin': 'http://192.168.8.13:8000'}) as ws:
                ws.send_json({'type': 'interrupt'})
                self.assertEqual(ws.receive_json()['state'], 'interrupted')

    def test_websocket_rejects_untrusted_host_and_origin(self):
        with self.client('192.168.8.13') as client:
            for headers in ({'host': 'evil.example'}, {'origin': 'https://evil.example'},
                            {'sec-fetch-site': 'cross-site'}):
                with self.subTest(headers=headers), self.assertRaises(WebSocketDisconnect) as error:
                    with client.websocket_connect('/api/v1/realtime/voice', headers=headers):
                        pass
                self.assertEqual(error.exception.code, 1008)

    def test_public_and_invalid_lan_addresses_rejected(self):
        for address in ('8.8.8.8', '127.0.0.1', '169.254.1.1', 'example.com', '::1'):
            with self.subTest(address=address), self.assertRaises(ValueError):
                NetworkAccess(address)

    def test_https_origin_uses_explicit_tls_port(self):
        network = NetworkAccess('192.168.8.13', True)
        with TestClient(create_app(Store(Path(self.tmp.name)), network=network)) as client:
            headers = {'host': '192.168.8.13:8000', 'origin': 'https://192.168.8.13:8000'}
            self.assertEqual(client.get('/api/v1/health', headers=headers).status_code, 200)
            self.assertEqual(client.get('/api/v1/health', headers={**headers, 'origin': 'https://192.168.8.13:8444'}).status_code, 403)
            with client.websocket_connect('/api/v1/realtime/voice', headers=headers) as ws:
                ws.send_json({'type': 'interrupt'})
                self.assertEqual(ws.receive_json()['state'], 'interrupted')

    def test_certificate_not_exposed_in_local_only_mode(self):
        with self.client() as client:
            self.assertEqual(client.get('/api/v1/system/local-ca.crt').status_code, 404)
