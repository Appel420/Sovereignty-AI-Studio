"""
Encrypted RAG wrappers — every add / query goes through the quad ratchet.

Public API
----------
- :class:`EncryptedRAGBase` – abstract base
- :class:`ChromaRAG`        – ChromaDB wrapper
- :class:`PineconeRAG`      – Pinecone wrapper
- :class:`QdrantRAG`        – Qdrant wrapper
"""

from sovereignty_ai.rag.base import EncryptedRAGBase
from sovereignty_ai.rag.chroma_wrapper import ChromaRAG
from sovereignty_ai.rag.pinecone_wrapper import PineconeRAG
from sovereignty_ai.rag.qdrant_wrapper import QdrantRAG

__all__ = [
    "EncryptedRAGBase",
    "ChromaRAG",
    "PineconeRAG",
    "QdrantRAG",
]
