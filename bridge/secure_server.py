#!/usr/bin/env python3
"""TLS-only production WebSocket bridge on TCP/443."""
from __future__ import annotations

import asyncio
import os
import ssl

from websockets.asyncio.server import serve

from server import BridgeServer

HOST = os.environ.get("SG_HOST", "0.0.0.0")
PORT = int(os.environ.get("SG_PORT", "443"))
CERT = os.environ.get("TLS_CERT")
KEY = os.environ.get("TLS_KEY")


class SecureBridgeServer(BridgeServer):
    def __init__(self, host: str = HOST, port: int = PORT):
        if port != 443:
            raise ValueError("production WebSocket bridge must listen on TCP/443")
        if not CERT or not KEY:
            raise RuntimeError("TLS_CERT and TLS_KEY are required; refusing plaintext startup")
        super().__init__(host=host, port=port)
        if self.bridge_watcher is not None:
            self.bridge_watcher._url = f"wss://{host}:443"

    async def start(self) -> None:
        if not os.path.isfile(CERT) or not os.path.isfile(KEY):
            raise RuntimeError("TLS certificate/key files are missing")

        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.minimum_version = ssl.TLSVersion.TLSv1_3
        context.load_cert_chain(certfile=CERT, keyfile=KEY)

        if self.memory:
            await self.memory.init()
        if self.memory_watcher:
            await self.memory_watcher.start()

        self._server = await serve(
            self.handle_client,
            self.host,
            443,
            ssl=context,
            ping_interval=20,
            ping_timeout=30,
            max_size=50 * 1024 * 1024,
        )
        print(f"Bridge LIVE -> wss://{self.host}:443", flush=True)
        await asyncio.Future()


async def main() -> None:
    server = SecureBridgeServer()
    try:
        await server.start()
    finally:
        await server.stop()


if __name__ == "__main__":
    asyncio.run(main())
