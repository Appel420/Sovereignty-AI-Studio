#!/usr/bin/env python3
"""Local root-chain oversight console with no third-party dependencies."""

from __future__ import annotations

import base64
import hashlib
import json
import re
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

HOST = "127.0.0.1"
PORT = 9897
MAX_BODY_BYTES = 64 * 1024

PEM = """-----BEGIN CERTIFICATE-----
MIICbjCCAdOgAwIBAgIBATANBgkqhkiG9w0BAQsFADByMQswCQYDVQQGEwJVUzEY
MBYGA1UEChMPVS5TLiBHb3Zlcm5tZW50MQwwCgYDVQQLEwNQS0kxDzANBgNVBAsT
BkRPREpRMSwwKgYDVQQDEyNET0QgSU5URVJPUEVSQUJJTElUWSBST09UIENBIDIw
HhcNMTAxMTI5MTQyNTEwWhcNMzAxMTI0MTQyNTEwWjByMQswCQYDVQQGEwJVUzEY
MBYGA1UEChMPVS5TLiBHb3Zlcm5tZW50MQwwCgYDVQQLEwNQS0kxDzANBgNVBAsT
BkRPREpRMSwwKgYDVQQDEyNET0QgSU5URVJPUEVSQUJJTElUWSBST09UIENBIDIw
ggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAwggEKAoIBAQC/xuCDk+YLgynoKDt2SuCs
jJ60VcPfGH7is3NytGihZtiYY+q+j17ADhGtf9LzpSUv7n6j2JCNSCFg098/hRv8
Qxe9rM3R/uAt/r1GHz6YVojfB0ySBLQF1RXgmqTDUdMKeNg8/Fwc5c0jSZdQPrG0
tqJTUiQJMQOME+fpTcP7A9wCo1rVbWuvFivUTv57oEE47UuvJjW1nIlpDuklzbFN
M6+ObWWRKOXc/XLo+KYxM5L/8AKjUE6Bwfj06pUpCaXaq2Bh/eq5T0oxipdm+MMQ
0tKGoyJD07t5Jy5vtbJl5UuNSa8QsdJbdXcQdOMW8iRneAy29jYPQu//o8C7xl61
AgMBAAGjQjBAMA8GA1UdEwEB/wQFMAMBAf8wHQYDVR0OBBYEFF/4rhOLkit5kkGj
dlwsgZ6axZx4MA4GA1UdDwEB/wQEAwIBhjANBgkqhkiG9w0BAQsFAAOCAQEAUyKL
L/dezOY4MizE80RLGcjgNLW8TUsJP6sPP7LgtPig3thXED8/LNK/NDeAU03jWRzJ
gIW+o40UpU9QWIqstkzCVuzh8512O73hUCCz7C6Tt+dPGfb4UsKHSFPiimI0R1TW
ET1RP5ejpjWC8s4hC73OJbsU9Ycc7fGSu/V+VEfIbMOwwq3CWAt4DA8fYKWlmQTw
CfMv4kuYuRgA7HqUS/o2CumHH0e5OSmRY3WiJOEEMpgzSV3nP5jkFvO4uVRqIrwd
LTdLE5GWFGuFKBEl19XSCmtf+1yQFoZK1JFA9QjHdFAmRLET4kU5q2XrRziBxvOL
/4ZKhMfkdCdIiBMPng==
-----END CERTIFICATE-----"""

_PEM_RE = re.compile(
    r"\A-----BEGIN CERTIFICATE-----\s*([A-Za-z0-9+/=\s]+)"
    r"-----END CERTIFICATE-----\s*\Z"
)


def _pem_digest(pem: str) -> str:
    return hashlib.sha256(pem.encode("ascii")).hexdigest()


ROOTS = [
    {
        "id": "dod-interoperability-root-ca-2",
        "name": "DOD INTEROPERABILITY ROOT CA 2",
        "pem": PEM,
        "metadata": {
            "subject": "DOD INTEROPERABILITY ROOT CA 2",
            "expected_pem_sha256": _pem_digest(PEM),
        },
    }
]


def validate_root(root: object) -> dict[str, object]:
    """Validate PEM structure and bind it to its declared metadata fingerprint."""
    if not isinstance(root, dict):
        return {"id": "unknown", "valid": False, "errors": ["Root entry is not an object."]}

    root_id = root.get("id", "unknown")
    pem = root.get("pem")
    metadata = root.get("metadata")
    errors: list[str] = []
    if not isinstance(pem, str):
        errors.append("Certificate PEM is missing.")
    else:
        match = _PEM_RE.fullmatch(pem)
        if not match:
            errors.append("Certificate PEM delimiters or Base64 payload are invalid.")
        else:
            try:
                der = base64.b64decode(re.sub(r"\s+", "", match.group(1)), validate=True)
                if not der or der[0] != 0x30:
                    errors.append("Certificate PEM does not contain a DER sequence.")
            except ValueError:
                errors.append("Certificate PEM Base64 payload is invalid.")

    expected = metadata.get("expected_pem_sha256") if isinstance(metadata, dict) else None
    if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
        errors.append("Root metadata lacks a valid expected_pem_sha256 value.")
    elif isinstance(pem, str) and _pem_digest(pem) != expected:
        errors.append("Metadata fingerprint does not match the certificate PEM.")

    return {
        "id": root_id if isinstance(root_id, str) else "unknown",
        "valid": not errors,
        "errors": errors,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Root Chain Oversight</title><style>
:root{color-scheme:dark;font-family:system-ui,sans-serif;background:#08111c;color:#e6edf5}
body{max-width:900px;margin:0 auto;padding:24px}h1{margin:0 0 8px}.banner{padding:14px;border-radius:8px;margin:16px 0;font-weight:700}.pending{background:#183451;color:#b9ddff}.ok{background:#153d2c;color:#b8f4cf}.error{background:#501d26;color:#ffccd2}
button{background:#238636;color:white;border:0;border-radius:6px;padding:10px 14px;font-weight:700;cursor:pointer;margin-right:8px}button.secondary{background:#30363d}
article{border:1px solid #30363d;border-radius:8px;padding:16px;margin:12px 0}.status{font-weight:700}.status.error{color:#ff9ca6;background:none;padding:0}.status.ok{color:#7ee787;background:none;padding:0}code{word-break:break-all;color:#9ecbff}
</style></head><body>
<h1>Root Chain Oversight</h1><p>Local-only certificate PEM and metadata integrity checks.</p>
<div id="alert" class="banner pending" role="alert">Loading roots…</div>
<p><button id="validate">Validate roots</button><button id="reload" class="secondary">Reload</button></p><main id="roots"></main>
<script>
let roots=[];
const alertBox=document.getElementById("alert"), rootList=document.getElementById("roots");
function setAlert(message, kind){alertBox.textContent=message;alertBox.className="banner "+kind;}
function render(results=[]){const indexed=new Map(results.map(r=>[r.id,r]));rootList.replaceChildren(...roots.map(root=>{
 const result=indexed.get(root.id), card=document.createElement("article"), title=document.createElement("h2");
 title.textContent=root.name||root.id; card.append(title);
 const status=document.createElement("p");status.className="status "+(result?(result.valid?"ok":"error"):"");
 status.textContent=result?(result.valid?"VALID":"INVALID: "+result.errors.join(" ")): "Awaiting validation";card.append(status);
 const subject=document.createElement("p");subject.textContent="Subject: "+(root.metadata?.subject||"Missing");card.append(subject);
 const fingerprint=document.createElement("code");fingerprint.textContent="SHA-256: "+(root.metadata?.expected_pem_sha256||"Missing");card.append(fingerprint);return card;
}));}
async function validate(){try{const response=await fetch("/api/validate",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({roots})});if(!response.ok)throw new Error("Validation request failed ("+response.status+")");const data=await response.json();render(data.results);const invalid=data.results.filter(r=>!r.valid);setAlert(invalid.length?invalid.length+" invalid root(s): "+invalid.flatMap(r=>r.errors).join(" "):"All "+data.results.length+" root(s) validated.",invalid.length?"error":"ok");}catch(error){setAlert("Validation error: "+error.message,"error");}}
async function load(){try{const response=await fetch("/api/roots");if(!response.ok)throw new Error("Root reload failed ("+response.status+")");const data=await response.json();roots=data.roots;render();setAlert(roots.length+" root(s) loaded; validating now.","pending");await validate();}catch(error){setAlert("Root load error: "+error.message,"error");}}
document.getElementById("validate").addEventListener("click",validate);document.getElementById("reload").addEventListener("click",load);load();
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def _send_json(self, status: int, payload: object) -> None:
        body = json.dumps(payload, separators=(",", ":")).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/":
            body = HTML.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Security-Policy", "default-src 'self'; connect-src 'self'; style-src 'unsafe-inline'; script-src 'self'")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif path == "/api/roots":
            self._send_json(200, {"roots": ROOTS})
        else:
            self._send_json(404, {"error": "Not found"})

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/api/validate":
            self._send_json(404, {"error": "Not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 1 or length > MAX_BODY_BYTES:
                raise ValueError("Request body must be between 1 and 65536 bytes.")
            payload = json.loads(self.rfile.read(length))
            roots = payload.get("roots")
            if not isinstance(roots, list) or len(roots) > 100:
                raise ValueError("roots must be a list of at most 100 entries.")
        except (json.JSONDecodeError, ValueError) as exc:
            self._send_json(400, {"error": str(exc)})
            return
        self._send_json(200, {"results": [validate_root(root) for root in roots]})

    def log_message(self, format: str, *args: object) -> None:
        return


if __name__ == "__main__":
    HTTPServer((HOST, PORT), Handler).serve_forever()
