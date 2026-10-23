"""Explicit LAN host/origin allowlist shared by HTTP and WebSocket routes."""
from dataclasses import dataclass
from ipaddress import IPv4Address, IPv4Network
import os


@dataclass(frozen=True)
class NetworkAccess:
    lan_address: str = ''
    https_enabled: bool = False

    def __post_init__(self):
        if self.lan_address:
            address = IPv4Address(self.lan_address)
            if not any(address in IPv4Network(block) for block in
                       ('10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16')):
                raise ValueError('LAN adresi özel bir IPv4 adresi olmalıdır.')

    @classmethod
    def from_env(cls):
        return cls(os.environ.get('VOICE_LAN_IP', '').strip(), os.environ.get('VOICE_LAN_HTTPS') == '1')

    @property
    def hosts(self):
        return {'localhost', '127.0.0.1', '::1', 'testserver'} | (
            {self.lan_address} if self.lan_address else set())

    @property
    def origins(self):
        origins = {f'http://{host}:{port}' for host in
                   ('localhost', '127.0.0.1', '[::1]') for port in (5173, 8000)}
        if self.lan_address:
            origins.add(self.lan_url)
        if self.https_enabled:
            origins.update(f'https://{host}:8000' for host in ('localhost', '127.0.0.1', '[::1]'))
            origins.update(f'http://{host}:8001' for host in ('localhost', '127.0.0.1', '[::1]'))
            if self.https_url:
                origins.add(self.https_url)
        return origins

    @property
    def lan_url(self):
        return self.https_url or (f'http://{self.lan_address}:8000' if self.lan_address else None)

    def describe(self):
        return dict(lan_enabled=bool(self.lan_address), lan_url=self.lan_url,
                    https_url=self.https_url)

    @property
    def https_url(self):
        return f'https://{self.lan_address}:8000' if self.lan_address and self.https_enabled else None
