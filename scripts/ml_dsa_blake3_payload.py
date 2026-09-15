#!/usr/bin/env python3
"""ML-DSA + BLAKE3 payload signer for Sovereignty AI Studio.

Generates a signed payload: BLAKE3 hash of the body, then ML-DSA signature over
the hash. Pure-Python, air-gap friendly. No external network calls.

Usage:
    python scripts/ml_dsa_blake3_payload.py --keygen
    python scripts/ml_dsa_blake3_payload.py --sign --message 'hello' --sk sk.bin --out payload.json
    python scripts/ml_dsa_blake3_payload.py --verify --payload payload.json --pk pk.bin
"""
from __future__ import annotations

import argparse
import base64
import json
import sys
from pathlib import Path

try:
    from blake3 import blake3
except ImportError:  # pragma: no cover
    blake3 = None  # type: ignore

try:
    from dilithium_py.ml_dsa import ML_DSA_44
except ImportError:  # pragma: no cover
    ML_DSA_44 = None  # type: ignore


def blake3_hash(data: bytes) -> bytes:
    if blake3 is not None:
        return blake3(data).digest()
    import hashlib
    return hashlib.blake2b(data, digest_size=32).digest()


def keygen() -> tuple[bytes, bytes]:
    if ML_DSA_44 is None:
        raise RuntimeError('dilithium-py not installed: pip install dilithium-py blake3')
    return ML_DSA_44.keygen()


def sign_payload(message: bytes, sk: bytes) -> dict:
    if ML_DSA_44 is None:
        raise RuntimeError('dilithium-py not installed')
    body_hash = blake3_hash(message)
    sig = ML_DSA_44.sign(sk, body_hash)
    return {
        'alg': 'ML-DSA-44+BLAKE3',
        'body_blake3': base64.b64encode(body_hash).decode(),
        'signature': base64.b64encode(sig).decode(),
        'message_b64': base64.b64encode(message).decode(),
    }


def verify_payload(payload: dict, pk: bytes) -> bool:
    if ML_DSA_44 is None:
        raise RuntimeError('dilithium-py not installed')
    body_hash = base64.b64decode(payload['body_blake3'])
    sig = base64.b64decode(payload['signature'])
    msg = base64.b64decode(payload['message_b64'])
    if blake3_hash(msg) != body_hash:
        return False
    return ML_DSA_44.verify(pk, body_hash, sig)


def main() -> int:
    p = argparse.ArgumentParser(description='ML-DSA + BLAKE3 payload signer')
    p.add_argument('--keygen', action='store_true')
    p.add_argument('--sign', action='store_true')
    p.add_argument('--verify', action='store_true')
    p.add_argument('--message', default='')
    p.add_argument('--sk', type=Path)
    p.add_argument('--pk', type=Path)
    p.add_argument('--out', type=Path)
    p.add_argument('--payload', type=Path)
    args = p.parse_args()

    if args.keygen:
        pk, sk = keygen()
        Path('pk.bin').write_bytes(pk)
        Path('sk.bin').write_bytes(sk)
        print('Wrote pk.bin and sk.bin')
        return 0

    if args.sign:
        if not args.sk or not args.sk.exists():
            print('Missing --sk', file=sys.stderr)
            return 1
        sk = args.sk.read_bytes()
        payload = sign_payload(args.message.encode(), sk)
        out = args.out or Path('payload.json')
        out.write_text(json.dumps(payload, indent=2))
        print(f'Wrote {out}')
        return 0

    if args.verify:
        if not args.pk or not args.pk.exists() or not args.payload:
            print('Missing --pk or --payload', file=sys.stderr)
            return 1
        pk = args.pk.read_bytes()
        payload = json.loads(args.payload.read_text())
        ok = verify_payload(payload, pk)
        print('VERIFY:', 'PASS' if ok else 'FAIL')
        return 0 if ok else 2

    p.print_help()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
