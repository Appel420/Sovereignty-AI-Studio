"""
sovereignty_ai/rag/pinecone_wrapper.py

PineconeRAG -- Encrypted in-memory RAG store with QuadRatchet protection.
Same interface as ChromaRAG; swappable with a real Pinecone client in production.

Author: Derek Appel | Sovereignty One
"""
from __future__ import annotations

import uuid
from typing import Optional

from sovereignty_ai.ratchet.quad_ratchet import QuadRatchetSession


class PineconeRAG:
    """
    Encrypted RAG wrapper with a Pinecone-compatible interface.

    In production, replace _mem_store operations with:
      pinecone.Index(index_name).upsert(...)
      pinecone.Index(index_name).query(...)
    The encryption layer remains identical.
    """

    def __init__(
        self,
        index_name: str = "sovereign-rag",
        session: Optional[QuadRatchetSession] = None,
    ) -> None:
        self.index_name  = index_name
        self._session    = session or QuadRatchetSession()
        self._mem_store: dict[str, dict] = {}

    def add(self, text: str, metadata: dict | None = None) -> dict:
        """Encrypt `text` and store. Returns receipt with doc_id and merkle_root."""
        blob, proof = self._session.encrypt_text(text)
        doc_id = str(uuid.uuid4())
        self._mem_store[doc_id] = {
            "blob":        blob,
            "merkle_root": proof["merkle_root"],
            "leaf_index":  proof["leaf_index"],
            "meta":        metadata or {},
        }
        return {
            "doc_id":      doc_id,
            "merkle_root": proof["merkle_root"],
            "leaf_index":  proof["leaf_index"],
        }

    def query(self, query_text: str, top_k: int = 10) -> list[dict]:
        """Decrypt and return all stored documents (in-memory full-scan)."""
        results = []
        for doc_id, entry in self._mem_store.items():
            try:
                text = self._session.decrypt_text(entry["blob"])
            except Exception:
                text = "[DECRYPTION_FAILED]"
            results.append({
                "text":        text,
                "doc_id":      doc_id,
                "meta":        entry["meta"],
                "merkle_root": entry["merkle_root"],
            })
        return results[:top_k]

    def _delete_blob(self, doc_id: str) -> None:
        self._mem_store.pop(doc_id, None)
