#!/usr/bin/env python3
"""
gen_cert.py — one-time local self-signed TLS cert for the live dashboard.

This is a REAL cert (RSA 2048 + X.509, via openssl), not a placeholder.
Browsers will still warn on first visit because it's self-signed and not
chain-verified by a public CA — that warning is expected for local dev
HTTPS and is not a sign anything is broken. For a browser-trusted cert
on localhost, use `mkcert` instead; for a real domain, use Let's Encrypt.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
CERT = ROOT / "cert.pem"
KEY = ROOT / "key.pem"

if CERT.exists() and KEY.exists():
    print("cert.pem and key.pem already exist — delete them first if you want to regenerate.")
    sys.exit(0)

cmd = [
    "openssl", "req", "-x509", "-newkey", "rsa:2048",
    "-keyout", str(KEY), "-out", str(CERT),
    "-days", "365", "-nodes",
    "-subj", "/CN=127.0.0.1",
    "-addext", "subjectAltName=DNS:localhost,IP:127.0.0.1",
]

result = subprocess.run(cmd, capture_output=True, text=True)
if result.returncode != 0:
    print("openssl failed:\n", result.stderr)
    sys.exit(1)

print(f"Generated {CERT.name} and {KEY.name} (valid 365 days, CN=127.0.0.1)")
