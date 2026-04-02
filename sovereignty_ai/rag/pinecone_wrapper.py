"""
Pinecone wrapper with quadruple-ratchet encryption.

Every ``add`` encrypts via the quad ratchet before upserting.
Every ``query`` decrypts only for the session owner.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from sovereignty_ai.rag.base import EncryptedRAGBase
from sovereignty_ai.ratchet import QuadRatchetSession


class PineconeRAG(EncryptedRAGBase):
    """
    Encrypted Pinecone RAG wrapper.

    Parameters
    ----------
    index : object, optional
        A ``pinecone.Index`` instance.  When *None* falls back to an
        in-memory dict store for testing.
    session : QuadRatchetSession, optional
        An existing ratchet session.
    """

    def __init__(
        self,
        *,
        index: Any = None,
        session: Optional[QuadRatchetSession] = None,
    ) -> None:
        super().__init__(session=session)
        self._index = index
        self._mem_store: Dict[str, Dict[str, Any]] = {}

    # -- transport ------------------------------------------------------------

    def _store_blob(self, doc_id: str, encrypted: bytes, metadata: Dict[str, Any]) -> None:
        if self._index is not None:
            metadata["_blob_hex"] = encrypted.hex()
            # Pinecone requires a vector; use a zero-vector placeholder so the
            # encrypted payload travels in metadata.
            self._index.upsert(vectors=[(doc_id, [0.0] * 768, metadata)])
        else:
            self._mem_store[doc_id] = {"blob": encrypted, "meta": metadata}

    def _fetch_blobs(self, query_encrypted: bytes, top_k: int) -> List[Dict[str, Any]]:
        if self._index is not None:
            res = self._index.query(vector=[0.0] * 768, top_k=top_k, include_metadata=True)
            out: List[Dict[str, Any]] = []
            for match in res.get("matches", []):
                meta = match.get("metadata", {})
                blob_hex = meta.pop("_blob_hex", "")
                out.append({
                    "id": match["id"],
                    "blob": bytes.fromhex(blob_hex) if blob_hex else b"",
                    "meta": meta,
                })
            return out
        return [
            {"id": k, "blob": v["blob"], "meta": v.get("meta", {})}
            for k, v in list(self._mem_store.items())[:top_k]
        ]

    def _delete_blob(self, doc_id: str) -> None:
        if self._index is not None:
            self._index.delete(ids=[doc_id])
        else:
            self._mem_store.pop(doc_id, None)
