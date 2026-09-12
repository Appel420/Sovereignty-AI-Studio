"""Canonical compatibility entry point for the local Python bridge.

The implementation lives in :mod:`bridge.server`; this root module preserves
START_SERVER.sh and legacy imports without duplicating the runtime owner.
"""

from bridge.server import BridgeServer, main

__all__ = ["BridgeServer", "main"]


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
