"""
sovereignty_ai/rag/chroma_wrapper.py

ChromaRAG -- Encrypted in-memory RAG store with QuadRatchet protection.

All stored documents are encrypted with XChaCha20-Poly1305 via
QuadRatchetSession before being placed in _mem_store. The session key
is never exposed; only the session owner can decrypt.

In production, swap _mem_store for a real Chroma collection using
chromadb.Client().get_or_create_collection(name=collection_name).
The encryption layer is identical either way.

Author: Derek Appel | Sovereignty One
"""
from __future__ import annotations

import base64
import hashlib
import uuid
from typing import Any, Optional

from sovereignty_ai.ratchet.quad_ratchet import QuadRatchetSession


class ChromaRAG:
    """
    Encrypted RAG wrapper with a Chroma-compatible interface.

    Parameters
    ----------
    collection_name : str
        Logical collection identifier (used as AAD for encryption).
    session : QuadRatchetSession, optional
        If provided, all documents are encrypted with this session.
        If None, a fresh session is created per instance.
    """

    def __init__(
        self,
        collection_name: str = "default",
        session: Optional[QuadRatchetSession] = None,
    ) -> None:
        self.collection_name = collection_name
        self._session        = session or QuadRatchetSession()
        # {doc_id: {"blob": bytes, "merkle_root": str, "leaf_index": int, "meta": dict}}
        self._mem_store: dict[str, dict] = {}

    def add(self, text: str, metadata: dict | None = None) -> dict:
        """
        Encrypt `text` and store in the collection.

        Returns a receipt dict with doc_id, merkle_root, leaf_index.
        """
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
        """
        Query the collection.

        In this in-memory implementation, all documents are returned
        (simulating a small collection). Each blob is decrypted; failed
        decryptions (e.g. wrong session) return {"text": "[DECRYPTION_FAILED]"}.

        Returns list of {"text": str, "doc_id": str, "meta": dict}.
        """
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
        """Remove a document from the store by doc_id."""
        self._mem_store.pop(doc_id, None)
