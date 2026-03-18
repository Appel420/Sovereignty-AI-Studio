"""
Sovereignty AI Studio — Sovereign API Provider
Calls a self-hosted sovereign API endpoint. JWT-authenticated.
No external SaaS calls — your own infrastructure only.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SovereignAPIProvider:
    """
    HTTP client for a self-hosted sovereign AI API endpoint.

    The endpoint must accept POST requests with JSON body:
        {"messages": [...], "max_tokens": int, "stream": bool}

    Authentication is via Bearer JWT from the SOVEREIGN_API_JWT env var.
    """

    def __init__(
        self,
        api_url: Optional[str] = None,
        jwt_token: Optional[str] = None,
        timeout: int = 60,
    ):
        self._api_url = (
            api_url
            or os.getenv("SOVEREIGN_API_URL", "http://localhost:9898/api/ai")
        ).rstrip("/")
        self._jwt = jwt_token or os.getenv("SOVEREIGN_API_JWT", "")
        self._timeout = timeout

    def chat(
        self,
        messages: List[Dict[str, str]],
        *,
        context: Optional[Dict[str, str]] = None,
        max_tokens: int = 1200,
        stream: bool = False,
    ) -> str:
        """Send a chat request to the self-hosted sovereign API."""
        endpoint = f"{self._api_url}/chat"
        payload = {
            "messages": messages,
            "max_tokens": max_tokens,
            "stream": False,  # streaming requires SSE — handle separately
            "context": context or {},
        }
        data = json.dumps(payload).encode("utf-8")
        headers: Dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self._jwt:
            headers["Authorization"] = f"Bearer {self._jwt}"

        req = urllib.request.Request(
            endpoint,
            data=data,
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise RuntimeError(
                f"Sovereign API HTTP {exc.code}: {exc.read().decode()}"
            ) from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(
                f"Sovereign API connection error ({self._api_url}): {exc.reason}"
            ) from exc

        return self._extract_text(body)

    def health(self) -> Dict[str, Any]:
        """Ping the /health endpoint of the sovereign API."""
        try:
            req = urllib.request.Request(
                f"{self._api_url}/health",
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                ok = resp.status == 200
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "provider": "sovereign_api", "error": str(exc)}
        return {"ok": ok, "provider": "sovereign_api", "url": self._api_url}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_text(body: Dict[str, Any]) -> str:
        """Extract the response text from common API response formats."""
        # OpenAI-compatible format
        choices = body.get("choices")
        if choices and isinstance(choices, list):
            msg = choices[0].get("message") or {}
            return msg.get("content", "").strip()

        # Simple {text: "..."} format
        if "text" in body:
            return str(body["text"]).strip()

        # {response: "..."} format
        if "response" in body:
            return str(body["response"]).strip()

        raise RuntimeError(
            f"Unrecognized sovereign API response format: {list(body.keys())}"
        )
