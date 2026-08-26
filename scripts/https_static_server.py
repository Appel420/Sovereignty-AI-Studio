#!/usr/bin/env python3
from __future__ import annotations

import argparse
import http.server
import ssl

parser = argparse.ArgumentParser(description="Serve static Sovereignty content over HTTPS only")
parser.add_argument("--host", default="127.0.0.1")
parser.add_argument("--port", type=int, default=9898)
parser.add_argument("--directory", default=".")
parser.add_argument("--cert", required=True)
parser.add_argument("--key", required=True)
args = parser.parse_args()

class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, fmt, *values):
        print(fmt % values, flush=True)

server = http.server.ThreadingHTTPServer((args.host, args.port), Handler)
server.RequestHandlerClass.directory = args.directory
context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
context.minimum_version = ssl.TLSVersion.TLSv1_3
context.load_cert_chain(args.cert, args.key)
server.socket = context.wrap_socket(server.socket, server_side=True)
print(f"HTTPS static server listening on https://{args.host}:{args.port}", flush=True)
server.serve_forever()
