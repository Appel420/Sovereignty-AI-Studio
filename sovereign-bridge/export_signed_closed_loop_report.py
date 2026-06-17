"""Signed closed-loop report compatibility helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def export_signed_closed_loop_report(
    report: dict[str, Any],
    output_path: str | None = None,
) -> dict[str, Any]:
    payload = {"report": report, "signed": False}
    if output_path:
        path = Path(output_path)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        payload["output_path"] = str(path)
    return payload