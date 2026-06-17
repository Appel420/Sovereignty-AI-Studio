"""Compatibility launcher for the full sovereignty server."""

from __future__ import annotations

import asyncio

from bridge import BridgeServer


async def main() -> None:
    server = BridgeServer()
    try:
        await server.start()
    finally:
        await server.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        raise SystemExit(0)