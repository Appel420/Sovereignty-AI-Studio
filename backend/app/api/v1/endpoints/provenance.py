"""Offline provenance endpoints backed by the existing Merkle/SHA-256 implementation."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()

Sha256Hex = Annotated[
    str,
    Field(
        min_length=64,
        max_length=64,
        pattern=r"^[0-9a-fA-F]{64}$",
    ),
]


class MerkleProofPayload(BaseModel):
    proof_type: str = Field(default="merkle")
    algorithm: str = Field(default="sha256")
    leaf_index: int = Field(ge=0)
    leaf_count: int = Field(ge=1)
    leaf_hash: Sha256Hex
    hashes: list[Sha256Hex] = Field(default_factory=list)
    directions: list[bool] = Field(default_factory=list)
    merkle_root: Sha256Hex
    offline: bool = True


class GenerateProofRequest(BaseModel):
    leaves: list[Any] = Field(min_length=1, max_length=2048)
    leaf_index: int = Field(default=0, ge=0)


class VerifyProofRequest(BaseModel):
    leaf: Any
    proof: MerkleProofPayload


@router.post("/proof/generate", response_model=dict)
async def generate_provenance_proof(request: GenerateProofRequest):
    """Generate an offline Merkle/SHA-256 inclusion proof for the selected leaf."""
    from app.services.provenance_service import provenance_service

    try:
        return provenance_service.generate_proof(request.leaves, request.leaf_index)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/proof/verify", response_model=dict)
async def verify_provenance_proof(request: VerifyProofRequest):
    """Verify an offline Merkle/SHA-256 inclusion proof."""
    from app.services.provenance_service import provenance_service

    try:
        valid = provenance_service.verify_proof(
            request.leaf,
            request.proof.model_dump(),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "valid": valid,
        "proof_type": "merkle",
        "algorithm": "sha256",
        "merkle_root": request.proof.merkle_root,
        "offline": True,
    }
