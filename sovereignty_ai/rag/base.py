"""
Abstract base for encrypted RAG wrappers.

Every concrete wrapper (Chroma, Pinecone, Qdrant, FAISS, Redis, etc.)
inherits from :class:`EncryptedRAGBase` and only needs to implement the
three transport methods that talk to the underlying vector store.

The base class handles:
- quad-ratchet encrypt/decrypt on every ``add`` / ``query``
- Merkle-tree proof generation per insert
- cookie-bound session keys
"""

from __future__ import annotations

import base64
import json
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from sovereignty_ai.ratchet import MerkleTree, QuadRatchetSession


class EncryptedRAGBase(ABC):
    """
    Base class for ratchet-encrypted RAG stores.

    Subclasses must implement:
    - :meth:`_store_blob`   – persist the encrypted blob + metadata
    - :meth:`_fetch_blobs`  – retrieve candidate blobs for a query
    - :meth:`_delete_blob`  – remove a blob by id (optional)
    """

    def __init__(self, *, session: Optional[QuadRatchetSession] = None) -> None:
        self.session = session or QuadRatchetSession()

    # -- abstract transport ---------------------------------------------------

    @abstractmethod
    def _store_blob(self, doc_id: str, encrypted: bytes, metadata: Dict[str, Any]) -> None:
        """Persist *encrypted* bytes under *doc_id* with *metadata*."""

    @abstractmethod
    def _fetch_blobs(self, query_encrypted: bytes, top_k: int) -> List[Dict[str, Any]]:
        """
        Return up to *top_k* results.

        Each dict must contain at least ``{"id": str, "blob": bytes}``.
        """

    @abstractmethod
    def _delete_blob(self, doc_id: str) -> None:
        """Remove *doc_id* from the store."""

    # -- public API -----------------------------------------------------------

    def add(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Encrypt *text* through the quad ratchet and store it.

        Returns a receipt dict with ``doc_id``, ``merkle_root``, and ``leaf_index``.
        """
        blob, proof = self.session.encrypt_text(text)
        doc_id = base64.urlsafe_b64encode(proof["merkle_root"][:12]).decode()
        meta = metadata or {}
        meta["leaf_index"] = proof["leaf_index"]
        meta["merkle_root"] = base64.urlsafe_b64encode(proof["merkle_root"]).decode()
        meta["sig"] = base64.urlsafe_b64encode(proof["sig"]).decode()
        meta["dh_pub"] = base64.urlsafe_b64encode(proof["dh_pub"]).decode()
        meta["pq_ct"] = base64.urlsafe_b64encode(proof["pq_ct"]).decode()

        self._store_blob(doc_id, blob, meta)

        return {
            "doc_id": doc_id,
            "leaf_index": proof["leaf_index"],
            "merkle_root": meta["merkle_root"],
        }

    def query(self, text: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Encrypt the query, fetch candidates, decrypt results.

        Only the session owner can decrypt — anyone else sees gibberish.
        """
        query_blob, _ = self.session.encrypt_text(text)
        results = self._fetch_blobs(query_blob, top_k)
        decrypted: List[Dict[str, Any]] = []
        for r in results:
            blob = r.get("blob", b"")
            if not blob:
                continue
            try:
                plain = self.session.decrypt_text(blob)
            except Exception:
                plain = "<ratchet: undecryptable — not your session>"
            decrypted.append({"id": r.get("id", ""), "text": plain, "meta": r.get("meta", {})})
        return decrypted
