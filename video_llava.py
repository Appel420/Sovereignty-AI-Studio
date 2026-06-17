"""Lightweight video analysis compatibility helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class VideoLlavaService:
    """Minimal stand-in for the missing video LLaVA service."""

    model_name: str = "video-llava"
    metadata: dict[str, Any] = field(default_factory=dict)

    def describe(self, video_path: str) -> dict[str, Any]:
        path = Path(video_path)
        return {
            "service": self.model_name,
            "video_path": str(path),
            "exists": path.exists(),
            "status": "not_implemented",
        }

    def get_status(self) -> dict[str, Any]:
        return {"service": self.model_name, "status": "online"}


video_llava = VideoLlavaService()