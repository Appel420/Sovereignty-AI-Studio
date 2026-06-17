"""Compatibility wrapper for the backend media generator service."""

from backend.app.services.media_generator_service import (  # noqa: F401
    GenerationJob,
    GenerationStatus,
    MediaGeneratorService,
    MediaType,
    media_generator_service,
)

__all__ = [
    "GenerationJob",
    "GenerationStatus",
    "MediaGeneratorService",
    "MediaType",
    "media_generator_service",
]