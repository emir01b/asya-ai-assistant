"""Check launch ports without importing the app or recovering its persisted jobs."""
from __future__ import annotations

import argparse
import json
import socket
import ssl

import httpx

from .core import ROOT


def probe(lan_address: str = '', https: bool = False) -> dict:
    occupied = []
    listeners = [('0.0.0.0' if lan_address else '127.0.0.1', 8000)]
    if https:
        listeners.append(('127.0.0.1', 8001))
    for host, port in listeners:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
                if hasattr(socket, 'SO_EXCLUSIVEADDRUSE'):
                    listener.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
                listener.bind((host, port))
        except OSError:
            occupied.append(port)
    if not occupied:
        return dict(state='free')

    scheme = 'https' if https else 'http'
    expected_url = f'{scheme}://{lan_address}:8000' if lan_address else None
    try:
        local_url = 'http://127.0.0.1:8001' if https else 'http://127.0.0.1:8000'
        with httpx.Client(timeout=8, trust_env=False) as client:
            health = client.get(local_url + '/api/v1/health')
            health.raise_for_status()
            health_data = health.json()
            if not isinstance(health_data, dict) or health_data.get('status') != 'ok':
                raise ValueError('Portu başka bir uygulama kullanıyor.')
            status = client.get(local_url + '/api/v1/system/status')
            status.raise_for_status()
            status_data = status.json()
            network = status_data.get('network', {}) if isinstance(status_data, dict) else {}
            if not isinstance(network, dict) or 'lan_enabled' not in network:
                raise ValueError('Sunucu erişim modu doğrulanamadı.')
        if https:
            # Verify the certificate as well as the mode; never skip TLS validation.
            context = ssl.create_default_context(cafile=str(ROOT / 'data/certs/VoiceAIStudio-Local-CA.crt'))
            with httpx.Client(verify=context, timeout=5, trust_env=False) as client:
                secure = client.get('https://127.0.0.1:8000/api/v1/health')
                secure.raise_for_status()
                secure_data = secure.json()
                if not isinstance(secure_data, dict) or secure_data.get('status') != 'ok':
                    raise ValueError('HTTPS yanıtı doğrulanamadı.')
            matches = network.get('https_url') == expected_url
        else:
            matches = (not network.get('https_url') and
                       (network.get('lan_url') == expected_url if lan_address else not network.get('lan_enabled')))
        if matches:
            return dict(state='running', url=expected_url or local_url, local_url=local_url)
        reason = 'Uygulama farklı bir adres veya erişim modunda açık.'
    except (httpx.HTTPError, ValueError, OSError) as exc:
        reason = f'Çalışan sunucu istenen modda doğrulanamadı: {exc}'
    return dict(state='blocked', ports=occupied, reason=reason)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--lan-address', default='')
    parser.add_argument('--https', action='store_true')
    args = parser.parse_args()
    print(json.dumps(probe(args.lan_address, args.https), ensure_ascii=True))
