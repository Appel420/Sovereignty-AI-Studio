"""
Qdrant wrapper with quadruple-ratchet encryption.

Every ``add`` encrypts via the quad ratchet before upserting.
Every ``query`` decrypts only for the session owner.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from sovereignty_ai.rag.base import EncryptedRAGBase
from sovereignty_ai.ratchet import QuadRatchetSession


class QdrantRAG(EncryptedRAGBase):
    """
    Encrypted Qdrant RAG wrapper.

    Parameters
    ----------
    client : object, optional
        A ``qdrant_client.QdrantClient`` instance.  Falls back to in-memory
        when *None*.
    collection_name : str
        Qdrant collection name.
    session : QuadRatchetSession, optional
        An existing ratchet session.
    """

    def __init__(
        self,
        *,
        client: Any = None,
        collection_name: str = "default",
        session: Optional[QuadRatchetSession] = None,
    ) -> None:
        super().__init__(session=session)
        self._client = client
        self.collection_name = collection_name
        self._mem_store: Dict[str, Dict[str, Any]] = {}

    # -- transport ------------------------------------------------------------

    def _store_blob(self, doc_id: str, encrypted: bytes, metadata: Dict[str, Any]) -> None:
        if self._client is not None:
            from qdrant_client.models import PointStruct

            point = PointStruct(
                id=str(uuid.uuid4()),
                vector=[0.0] * 768,
                payload={"doc_id": doc_id, "_blob_hex": encrypted.hex(), **metadata},
            )
            self._client.upsert(collection_name=self.collection_name, points=[point])
        else:
            self._mem_store[doc_id] = {"blob": encrypted, "meta": metadata}

    def _fetch_blobs(self, query_encrypted: bytes, top_k: int) -> List[Dict[str, Any]]:
        if self._client is not None:
            results = self._client.search(
                collection_name=self.collection_name,
                query_vector=[0.0] * 768,
                limit=top_k,
            )
            out: List[Dict[str, Any]] = []
            for point in results:
                payload = point.payload or {}
                blob_hex = payload.pop("_blob_hex", "")
                out.append({
                    "id": payload.get("doc_id", ""),
                    "blob": bytes.fromhex(blob_hex) if blob_hex else b"",
                    "meta": payload,
                })
            return out
        return [
            {"id": k, "blob": v["blob"], "meta": v.get("meta", {})}
            for k, v in list(self._mem_store.items())[:top_k]
        ]

    def _delete_blob(self, doc_id: str) -> None:
        if self._client is not None:
            from qdrant_client.models import Filter, FieldCondition, MatchValue

            self._client.delete(
                collection_name=self.collection_name,
                points_selector=Filter(
                    must=[FieldCondition(key="doc_id", match=MatchValue(value=doc_id))]
                ),
            )
        else:
            self._mem_store.pop(doc_id, None)
