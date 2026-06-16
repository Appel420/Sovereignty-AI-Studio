"""Closed-loop orchestration compatibility helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ClosedLoopOrchestrator:
    steps: list[str] = field(default_factory=list)
    running: bool = False

    def add_step(self, step: str) -> None:
        self.steps.append(step)

    def run(self) -> dict[str, Any]:
        self.running = True
        return {"status": "completed", "steps": list(self.steps)}

    def stop(self) -> None:
        self.running = False