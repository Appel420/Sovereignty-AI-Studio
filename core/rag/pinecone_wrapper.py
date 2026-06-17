"""Compatibility in-memory Pinecone wrapper."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PineconeRAG:
    index_name: str = "default"
    records: list[dict[str, Any]] = field(default_factory=list)

    def upsert(self, document_id: str, text: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        record = {"id": document_id, "text": text, "metadata": metadata or {}}
        self.records = [doc for doc in self.records if doc["id"] != document_id]
        self.records.append(record)
        return record

    def query(self, text: str, limit: int = 5) -> list[dict[str, Any]]:
        tokens = set(text.lower().split())
        ranked = sorted(
            self.records,
            key=lambda document: len(tokens & set(str(document["text"]).lower().split())),
            reverse=True,
        )
        return ranked[:limit]

    def status(self) -> dict[str, Any]:
        return {"service": "pinecone", "index_name": self.index_name, "record_count": len(self.records)}