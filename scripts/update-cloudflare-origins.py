#!/usr/bin/env python3
"""Generate Caddy's immediate-peer allowlist; no firewall mutation or reload."""
import ipaddress
from pathlib import Path
from urllib.request import urlopen

import json

with urlopen('https://api.cloudflare.com/client/v4/ips', timeout=20) as response:
    payload = json.load(response)
if payload.get('success') is not True:
    raise RuntimeError('Cloudflare IP request failed; existing allowlist preserved')
networks = []
for version, key in ((4, 'ipv4_cidrs'), (6, 'ipv6_cidrs')):
    parsed = [ipaddress.ip_network(value, strict=True) for value in payload['result'][key]]
    if not parsed or any(net.version != version or not net.is_global for net in parsed):
        raise RuntimeError('Invalid Cloudflare IP response; existing allowlist preserved')
    networks.extend(str(net) for net in parsed)
root = Path(__file__).resolve().parents[1]
path = root / 'infra/international/cloudflare-ips.caddy'
path.write_text('@not_cloudflare not remote_ip ' + ' '.join(networks) + '\n')
print(f'Wrote {len(networks)} verified network ranges to {path.name}')
