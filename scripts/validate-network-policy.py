#!/usr/bin/env python3
"""Validate local network policy and reject unsafe service bindings."""
from __future__ import annotations

import ipaddress
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "config" / "network-policy.json"


def load_policy() -> dict:
    with POLICY_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def validate(policy: dict) -> list[str]:
    errors: list[str] = []
    if policy.get("default_mode") != "offline":
        errors.append("default_mode must be offline")
    if policy.get("loopback_only") is not True:
        errors.append("loopback_only must be true")
    if policy.get("allow_lan_bind") is not False:
        errors.append("allow_lan_bind must be false")
    if policy.get("allow_global_ipv6_bind") is not False:
        errors.append("allow_global_ipv6_bind must be false")
    if set(policy.get("allowed_loopback_hosts", [])) != {"127.0.0.1", "::1"}:
        errors.append("allowed_loopback_hosts must contain only 127.0.0.1 and ::1")

    for name, binding in policy.get("service_bindings", {}).items():
        host = binding.get("host")
        port = binding.get("port")
        if host not in {"127.0.0.1", "::1"}:
            errors.append(f"{name} must bind to loopback, got {host!r}")
        if not isinstance(port, int) or not 1 <= port <= 65535:
            errors.append(f"{name} has invalid port {port!r}")

    # Reject non-contiguous IPv4 masks if diagnostic metadata is added later.
    netmask = policy.get("reported_netmask")
    if netmask:
        try:
            mask_int = int(ipaddress.IPv4Address(netmask))
            bits = f"{mask_int:032b}"
            if "01" in bits:
                errors.append(f"reported_netmask is non-contiguous: {netmask}")
        except ipaddress.AddressValueError:
            errors.append(f"reported_netmask is invalid: {netmask}")

    return errors


def main() -> int:
    errors = validate(load_policy())
    if errors:
        for error in errors:
            print(f"network policy: FAIL: {error}", file=sys.stderr)
        return 1
    print("network policy: PASS — offline, loopback-only, external network policy-gated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
