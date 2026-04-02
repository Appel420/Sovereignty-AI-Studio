"""
Tests for the quadruple-ratchet layer and encrypted RAG wrappers.

Covers:
- Merkle tree append, root computation, proof generation + verification
- seal / unseal (XChaCha20-Poly1305 round-trip)
- QuadRatchetSession encrypt / decrypt round-trip
- Forward-secrecy: dropped message is gibberish to new session
- ChromaRAG, PineconeRAG, QdrantRAG in-memory add / query
- "copper tag flip" end-to-end smoke test
"""

import base64
import pytest
from sovereignty_ai.ratchet.merkle import MerkleTree, MerkleProof
from sovereignty_ai.ratchet.quad_ratchet import (
    QuadRatchetSession,
    seal,
    unseal,
    _kdf_chain,
    CHAIN_KEY_LEN,
)
from sovereignty_ai.rag.chroma_wrapper import ChromaRAG
from sovereignty_ai.rag.pinecone_wrapper import PineconeRAG
from sovereignty_ai.rag.qdrant_wrapper import QdrantRAG


# ── Merkle tree ──────────────────────────────────────────────────────────────

class TestMerkleTree:
    def test_empty_root_is_zero(self):
        tree = MerkleTree()
        assert tree.root == b"\x00" * 32

    def test_single_leaf(self):
        tree = MerkleTree()
        idx = tree.append(b"hello")
        assert idx == 0
        assert len(tree.root) == 32
        assert tree.root != b"\x00" * 32

    def test_two_leaves_different_root(self):
        tree = MerkleTree()
        tree.append(b"a")
        root1 = tree.root
        tree.append(b"b")
        root2 = tree.root
        assert root1 != root2

    def test_proof_single_leaf(self):
        tree = MerkleTree()
        tree.append(b"data")
        proof = tree.proof(0)
        assert proof.verify(tree.root)

    def test_proof_multiple_leaves(self):
        tree = MerkleTree()
        for i in range(7):
            tree.append(f"leaf-{i}".encode())
        root = tree.root
        for i in range(7):
            proof = tree.proof(i)
            assert proof.verify(root), f"proof failed for leaf {i}"

    def test_proof_bad_root_fails(self):
        tree = MerkleTree()
        tree.append(b"x")
        proof = tree.proof(0)
        assert not proof.verify(b"\xff" * 32)

    def test_proof_out_of_range(self):
        tree = MerkleTree()
        tree.append(b"x")
        with pytest.raises(IndexError):
            tree.proof(5)


# ── XChaCha20-Poly1305 seal / unseal ────────────────────────────────────────

class TestSealUnseal:
    def test_round_trip(self):
        key = b"\x42" * 32
        plain = b"Sovereignty AI"
        blob = seal(key, plain)
        assert unseal(key, blob) == plain

    def test_wrong_key_fails(self):
        key = b"\x42" * 32
        bad = b"\x00" * 32
        blob = seal(key, b"data")
        with pytest.raises(Exception):
            unseal(bad, blob)

    def test_aad_mismatch_fails(self):
        key = b"\x42" * 32
        blob = seal(key, b"data", aad=b"ctx")
        with pytest.raises(Exception):
            unseal(key, blob, aad=b"wrong")


# ── QuadRatchetSession ──────────────────────────────────────────────────────

class TestQuadRatchetSession:
    def test_encrypt_decrypt_round_trip(self):
        """Encrypt and immediately decrypt with the same session."""
        session = QuadRatchetSession()
        blob, proof = session.encrypt_text("copper tag flip")

        assert isinstance(blob, bytes)
        assert len(blob) > 0
        assert "sig" in proof
        assert "merkle_root" in proof
        assert "leaf_index" in proof
        assert "dh_pub" in proof
        assert "pq_ct" in proof

        plain = session.decrypt_text(blob)
        assert plain == "copper tag flip"

    def test_merkle_root_changes_on_each_encrypt(self):
        session = QuadRatchetSession()
        _, p1 = session.encrypt(b"a")
        _, p2 = session.encrypt(b"b")
        assert p1["merkle_root"] != p2["merkle_root"]

    def test_forward_secrecy_different_session(self):
        """A second session cannot decrypt blobs from the first."""
        s1 = QuadRatchetSession()
        blob, _ = s1.encrypt_text("secret")

        s2 = QuadRatchetSession()
        with pytest.raises(Exception):
            s2.decrypt_text(blob)

    def test_kdf_chain_advances(self):
        ck = b"\x01" * CHAIN_KEY_LEN
        ck2, mk = _kdf_chain(ck)
        assert len(ck2) == CHAIN_KEY_LEN
        assert len(mk) == CHAIN_KEY_LEN
        assert ck2 != ck
        assert mk != ck

    def test_multiple_messages_each_unique_blob(self):
        session = QuadRatchetSession()
        blobs = set()
        for i in range(5):
            b, _ = session.encrypt(f"msg-{i}".encode())
            blobs.add(b)
        assert len(blobs) == 5


# ── In-memory RAG wrappers ──────────────────────────────────────────────────

class TestChromaRAG:
    def test_add_returns_receipt(self):
        rag = ChromaRAG(collection_name="test")
        receipt = rag.add("copper tag flip")
        assert "doc_id" in receipt
        assert "merkle_root" in receipt
        assert receipt["leaf_index"] == 0

    def test_add_query_round_trip(self):
        session = QuadRatchetSession()
        rag = ChromaRAG(collection_name="test", session=session)
        rag.add("copper tag flip", {"category": "test"})
        results = rag.query("copper")
        assert len(results) >= 1
        # The first result should decrypt successfully
        assert results[0]["text"] == "copper tag flip"

    def test_delete(self):
        rag = ChromaRAG(collection_name="test")
        receipt = rag.add("to delete")
        rag._delete_blob(receipt["doc_id"])
        assert len(rag._mem_store) == 0


class TestPineconeRAG:
    def test_add_returns_receipt(self):
        rag = PineconeRAG()
        receipt = rag.add("copper tag flip")
        assert "doc_id" in receipt
        assert "merkle_root" in receipt

    def test_add_query_round_trip(self):
        session = QuadRatchetSession()
        rag = PineconeRAG(session=session)
        rag.add("copper tag flip")
        results = rag.query("copper")
        assert len(results) >= 1
        assert results[0]["text"] == "copper tag flip"


class TestQdrantRAG:
    def test_add_returns_receipt(self):
        rag = QdrantRAG()
        receipt = rag.add("copper tag flip")
        assert "doc_id" in receipt
        assert "merkle_root" in receipt

    def test_add_query_round_trip(self):
        session = QuadRatchetSession()
        rag = QdrantRAG(session=session)
        rag.add("copper tag flip")
        results = rag.query("copper")
        assert len(results) >= 1
        assert results[0]["text"] == "copper tag flip"


# ── "copper tag flip" end-to-end smoke test ─────────────────────────────────

class TestCopperTagFlipE2E:
    """
    Add "copper tag flip" to each wrapper, verify:
    1. Encrypted blob lands (not plaintext)
    2. Merkle proof is attached
    3. Query decrypts only for the session owner
    """

    @pytest.fixture(params=["chroma", "pinecone", "qdrant"])
    def rag(self, request):
        session = QuadRatchetSession()
        if request.param == "chroma":
            return ChromaRAG(session=session)
        elif request.param == "pinecone":
            return PineconeRAG(session=session)
        else:
            return QdrantRAG(session=session)

    def test_encrypted_blob_not_plaintext(self, rag):
        receipt = rag.add("copper tag flip")
        # The stored blob should NOT contain the plaintext
        for entry in rag._mem_store.values():
            assert b"copper tag flip" not in entry["blob"]

    def test_merkle_root_attached(self, rag):
        receipt = rag.add("copper tag flip")
        assert receipt["merkle_root"]
        # Should be valid base64
        raw = base64.urlsafe_b64decode(receipt["merkle_root"])
        assert len(raw) == 32

    def test_only_owner_decrypts(self, rag):
        rag.add("copper tag flip")
        results = rag.query("test")
        assert len(results) == 1
        assert results[0]["text"] == "copper tag flip"

        # A fresh session cannot decrypt
        stranger = QuadRatchetSession()
        other_rag = ChromaRAG(session=stranger)
        other_rag._mem_store = rag._mem_store
        results2 = other_rag.query("test")
        assert results2[0]["text"] != "copper tag flip"
