"""Compatibility in-memory RAG wrapper."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ChromaRAG:
    collection_name: str = "default"
    documents: list[dict[str, Any]] = field(default_factory=list)

    def upsert(self, document_id: str, text: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        record = {"id": document_id, "text": text, "metadata": metadata or {}}
        self.documents = [doc for doc in self.documents if doc["id"] != document_id]
        self.documents.append(record)
        return record

    def query(self, text: str, limit: int = 5) -> list[dict[str, Any]]:
        tokens = set(text.lower().split())

        def score(document: dict[str, Any]) -> int:
            return len(tokens & set(str(document["text"]).lower().split()))

        return sorted(self.documents, key=score, reverse=True)[:limit]

    def status(self) -> dict[str, Any]:
        return {
            "service": "chroma",
            "collection_name": self.collection_name,
            "document_count": len(self.documents),
        }