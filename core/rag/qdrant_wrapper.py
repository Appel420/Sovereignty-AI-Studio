"""Compatibility in-memory Qdrant wrapper."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class QdrantRAG:
    collection_name: str = "default"
    points: list[dict[str, Any]] = field(default_factory=list)

    def upsert(self, point_id: str, text: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        point = {"id": point_id, "text": text, "metadata": metadata or {}}
        self.points = [record for record in self.points if record["id"] != point_id]
        self.points.append(point)
        return point

    def query(self, text: str, limit: int = 5) -> list[dict[str, Any]]:
        tokens = set(text.lower().split())
        ranked = sorted(
            self.points,
            key=lambda point: len(tokens & set(str(point["text"]).lower().split())),
            reverse=True,
        )
        return ranked[:limit]

    def status(self) -> dict[str, Any]:
        return {
            "service": "qdrant",
            "collection_name": self.collection_name,
            "point_count": len(self.points),
        }