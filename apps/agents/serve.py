"""Explicit loopback or private LAN TLS launcher."""
import argparse
import ipaddress
import os
import httpx
import uvicorn

def validate_lan(host, cert, key, backend_status):
    address = ipaddress.ip_address(host)
    if not any(address in ipaddress.ip_network(block) for block in ('10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16')):
        raise ValueError('LAN adresi özel IPv4 olmalı; 0.0.0.0 kabul edilmez.')
    if not cert or not key:
        raise ValueError('LAN için HTTPS sertifikası ve anahtarı gerekli.')
    if backend_status.get('network', {}).get('lan_enabled') is not False:
        raise ValueError('Ana ASYA backend yalnızca localhost modunda çalışmalı. Mevcut LAN modunu önce kapatın.')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--lan-address')
    parser.add_argument('--cert')
    parser.add_argument('--key')
    args = parser.parse_args()
    if args.lan_address:
        with httpx.Client(trust_env=False, timeout=30) as client:
            response = client.get('http://127.0.0.1:8000/api/v1/system/status')
            response.raise_for_status()
        validate_lan(args.lan_address, args.cert, args.key, response.json())
        os.environ['ASYA_AGENT_LAN_IP'] = args.lan_address
    uvicorn.run('apps.agents.main:app', host=args.lan_address or '127.0.0.1', port=8002,
                ssl_certfile=args.cert, ssl_keyfile=args.key, access_log=False, limit_concurrency=32)
