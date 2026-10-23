"""Validate LAN TLS with the explicit local CA; never disable TLS verification."""
import argparse
import asyncio
import hashlib
import json
from pathlib import Path
import ssl

import httpx
from websockets.asyncio.client import connect

ROOT = Path(__file__).resolve().parents[1]


async def verify(address):
    ca = ROOT / 'data/certs/VoiceAIStudio-Local-CA.crt'
    context = ssl.create_default_context(cafile=str(ca))
    https_url = f'https://{address}:8000'
    async with httpx.AsyncClient(verify=context, timeout=30, trust_env=False) as client:
        health = await client.get(https_url + '/api/v1/health')
        health.raise_for_status()
        assert health.json()['status'] == 'ok'
        status = (await client.get(https_url + '/api/v1/system/status')).json()
        assert status['network']['https_url'] == https_url
        public_ca = await client.get(https_url + '/api/v1/system/local-ca.crt')
        public_ca.raise_for_status()
        assert public_ca.content == ca.read_bytes()
        for path in ('/api/v1/system/server.key', '/data/certs/server.key', '/data/certs/root-key.dpapi'):
            assert (await client.get(https_url + path)).status_code == 404
    async with connect(f'wss://{address}:8000/api/v1/realtime/voice',
                       ssl=context, origin=https_url, proxy=None) as socket:
        await socket.send(json.dumps(dict(type='interrupt')))
        event = json.loads(await asyncio.wait_for(socket.recv(), timeout=5))
        assert event['state'] == 'interrupted'
    result = dict(url=https_url, tls_verified=True, hostname_verified=True,
                  public_ca_download=True, private_keys_not_served=True,
                  wss_verified=True, lm_connected=status['lm']['connected'],
                  ca_sha256=hashlib.sha256(ssl.PEM_cert_to_DER_cert(ca.read_text())).hexdigest())
    (ROOT / 'docs/https-results.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--address', default='192.168.8.13')
    asyncio.run(verify(parser.parse_args().address))
