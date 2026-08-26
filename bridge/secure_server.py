#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import os
import ssl

from websockets.asyncio.server import serve

from server import BridgeServer

CERT = os.environ.get("TLS_CERT")
KEY = os.environ.get("TLS_KEY")
if not CERT or not KEY:
    raise SystemExit("TLS_CERT and TLS_KEY are required; refusing plaintext WebSocket startup")

class SecureBridgeServer(BridgeServer):
    async def start(self):
        if not os.path.exists(CERT) or not os.path.exists(KEY):
            raise SystemExit("TLS material is missing")
        if self.memory:
            await self.memory.init()
        if self.memory_watcher:
            await self.memory_watcher.start()
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.minimum_version = ssl.TLSVersion.TLSv1_3
        context.load_cert_chain(CERT, KEY)
        self._server = await serve(
            self.handle_client,
            self.host,
            self.port,
            ssl=context,
            ping_interval=20,
            ping_timeout=30,
            max_size=50 * 1024 * 1024,
        )
        print(f"Bridge LIVE → wss://{self.host}:{self.port}", flush=True)
        await asyncio.Future()

async def main():
    server = SecureBridgeServer()
    try:
        await server.start()
    finally:
        await server.stop()

if __name__ == "__main__":
    asyncio.run(main())
