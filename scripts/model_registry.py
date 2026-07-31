#!/usr/bin/env python3
"""
Sovereign Model Registry for Sovereignty Playground

- Grok-4.5-build is THE authoritative default model.
- Judge model (judge-grok-4.5) routes all complex selection logic.
- Hard fail-closed blocking of Gemini, Siri cloud, Meta/Llama, Claude, GPT external providers.
- Thread-safe with SCAR emission on every mutation.
- Designed for full offline/local execution per Playground architecture.
- Integrates with existing AuthorityGate / SCAR / PolicyGate / OfflineExecutor chain.

No cloud fallbacks. No placeholders. Production zero-tolerance.
"""

import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional, Any

# --- SCAR hook (replace with your real scar_logger.emit_scar when wired) ---
def emit_scar(event_type: str, payload: Dict[str, Any]) -> None:
    """Minimal SCAR emission stub. Replace with real immutable logger."""
    timestamp = time.time()
    print(f"[SCAR] {timestamp:.0f} | {event_type} | {payload}")


class ModelProvider(Enum):
    LOCAL_GROK = "local_grok"
    JUDGE = "judge"
    BLOCKED = "blocked"          # Gemini, SiriIntelligence, Meta, Llama, Claude, GPT external, etc.


@dataclass(frozen=True)
class ModelConfig:
    name: str
    endpoint: Optional[str] = None
    provider: ModelProvider = ModelProvider.LOCAL_GROK
    priority: int = 100
    policy: str = "default"


class ModelRegistry:
    """
    Thread-safe sovereign model registry.
    Grok is default. External cloud providers are blocked at the gate.
    """

    def __init__(self):
        self._models: Dict[str, ModelConfig] = {}
        self._lock = threading.RLock()
        self._init_sovereign_defaults()

    def _init_sovereign_defaults(self) -> None:
        """Seed the registry with the only allowed sovereign models."""
        with self._lock:
            # Primary local Grok (your running endpoint)
            self._models["grok-4.5-build"] = ModelConfig(
                name="grok-4.5-build",
                endpoint="http://127.0.0.1:9899/api/generate",
                provider=ModelProvider.LOCAL_GROK,
                priority=100,
                policy="sovereign-default"
            )

            # Judge model — single source of truth for routing decisions
            self._models["judge-grok-4.5"] = ModelConfig(
                name="judge-grok-4.5",
                endpoint="http://127.0.0.1:9899/api/generate",
                provider=ModelProvider.JUDGE,
                priority=200,
                policy="judge-routing"
            )

            emit_scar("model_registry_initialized", {
                "defaults": ["grok-4.5-build", "judge-grok-4.5"]
            })

    def _is_blocked(self, model_name: str) -> bool:
        """Hard block list for Gemini/Siri cloud / Meta / Llama / external providers."""
        blocked_keywords = {
            "gemini", "geminiservice", "siri", "siriintelligence",
            "llama", "paligemma", "metalLlamaDaemon",
            "meta", "claude", "anthropic", "gpt", "openai"
        }
        normalized = model_name.lower()
        return any(kw in normalized for kw in blocked_keywords)

    def register_model(self, model_name: str, provider: str = "local", policy: str = "default") -> bool:
        """
        Register or update a model.
        External cloud providers are rejected.
        """
        with self._lock:
            if self._is_blocked(model_name):
                emit_scar("model_registration_blocked", {
                    "model": model_name,
                    "reason": "External provider blocked by sovereign policy"
                })
                print(f"[BLOCKED] Model '{model_name}' rejected — external provider.")
                return False

            if model_name in self._models:
                print(f"Model '{model_name}' already exists. Updating policy.")
                existing = self._models[model_name]
                updated = ModelConfig(
                    name=model_name,
                    endpoint=existing.endpoint,
                    provider=existing.provider,
                    priority=existing.priority,
                    policy=policy
                )
                self._models[model_name] = updated
            else:
                # Default to local Grok endpoint for any new sovereign model
                self._models[model_name] = ModelConfig(
                    name=model_name,
                    endpoint="http://127.0.0.1:9899/api/generate",
                    provider=ModelProvider.LOCAL_GROK,
                    priority=50,
                    policy=policy
                )

            emit_scar("model_registered", {
                "model": model_name,
                "provider": provider,
                "policy": policy
            })
            print(f"Model '{model_name}' registered/updated successfully.")
            return True

    def get_model(self, model_name: str) -> Optional[ModelConfig]:
        """Retrieve model config. Blocked models return None."""
        with self._lock:
            if self._is_blocked(model_name):
                emit_scar("model_access_blocked", {"model": model_name})
                return None

            config = self._models.get(model_name)
            if config:
                emit_scar("model_retrieved", {"model": model_name})
            return config

    def get_active_model(self, request_context: str = "") -> str:
        """
        Returns the authoritative model for this request.
        Judge model decides for complex cases; otherwise Grok-4.5-build is default.
        """
        with self._lock:
            if "judge" in request_context.lower() or "complex" in request_context.lower():
                return "judge-grok-4.5"

            # Default sovereign model
            return "grok-4.5-build"

    def list_models(self) -> Dict[str, ModelConfig]:
        """Return copy of all allowed models."""
        with self._lock:
            allowed = {k: v for k, v in self._models.items() if not self._is_blocked(k)}
            emit_scar("model_list_accessed", {"count": len(allowed)})
            return allowed.copy()

    def delete_model(self, model_name: str) -> bool:
        """Delete a model (cannot delete the two core sovereign models)."""
        with self._lock:
            if model_name in ("grok-4.5-build", "judge-grok-4.5"):
                emit_scar("model_deletion_blocked", {
                    "model": model_name,
                    "reason": "Core sovereign model cannot be deleted"
                })
                print(f"[PROTECTED] Cannot delete core sovereign model: {model_name}")
                return False

            if model_name in self._models:
                del self._models[model_name]
                emit_scar("model_deleted", {"model": model_name})
                print(f"Model '{model_name}' deleted.")
                return True

            print(f"Model '{model_name}' not found.")
            return False


# --- Quick self-test (run directly) ---
if __name__ == "__main__":
    registry = ModelRegistry()

    print("\n=== Sovereign Model Registry Test ===")
    print("Active model (normal):", registry.get_active_model())
    print("Active model (judge context):", registry.get_active_model("complex reasoning task"))

    registry.register_model("my-custom-local-model", "local", "strict")
    registry.register_model("gemini-pro", "google", "default")  # should be blocked

    print("\nRegistered models:")
    for name, cfg in registry.list_models().items():
        print(f"  {name}: provider={cfg.provider.value}, policy={cfg.policy}")

    print("\nTrying to get blocked model:")
    print(registry.get_model("gemini-pro"))

    registry.delete_model("my-custom-local-model")
    registry.delete_model("grok-4.5-build")  # protected

    print("\nFinal registry state:")
    for name in registry.list_models():
        print(f"  - {name}")
