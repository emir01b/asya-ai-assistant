import ssl
import unittest
from unittest.mock import MagicMock, patch

import httpx

from apps.backend.app.server_probe import probe


class ServerProbeTests(unittest.TestCase):
    def setUp(self):
        self.client = httpx.Client
        self.context = ssl.create_default_context()

    def socket(self, busy=True):
        listener = MagicMock()
        listener.__enter__.return_value = listener
        if busy:
            listener.bind.side_effect = OSError('address already in use')
        return listener

    def request(self, network, health=None):
        def handle(request):
            if request.url.path.endswith('/health'):
                return httpx.Response(200, json={'status': 'ok'} if health is None else health)
            return httpx.Response(200, json={'network': network})
        return lambda **kwargs: self.client(transport=httpx.MockTransport(handle), **kwargs)

    def test_free_ports_allow_launch_without_contacting_a_server(self):
        with patch('apps.backend.app.server_probe.socket.socket', return_value=self.socket(False)), \
             patch('apps.backend.app.server_probe.httpx.Client') as client:
            self.assertEqual(probe('192.168.8.13', True), {'state': 'free'})
            client.assert_not_called()

    def test_matching_https_is_reused_with_certificate_verification(self):
        network = dict(https_url='https://192.168.8.13:8000', lan_enabled=True)
        with patch('apps.backend.app.server_probe.socket.socket', return_value=self.socket()), \
             patch('apps.backend.app.server_probe.ssl.create_default_context', return_value=self.context), \
             patch('apps.backend.app.server_probe.httpx.Client', side_effect=self.request(network)) as client:
            result = probe('192.168.8.13', True)
            self.assertEqual(result['state'], 'running')
            self.assertEqual(result['url'], network['https_url'])
            self.assertIs(client.call_args_list[-1].kwargs['verify'], self.context)

    def test_another_lan_address_is_not_reused(self):
        network = dict(https_url='https://192.168.8.99:8000', lan_enabled=True)
        with patch('apps.backend.app.server_probe.socket.socket', return_value=self.socket()), \
             patch('apps.backend.app.server_probe.ssl.create_default_context', return_value=self.context), \
             patch('apps.backend.app.server_probe.httpx.Client', side_effect=self.request(network)):
            self.assertEqual(probe('192.168.8.13', True)['state'], 'blocked')

    def test_http_mode_does_not_reuse_https_server(self):
        network = dict(https_url='https://192.168.8.13:8000', lan_enabled=True)
        with patch('apps.backend.app.server_probe.socket.socket', return_value=self.socket()), \
             patch('apps.backend.app.server_probe.httpx.Client', side_effect=self.request(network)):
            self.assertEqual(probe()['state'], 'blocked')

    def test_unrelated_service_is_blocked_without_starting_backend(self):
        with patch('apps.backend.app.server_probe.socket.socket', return_value=self.socket()), \
             patch('apps.backend.app.server_probe.httpx.Client', side_effect=self.request({}, health=[])):
            self.assertEqual(probe()['state'], 'blocked')

    def test_unresponsive_occupied_port_is_blocked(self):
        with patch('apps.backend.app.server_probe.socket.socket', return_value=self.socket()), \
             patch('apps.backend.app.server_probe.httpx.Client', side_effect=httpx.ConnectError('offline')):
            result = probe('192.168.8.13', True)
            self.assertEqual(result['state'], 'blocked')
            self.assertEqual(result['ports'], [8000, 8001])
