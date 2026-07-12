#!/usr/bin/env python3
"""
loop_guard.py
Stops AI from repeating the same answer and forces forward progress.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Dict, List


@dataclass
class LoopGuard:
    max_history: int = 8
    similarity_threshold: float = 0.88
    repeat_limit: int = 2
    outputs: List[str] = field(default_factory=list)
    hashes: Dict[str, int] = field(default_factory=dict)
    _fingerprints: List[str] = field(default_factory=list, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.max_history < 1:
            raise ValueError("max_history must be at least 1")
        if not 0.0 <= self.similarity_threshold <= 1.0:
            raise ValueError("similarity_threshold must be between 0 and 1")
        if self.repeat_limit < 2:
            raise ValueError("repeat_limit must be at least 2")

    def normalize(self, text: str) -> str:
        text = text.lower().strip()
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"[^\w\s\-./]", "", text)
        return text

    def fingerprint(self, text: str) -> str:
        normalized = self.normalize(text)
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def similarity(self, a: str, b: str) -> float:
        return SequenceMatcher(None, self.normalize(a), self.normalize(b)).ratio()

    def _record_output(self, model_output: str, fingerprint: str) -> None:
        self.outputs.append(model_output)
        self._fingerprints.append(fingerprint)
        self.hashes[fingerprint] = self.hashes.get(fingerprint, 0) + 1

        while len(self.outputs) > self.max_history:
            removed_fp = self._fingerprints.pop(0)
            self.outputs.pop(0)
            remaining = self.hashes[removed_fp] - 1
            if remaining <= 0:
                self.hashes.pop(removed_fp, None)
            else:
                self.hashes[removed_fp] = remaining

    def check(self, user_input: str, model_output: str) -> dict:
        fp = self.fingerprint(model_output)
        exact_count = self.hashes.get(fp, 0) + 1
        near_repeats = sum(
            1 for old in self.outputs if self.similarity(old, model_output) >= self.similarity_threshold
        )
        semantic_count = near_repeats + 1

        self._record_output(model_output, fp)

        if exact_count >= self.repeat_limit or semantic_count >= self.repeat_limit:
            return {
                "action": "break_loop",
                "reason": "repeat_detected",
                "replacement": self.forward_progress_prompt(user_input),
            }

        return {
            "action": "continue",
            "reason": "unique_enough",
        }

    def forward_progress_prompt(self, user_input: str) -> str:
        return (
            "Loop detected. Do not repeat the prior answer. "
            "Move forward with one concrete next action. "
            "Provide either a patch, a decision, a file classification, "
            "or a specific command. "
            f"Current user request: {user_input}"
        )


if __name__ == "__main__":
    guard = LoopGuard()

    user = "Fix the architecture drift problem."
    outputs = [
        "We need to prevent drift by creating governance documents.",
        "We need to prevent drift by creating governance documents.",
        "We need to prevent drift by creating governance documents.",
    ]

    for output in outputs:
        result = guard.check(user, output)
        print(result)
