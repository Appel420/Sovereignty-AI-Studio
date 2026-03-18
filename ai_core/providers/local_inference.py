"""
Sovereignty AI Studio — Local Inference Providers
Loads GGUF models via llama-cpp-python and ONNX models via onnxruntime.
No Ollama wrapper. No external API calls.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Generator, List, Optional

logger = logging.getLogger(__name__)


class _BaseLocalProvider:
    """Shared health-check interface."""

    def health(self) -> Dict[str, Any]:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# GGUF provider — via llama-cpp-python
# ---------------------------------------------------------------------------

class GGUFProvider(_BaseLocalProvider):
    """
    Loads a GGUF model file and serves inference locally.

    Requirements:
        pip install llama-cpp-python

    Set SOVEREIGN_MODEL_PATH or pass model_path at init.
    """

    def __init__(self, model_path: Optional[str] = None):
        self._model_path = model_path or os.getenv("SOVEREIGN_MODEL_PATH", "")
        self._llm: Any = None

    def _load_model(self) -> None:
        if self._llm is not None:
            return
        if not self._model_path:
            raise RuntimeError(
                "SOVEREIGN_MODEL_PATH not set. "
                "Set env var or pass model_path to GGUFProvider."
            )
        try:
            from llama_cpp import Llama  # type: ignore[import]

            logger.info("Loading GGUF model from %s", self._model_path)
            self._llm = Llama(
                model_path=self._model_path,
                n_ctx=4096,
                n_threads=os.cpu_count() or 4,
                verbose=False,
            )
            logger.info("GGUF model loaded")
        except ImportError as exc:
            raise RuntimeError(
                "llama-cpp-python not installed. "
                "Run: pip install llama-cpp-python"
            ) from exc

    def chat(
        self,
        messages: List[Dict[str, str]],
        *,
        context: Optional[Dict[str, str]] = None,
        max_tokens: int = 1200,
        stream: bool = False,
    ) -> str | Generator[str, None, None]:
        self._load_model()
        prompt = _messages_to_prompt(messages)

        if stream:
            return self._stream(prompt, max_tokens)

        output = self._llm(
            prompt,
            max_tokens=max_tokens,
            stop=["</s>", "Human:", "User:"],
            echo=False,
        )
        return output["choices"][0]["text"].strip()

    def _stream(self, prompt: str, max_tokens: int) -> Generator[str, None, None]:
        for chunk in self._llm(
            prompt,
            max_tokens=max_tokens,
            stop=["</s>", "Human:", "User:"],
            stream=True,
            echo=False,
        ):
            text = chunk["choices"][0]["text"]
            if text:
                yield text

    def health(self) -> Dict[str, Any]:
        available = bool(self._model_path and os.path.exists(self._model_path))
        return {
            "ok": available,
            "provider": "local_gguf",
            "model_path": self._model_path,
            "loaded": self._llm is not None,
        }


# ---------------------------------------------------------------------------
# ONNX provider — via onnxruntime
# ---------------------------------------------------------------------------

class ONNXProvider(_BaseLocalProvider):
    """
    Loads an ONNX model file for local text inference.

    Requirements:
        pip install onnxruntime

    Set SOVEREIGN_ONNX_PATH or pass onnx_path at init.
    """

    def __init__(self, onnx_path: Optional[str] = None):
        self._onnx_path = onnx_path or os.getenv("SOVEREIGN_ONNX_PATH", "")
        self._session: Any = None
        self._tokenizer: Any = None

    def _load_model(self) -> None:
        if self._session is not None:
            return
        if not self._onnx_path:
            raise RuntimeError(
                "SOVEREIGN_ONNX_PATH not set. "
                "Set env var or pass onnx_path to ONNXProvider."
            )
        try:
            import onnxruntime as ort  # type: ignore[import]

            logger.info("Loading ONNX model from %s", self._onnx_path)
            self._session = ort.InferenceSession(
                self._onnx_path,
                providers=["CPUExecutionProvider"],
            )
            logger.info("ONNX model loaded")
        except ImportError as exc:
            raise RuntimeError(
                "onnxruntime not installed. Run: pip install onnxruntime"
            ) from exc

    def chat(
        self,
        messages: List[Dict[str, str]],
        *,
        context: Optional[Dict[str, str]] = None,
        max_tokens: int = 1200,
        stream: bool = False,
    ) -> str:
        self._load_model()
        # ONNX inference — input/output names depend on the specific model.
        # Override this method or subclass for model-specific I/O binding.
        inputs = self._session.get_inputs()
        if not inputs:
            raise RuntimeError("ONNX model has no inputs.")
        logger.debug("ONNX inputs: %s", [i.name for i in inputs])
        raise NotImplementedError(
            "ONNXProvider.chat() requires model-specific I/O binding. "
            "Subclass ONNXProvider and implement chat() for your ONNX model."
        )

    def health(self) -> Dict[str, Any]:
        available = bool(self._onnx_path and os.path.exists(self._onnx_path))
        return {
            "ok": available,
            "provider": "local_onnx",
            "onnx_path": self._onnx_path,
            "loaded": self._session is not None,
        }


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _messages_to_prompt(messages: List[Dict[str, str]]) -> str:
    """Convert OpenAI-style messages to a simple prompt string."""
    parts: List[str] = []
    for msg in messages:
        role = msg.get("role", "user").capitalize()
        content = msg.get("content", "")
        parts.append(f"{role}: {content}")
    parts.append("Assistant:")
    return "\n".join(parts)
