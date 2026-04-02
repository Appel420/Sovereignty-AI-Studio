"""
ChromaDB wrapper with quadruple-ratchet encryption.

Every ``add`` encrypts via the quad ratchet before storing.
Every ``query`` decrypts only for the session owner.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from sovereignty_ai.rag.base import EncryptedRAGBase
from sovereignty_ai.ratchet import QuadRatchetSession


class ChromaRAG(EncryptedRAGBase):
    """
    Encrypted ChromaDB RAG wrapper.

    Parameters
    ----------
    collection_name : str
        Name of the Chroma collection.
    client : object, optional
        A ``chromadb.Client`` instance.  When *None* the wrapper falls back
        to an in-memory dict store so the ratchet layer can be tested
        without the chromadb package installed.
    session : QuadRatchetSession, optional
        An existing ratchet session.  A fresh one is created when omitted.
    """

    def __init__(
        self,
        collection_name: str = "default",
        *,
        client: Any = None,
        session: Optional[QuadRatchetSession] = None,
    ) -> None:
        super().__init__(session=session)
        self.collection_name = collection_name
        self._client = client
        self._collection: Any = None
        # in-memory fallback
        self._mem_store: Dict[str, Dict[str, Any]] = {}

        if self._client is not None:
            self._collection = self._client.get_or_create_collection(collection_name)

    # -- transport ------------------------------------------------------------

    def _store_blob(self, doc_id: str, encrypted: bytes, metadata: Dict[str, Any]) -> None:
        if self._collection is not None:
            self._collection.add(
                ids=[doc_id],
                documents=[encrypted.hex()],
                metadatas=[metadata],
            )
        else:
            self._mem_store[doc_id] = {"blob": encrypted, "meta": metadata}

    def _fetch_blobs(self, query_encrypted: bytes, top_k: int) -> List[Dict[str, Any]]:
        if self._collection is not None:
            res = self._collection.query(
                query_texts=[query_encrypted.hex()],
                n_results=top_k,
            )
            out: List[Dict[str, Any]] = []
            for doc_id, doc in zip(res["ids"][0], res["documents"][0]):
                out.append({"id": doc_id, "blob": bytes.fromhex(doc)})
            return out
        # in-memory: return all (unranked)
        return [
            {"id": k, "blob": v["blob"], "meta": v.get("meta", {})}
            for k, v in list(self._mem_store.items())[:top_k]
        ]

    def _delete_blob(self, doc_id: str) -> None:
        if self._collection is not None:
            self._collection.delete(ids=[doc_id])
        else:
            self._mem_store.pop(doc_id, None)
