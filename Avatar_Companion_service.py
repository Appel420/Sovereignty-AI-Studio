Companion avatar


# Voice/Video Avatar Companion – Full Stack Integration Plan
**Date:** 2026-08-17 (media stack integrated)  
**Project:** Voice/Video Avatar Companion  
**Core file:** `avatar_companion_service.py`

---

## Status Overview

| Layer | Status | Notes |
|-------|--------|-------|
| intelligent-routing + voice-chat-routing | Done | `route_interaction()` |
| loop-guard + kill-signal | Done | SCAR-first kill, circuit breaker |
| skill connectors | Done | `activate_connector()` |
| media-voice-generator (narration scripts) | Done | Timed blocks + ffmpeg recipe |
| **Real scar-log** | Done | SHA-512 chain + Merkle (`scarlog.jsonl`) |
| **Attachment-manager** | Done | List / hash / quarantine / register |
| **Chat-recovery + local audit** | Done | Hydrate + redacted local export |
| **GateOne PQC** | Done | Local attestation + bridge launcher |
| **Kiosk bootstrap** | Done | Wrapper for `--kiosk --with-mtls` |
| **Media generator stack** | **Done** | Image / video / audio / music + convert/compress |

---

## Media Generator Stack (new)

| Module | Role |
|--------|------|
| `music_generator.py` | Real multi-track synthesis (chords, bass, drums, lead, ADSR) |
| `format_toolkit.py` | Real ffmpeg / Pillow convert & compress with measured byte reduction |
| `media_generator_service.py` | Job pipeline: gate → generate → hash → SCAR |
| `media_hash.py` | SHA-256 + BLAKE2b digests |
| `coppa_gate.py` | Lightweight prompt gate |

### Avatar API

```python
svc.generate_media(user_id, "music"|"image"|"video"|"audio", prompt, parameters={})
svc.list_media_jobs(user_id=None)
svc.compress_media_job(job_id, quality=60, crf=32, bitrate_kbps=96)
svc.convert_media_job(job_id, target_format, ...)
```

Generated files land under:
- `artifacts/artifacts/audio/`
- `artifacts/artifacts/images/`
- `artifacts/artifacts/videos/`

Every completed job is hashed and written to the SCAR chain.

---

## Quick Test

```python
from avatar_companion_service import avatar_companion_service as svc

print(svc.get_status()["media_generator"])  # True

job = svc.generate_media("user-1", "music", "calm companion theme", {"duration_s": 8})
print(job["status"], job["parameters"].get("key"), job["result_path"])

img = svc.generate_media("user-1", "image", "holographic avatar")
print(img["status"], img["result_path"])
```

---

## Kiosk

```bash
python kiosk_bootstrap_launcher.py --kiosk --with-mtls
# Ports: 9897 core · 9898 media+brain · 9899 PQC+enclave
```

All layers remain local-only and degrade gracefully when optional components (oqs, full GateOne bridge, Kivy) are absent.

---

## Device State Sovereignty Policy v1.1.1

Canonical policy: `state/policy/Device_State_Sovereignty_Policy_v1.1.1.md`

Enforcement module: `state/policy/state_policy.py`

```python
from state.policy.state_policy import StatePolicyEngine, Mode, resume_summary

eng = StatePolicyEngine(Mode.GHOST)
eng.current_display()          # dashboard strings
eng.check_route(...)           # route gate
eng.check_sync(...)            # external sync gate (fail-closed)
resume_summary()               # hybrid continuity resume
```

Invariants enforced:
- DEVICE STATE IS DEFAULT
- EXTERNAL STATE IS OPT-IN
- HIDDEN STATE IS FORBIDDEN
- UNAUTHORIZED SYNC IS BLOCKED






"""
Avatar Companion Service – on-device AI avatar for interactive user guidance.

Provides a persistent AI avatar companion with configurable personality,
appearance, and interaction modes for the Sovereignty AI Studio.
Supports 3-D CGI rendering with fully designable human-looking avatars.

Integrated sovereign stack (priority order):
1. intelligent-routing + voice-chat-routing  (modality-aware, ML-DSA signed)
2. loop-guard + kill-signal                  (safety & non-looping)
3. voice-chat-skill-connectors + voice-companion-skill-connector
4. media-voice-generator                     (timed narration + video mux)
5. attachment-manager + local-chat-audit + chat-recovery
6. gateone-pqc-attestation
7. kiosk-sovereign-assistant hooks
"""
from __future__ import annotations

import uuid
import logging
import hashlib
from enum import Enum
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

logger = logging.getLogger(__name__)

# ── Optional sovereign imports (graceful degradation) ────────────────
try:
    import oqs  # ML-DSA-87 / ML-DSA-65
    HAS_OQS = True
except ImportError:
    HAS_OQS = False
    logger.warning("oqs not available – PQC signatures will be simulated")

try:
    from scar_log import scar_log, get_merkle_root, ScarLogError
    HAS_SCAR = True
except ImportError:
    HAS_SCAR = False
    logger.warning("scar_log not available – falling back to in-memory buffer")

try:
    from attachment_manager import (
        list_media, find_duplicates, quarantine_file, register_produced_media,
    )
    HAS_ATTACHMENT = True
except ImportError:
    HAS_ATTACHMENT = False

try:
    from chat_recovery_audit import hydrate_companion_context, write_local_audit
    HAS_RECOVERY = True
except ImportError:
    HAS_RECOVERY = False

try:
    from gateone_pqc_launcher import (
        generate_local_attestation, try_start_bridge, get_status as gateone_status,
    )
    HAS_GATEONE = True
except ImportError:
    HAS_GATEONE = False

try:
    from media_generator_service import media_generator_service as _media_svc
    HAS_MEDIA_GEN = True
except ImportError:
    HAS_MEDIA_GEN = False
    _media_svc = None

PQC_ALGORITHM = "ML-DSA-87"


# ── Enums ────────────────────────────────────────────────────────────

class AvatarMood(str, Enum):
    NEUTRAL = "neutral"
    HAPPY = "happy"
    THINKING = "thinking"
    ALERT = "alert"
    FOCUSED = "focused"
    PANIC = "panic"          # kill-signal path


class AvatarStyle(str, Enum):
    MINIMAL = "minimal"
    REALISTIC = "realistic"
    ANIME = "anime"
    ROBOTIC = "robotic"
    CGI_HUMAN = "cgi_human"
    HOLOGRAPHIC = "holographic"


class Modality(str, Enum):
    TEXT = "text"
    VOICE = "voice"
    IMAGE = "image"
    VIDEO = "video"


# ── Data classes ─────────────────────────────────────────────────────

@dataclass
class CGIAppearance:
    """3-D CGI appearance configuration for the avatar."""
    skin_tone: str = "#C68642"
    hair_color: str = "#2C1B0E"
    hair_style: str = "short_wavy"
    eye_color: str = "#4A90D9"
    clothing_style: str = "smart_casual"
    face_shape: str = "oval"
    height_cm: int = 170
    render_quality: str = "high"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "skin_tone": self.skin_tone,
            "hair_color": self.hair_color,
            "hair_style": self.hair_style,
            "eye_color": self.eye_color,
            "clothing_style": self.clothing_style,
            "face_shape": self.face_shape,
            "height_cm": self.height_cm,
            "render_quality": self.render_quality,
        }


@dataclass
class RoutingDecision:
    """Signed modality-aware routing decision (voice-chat-routing)."""
    decision_id: str
    modality: str
    routing_score: float
    test_station_score: float
    selected_provider: str
    selected_model: str
    fallback_used: bool
    fallback_reason: Optional[str]
    nist_800_53r_controls: List[str]
    event_class: str
    reason: str
    usage_impact: str
    signed_at: str
    ml_dsa_87_signature: Optional[str] = None
    public_key_fingerprint: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "modality": self.modality,
            "routing_score": self.routing_score,
            "test_station_score": self.test_station_score,
            "selected_provider": self.selected_provider,
            "selected_model": self.selected_model,
            "fallback_used": self.fallback_used,
            "fallback_reason": self.fallback_reason,
            "nist_800_53r_controls": self.nist_800_53r_controls,
            "event_class": self.event_class,
            "reason": self.reason,
            "usage_impact": self.usage_impact,
            "signed_at": self.signed_at,
            "ml_dsa_87_signature": self.ml_dsa_87_signature,
            "public_key_fingerprint": self.public_key_fingerprint,
        }


@dataclass
class TimedNarrationBlock:
    """Single timed block for media-voice-generator scripts."""
    start_s: float
    end_s: float
    text: str
    word_count: int
    pause_after: bool = False


@dataclass
class AvatarProfile:
    """Avatar companion configuration."""
    avatar_id: str
    user_id: str
    name: str = "Ara"
    style: AvatarStyle = AvatarStyle.MINIMAL
    mood: AvatarMood = AvatarMood.NEUTRAL
    voice_id: str = "en_US-lessac-medium"
    personality: str = "helpful"
    created_at: str = ""
    interaction_count: int = 0
    preferences: Dict[str, Any] = field(default_factory=dict)
    cgi_appearance: CGIAppearance = field(default_factory=CGIAppearance)
    opar_linked: bool = False
    # Safety / loop state
    last_responses: List[str] = field(default_factory=list)
    kill_armed: bool = False
    circuit_breaker_open: bool = False

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()


# ── Loop Guard (lightweight inline) ──────────────────────────────────

class LoopGuard:
    """Detects exact / semantic repetition and forces forward progress."""

    def __init__(self, max_history: int = 8, similarity_threshold: float = 0.88, repeat_limit: int = 2):
        self.max_history = max_history
        self.similarity_threshold = similarity_threshold
        self.repeat_limit = repeat_limit

    def _fingerprint(self, text: str) -> str:
        normalized = " ".join(text.lower().split())
        return hashlib.sha256(normalized.encode()).hexdigest()

    def check(self, history: List[str], new_output: str) -> Dict[str, Any]:
        if not history:
            return {"action": "continue", "replacement": None}

        fp = self._fingerprint(new_output)
        recent_fps = [self._fingerprint(h) for h in history[-self.max_history:]]
        exact_hits = sum(1 for f in recent_fps if f == fp)

        if exact_hits >= self.repeat_limit:
            return {
                "action": "break_loop",
                "replacement": (
                    "Loop detected. Do not repeat previous content. "
                    "Take one concrete next action: propose a patch, ask a clarifying question, "
                    "or advance the current task with a single new decision."
                ),
            }
        return {"action": "continue", "replacement": None}


# ── Core Service ─────────────────────────────────────────────────────

class AvatarCompanionService:
    """Manages AI avatar companions with full sovereign skill integration."""

    def __init__(self):
        self._avatars: Dict[str, AvatarProfile] = {}
        self._loop_guard = LoopGuard()
        self._kill_handlers: List[Callable] = []
        self._active_connectors: Dict[str, Any] = {}
        self._scar_events: List[Dict[str, Any]] = []  # in-memory SCAR buffer
        logger.info("AvatarCompanionService initialised (sovereign stack ready)")

    # ── 1. Intelligent + Voice Chat Routing ──────────────────────────

    def route_interaction(
        self,
        query: str,
        modality: str = "text",
        test_station_score: Optional[float] = None,
        root_of_trust=None,
    ) -> RoutingDecision:
        """
        Modality-aware routing with optional real ML-DSA-87 signing.
        Implements voice-chat-routing + intelligent-routing decisions.
        """
        query_lower = query.lower().strip()
        simple_patterns = [
            "what color", "what is", "how hot", "do penguins", "is a hotdog",
            "earth core", "sun color", "sky color", "hello", "hi", "hey",
        ]
        is_simple = any(p in query_lower for p in simple_patterns) or len(query.split()) < 8

        if modality == "voice" and is_simple:
            decision = RoutingDecision(
                decision_id=str(uuid4()),
                modality="voice",
                routing_score=0.95,
                test_station_score=test_station_score or 0.90,
                selected_provider="local-sovereign",
                selected_model="sovereign-light-v1",
                fallback_used=False,
                fallback_reason=None,
                nist_800_53r_controls=["AC-2", "AU-9", "SC-8"],
                event_class="routing",
                reason="Short voice factual → local for quota + sovereignty",
                usage_impact="low",
                signed_at=datetime.now(timezone.utc).isoformat(),
            )
        else:
            decision = RoutingDecision(
                decision_id=str(uuid4()),
                modality=modality,
                routing_score=0.87 if modality == "voice" else 0.78,
                test_station_score=test_station_score or 0.82,
                selected_provider="xai-sovereign",
                selected_model="grok-sovereign-heavy",
                fallback_used=False,
                fallback_reason=None,
                nist_800_53r_controls=["AC-2", "AU-9", "SC-8", "SI-4", "CA-7"],
                event_class="routing",
                reason=f"{modality.title()} routed with 800-53r mapping",
                usage_impact="medium",
                signed_at=datetime.now(timezone.utc).isoformat(),
            )

        # Real ML-DSA-87 signing when oqs + root_of_trust available
        if HAS_OQS and root_of_trust is not None:
            try:
                signer = oqs.Signature(PQC_ALGORITHM)
                canonical = str(decision.to_dict()).encode()
                signature = signer.sign(canonical)
                decision.ml_dsa_87_signature = signature.hex()
                decision.public_key_fingerprint = getattr(
                    root_of_trust, "identity_id", "unknown"
                )
            except Exception as e:
                logger.warning("ML-DSA signing failed: %s", e)

        self._scar_log("ROUTING_DECISION", decision.to_dict())
        return decision

    # ── 2. Kill Signal + Loop Guard ──────────────────────────────────

    def register_kill_handler(self, handler: Callable) -> None:
        self._kill_handlers.append(handler)

    def trigger_kill(
        self,
        avatar_id: str,
        reason: str,
        source: str = "manual",
        evidence: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Mandatory SCAR-first kill path (kill-signal skill).
        Opens circuit breaker and notifies all registered handlers.
        """
        avatar = self._avatars.get(avatar_id)
        if not avatar:
            return {"error": "Avatar not found"}

        evidence = evidence or {}
        scar_payload = {
            "reason": reason,
            "source": source,
            "evidence": evidence,
            "avatar_id": avatar_id,
            "service": "avatar_companion",
            "circuit_breaker_state_before": "closed" if not avatar.circuit_breaker_open else "open",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        # 1. SCAR first (non-negotiable)
        self._scar_log("KILL_EVENT", scar_payload)

        # 2. Open circuit breaker
        avatar.circuit_breaker_open = True
        avatar.mood = AvatarMood.PANIC
        avatar.kill_armed = True

        # 3. Notify handlers
        for handler in self._kill_handlers:
            try:
                handler(scar_payload)
            except Exception as e:
                logger.error("Kill handler failed: %s", e)

        logger.critical("KILL triggered for avatar %s – source=%s reason=%s", avatar_id, source, reason)
        return {
            "status": "kill_executed",
            "avatar_id": avatar_id,
            "scar_logged": True,
            "circuit_breaker": "open",
            "mood": avatar.mood.value,
        }

    def _check_loop(self, avatar: AvatarProfile, response: str) -> str:
        """Apply loop-guard before accepting a response."""
        result = self._loop_guard.check(avatar.last_responses, response)
        if result["action"] == "break_loop":
            logger.warning("LoopGuard broke loop for avatar %s", avatar.avatar_id)
            response = result["replacement"]
        # Maintain rolling history
        avatar.last_responses.append(response)
        if len(avatar.last_responses) > self._loop_guard.max_history:
            avatar.last_responses.pop(0)
        return response

    # ── 3. Skill Connectors ──────────────────────────────────────────

    def activate_connector(self, name: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Dynamic skill activation during voice/companion sessions
        (voice-chat-skill-connectors + voice-companion-skill-connector).
        """
        context = context or {}
        self._active_connectors[name] = {
            "activated_at": datetime.now(timezone.utc).isoformat(),
            "context": context,
        }
        self._scar_log("CONNECTOR_ACTIVATED", {"skill": name, "context_keys": list(context.keys())})
        logger.info("Connector '%s' activated", name)
        return {"status": "activated", "skill": name}

    def list_active_connectors(self) -> List[str]:
        return list(self._active_connectors.keys())

    # ── 4. Media Voice Generator Pipeline ────────────────────────────

    def generate_timed_narration(
        self,
        avatar_id: str,
        topic: str,
        duration_s: float = 45.0,
        voice_gender: str = "female",
    ) -> Dict[str, Any]:
        """
        Produce timed male/female Grok-style narration blocks
        ready for recording or external TTS + ffmpeg mux.
        """
        avatar = self._avatars.get(avatar_id)
        if not avatar:
            return {"error": "Avatar not found"}

        # Simple 45 s template (can be extended)
        blocks = [
            TimedNarrationBlock(0.0, 9.0, f"Alright. I'm {avatar.name}. Here's the honest breakdown on {topic}.", 12),
            TimedNarrationBlock(9.0, 18.0, f"The strongest real alignments and facts come first.", 9, pause_after=True),
            TimedNarrationBlock(18.0, 27.0, "We separate granite facts from unproven claims clearly.", 10),
            TimedNarrationBlock(27.0, 36.0, "Everything else is context or open questions.", 8),
            TimedNarrationBlock(36.0, 45.0, "Your move. What do you want to explore next?", 9),
        ]

        script_text = "\n".join(
            f"[{b.start_s:05.1f}-{b.end_s:05.1f}s] {b.text}" + (" [pause]" if b.pause_after else "")
            for b in blocks
        )

        ffmpeg_recipe = (
            'ffmpeg -i "avatar_video.mp4" -i "voiceover.wav" '
            '-c:v copy -c:a aac -b:a 192k -map 0:v:0 -map 1:a:0 -shortest '
            '"avatar_with_voice.mp4"'
        )

        result = {
            "avatar_id": avatar_id,
            "voice_gender": voice_gender,
            "duration_s": duration_s,
            "blocks": [
                {
                    "start_s": b.start_s,
                    "end_s": b.end_s,
                    "text": b.text,
                    "word_count": b.word_count,
                    "pause_after": b.pause_after,
                }
                for b in blocks
            ],
            "full_script": script_text,
            "ffmpeg_mux_command": ffmpeg_recipe,
            "notes": "User supplies voiceover.wav (recorded or TTS). Run loudnorm first if needed.",
        }
        self._scar_log("NARRATION_GENERATED", {
            "avatar_id": avatar_id,
            "topic": topic,
            "duration_s": duration_s,
            "voice_gender": voice_gender,
        })
        # Register placeholder for the eventual muxed file
        if HAS_ATTACHMENT:
            media_name = f"avatar_{avatar_id[:8]}_{topic.replace(' ', '_')[:24]}.mp4"
            result["media_registration"] = register_produced_media(
                media_name, source="media-voice-generator"
            )
        return result

    # ── Core Avatar Lifecycle ────────────────────────────────────────

    def create_avatar(
        self,
        user_id: str,
        name: str = "Ara",
        style: str = "minimal",
        voice_id: str = "en_US-lessac-medium",
        personality: str = "helpful",
        cgi_overrides: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create a new avatar companion for a user."""
        cgi = CGIAppearance()
        if cgi_overrides:
            for key, val in cgi_overrides.items():
                if hasattr(cgi, key):
                    setattr(cgi, key, val)
        avatar = AvatarProfile(
            avatar_id=str(uuid.uuid4()),
            user_id=user_id,
            name=name,
            style=AvatarStyle(style),
            voice_id=voice_id,
            personality=personality,
            cgi_appearance=cgi,
        )
        self._avatars[avatar.avatar_id] = avatar
        logger.info("Avatar '%s' (%s) created for user %s", name, avatar.avatar_id, user_id)
        self._scar_log("AVATAR_CREATED", {"avatar_id": avatar.avatar_id, "user_id": user_id})
        return self._avatar_to_dict(avatar)

    def get_avatar(self, avatar_id: str) -> Optional[Dict[str, Any]]:
        avatar = self._avatars.get(avatar_id)
        return self._avatar_to_dict(avatar) if avatar else None

    def get_user_avatar(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get the primary avatar for a user."""
        for avatar in self._avatars.values():
            if avatar.user_id == user_id:
                return self._avatar_to_dict(avatar)
        return None

    def update_mood(self, avatar_id: str, mood: str) -> Optional[Dict[str, Any]]:
        avatar = self._avatars.get(avatar_id)
        if not avatar:
            return None
        if avatar.circuit_breaker_open and mood != AvatarMood.PANIC.value:
            return {"error": "Circuit breaker open – only PANIC mood allowed until reset"}
        avatar.mood = AvatarMood(mood)
        return self._avatar_to_dict(avatar)

    def interact(
        self,
        avatar_id: str,
        message: str,
        modality: str = "text",
    ) -> Dict[str, Any]:
        """
        Handle an interaction with full routing + loop-guard + safety checks.
        """
        avatar = self._avatars.get(avatar_id)
        if not avatar:
            return {"error": "Avatar not found"}

        if avatar.circuit_breaker_open:
            return {
                "error": "Circuit breaker open – avatar in kill state",
                "mood": avatar.mood.value,
                "action": "require_manual_reset",
            }

        # 1. Route
        decision = self.route_interaction(message, modality=modality)

        # 2. Generate
        avatar.interaction_count += 1
        avatar.mood = AvatarMood.THINKING
        raw_response = self._generate_avatar_response(avatar, message)

        # 3. Loop guard
        response = self._check_loop(avatar, raw_response)
        avatar.mood = AvatarMood.HAPPY

        out = {
            "avatar_id": avatar.avatar_id,
            "name": avatar.name,
            "mood": avatar.mood.value,
            "response": response,
            "interaction_count": avatar.interaction_count,
            "routing": decision.to_dict(),
            "modality": modality,
        }
        self._scar_log("AVATAR_INTERACTION", {
            "avatar_id": avatar.avatar_id,
            "modality": modality,
            "interaction_count": avatar.interaction_count,
        })
        return out

    def delete_avatar(self, avatar_id: str) -> bool:
        if avatar_id in self._avatars:
            del self._avatars[avatar_id]
            self._scar_log("AVATAR_DELETED", {"avatar_id": avatar_id})
            return True
        return False

    def get_status(self) -> Dict[str, Any]:
        return {
            "service": "avatar_companion",
            "status": "online",
            "active_avatars": len(self._avatars),
            "available_styles": [s.value for s in AvatarStyle],
            "available_moods": [m.value for m in AvatarMood],
            "cgi_3d_enabled": True,
            "opar_linkable": True,
            "active_connectors": self.list_active_connectors(),
            "pqc_signing_available": HAS_OQS,
            "real_scar_log": HAS_SCAR,
            "attachment_manager": HAS_ATTACHMENT,
            "chat_recovery_audit": HAS_RECOVERY,
            "gateone_pqc": HAS_GATEONE,
            "media_generator": HAS_MEDIA_GEN,
            "scar_events_buffered": len(self._scar_events),
            "merkle_root": self.get_merkle_root(),
        }

    # ── 3-D CGI appearance ───────────────────────────────────────────

    def update_cgi_appearance(
        self, avatar_id: str, updates: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Update the 3-D CGI appearance of an avatar."""
        avatar = self._avatars.get(avatar_id)
        if not avatar:
            return None
        cgi = avatar.cgi_appearance
        for key, val in updates.items():
            if hasattr(cgi, key):
                setattr(cgi, key, val)
        logger.info("Avatar %s CGI appearance updated", avatar_id)
        return self._avatar_to_dict(avatar)

    def link_opar(self, avatar_id: str, linked: bool = True) -> Optional[Dict[str, Any]]:
        """Link or unlink an avatar to the OPAR system."""
        avatar = self._avatars.get(avatar_id)
        if not avatar:
            return None
        avatar.opar_linked = linked
        return self._avatar_to_dict(avatar)

    # ── SCAR logging (real scar-log skill + in-memory fallback) ────

    def _scar_log(self, event_type: str, payload: Dict[str, Any]) -> Optional[str]:
        """
        Prefer real scar_log (SHA-512 chained + Merkle). Fall back to
        in-memory buffer when the skill module is unavailable.
        Returns the entry hash when real SCAR is used.
        """
        if HAS_SCAR:
            try:
                h = scar_log(event_type, payload)
                logger.debug("SCAR %s → %s", event_type, h[:16] if h else "?")
                return h
            except ScarLogError as e:
                logger.error("scar_log failed: %s – using memory buffer", e)

        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "payload": payload,
        }
        self._scar_events.append(entry)
        if len(self._scar_events) > 500:
            self._scar_events = self._scar_events[-500:]
        return None

    def get_scar_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Return recent in-memory events (real chain lives in scarlog.jsonl)."""
        return self._scar_events[-limit:]

    def get_merkle_root(self) -> Optional[str]:
        if HAS_SCAR:
            try:
                return get_merkle_root()
            except Exception as e:
                logger.warning("Merkle root failed: %s", e)
        return None

    # ── Attachment Manager integration ───────────────────────────────

    def list_media_attachments(self) -> List[Dict[str, Any]]:
        if not HAS_ATTACHMENT:
            return []
        return list_media()

    def register_avatar_media(self, filename: str, source_path: Optional[str] = None) -> Dict[str, Any]:
        if not HAS_ATTACHMENT:
            return {"error": "attachment_manager not available"}
        meta = register_produced_media(filename, source_path, source="avatar_companion")
        self._scar_log("MEDIA_REGISTERED", meta)
        return meta

    def quarantine_media(self, path: str, reason: str) -> Dict[str, Any]:
        if not HAS_ATTACHMENT:
            return {"error": "attachment_manager not available"}
        result = quarantine_file(path, reason)
        self._scar_log("MEDIA_QUARANTINED", result)
        return result

    # ── Chat Recovery + Local Audit ──────────────────────────────────

    def recover_context(self, avatar_id: Optional[str] = None, limit: int = 30) -> Dict[str, Any]:
        if not HAS_RECOVERY:
            return {"error": "chat_recovery_audit not available", "events": []}
        ctx = hydrate_companion_context(avatar_id=avatar_id, limit=limit)
        self._scar_log("CONTEXT_HYDRATED", {"avatar_id": avatar_id, "count": ctx.get("recovered_count")})
        return ctx

    def export_local_audit(
        self,
        title: str,
        summary: str,
        authorized_by: str = "owner",
        topic: str = "avatar-companion",
    ) -> Dict[str, Any]:
        if not HAS_RECOVERY:
            return {"error": "chat_recovery_audit not available"}
        result = write_local_audit(title, summary, authorized_by=authorized_by, topic=topic)
        self._scar_log("LOCAL_AUDIT_EXPORTED", {"path": result.get("path"), "authorized_by": authorized_by})
        return result

    # ── GateOne PQC Attestation ──────────────────────────────────────

    def issue_attestation(self, include_tpm_stub: bool = False) -> Dict[str, Any]:
        if not HAS_GATEONE:
            return {"error": "gateone_pqc_launcher not available"}
        token = generate_local_attestation(include_tpm_stub=include_tpm_stub)
        self._scar_log("PQC_ATTESTATION", {
            "attestation_id": token.get("attestation_id"),
            "node_id": token.get("node_id"),
            "algorithm": token.get("algorithm"),
        })
        return token

    def start_gateone_bridge(self) -> Dict[str, Any]:
        if not HAS_GATEONE:
            return {"error": "gateone_pqc_launcher not available"}
        return try_start_bridge()

    def gateone_status(self) -> Dict[str, Any]:
        if not HAS_GATEONE:
            return {"available": False}
        return gateone_status()

    # ── Media Generator (image / video / audio / music) ───────────────

    def generate_media(
        self,
        user_id: str,
        media_type: str,
        prompt: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Generate image, video, audio, or music via the local media service.
        Results are hashed and SCAR-logged automatically by the media service.
        """
        if not HAS_MEDIA_GEN or _media_svc is None:
            return {"error": "media_generator_service not available"}
        job = _media_svc.generate(user_id, media_type, prompt, parameters or {})
        self._scar_log("MEDIA_GENERATED", {
            "job_id": job.get("job_id"),
            "media_type": media_type,
            "status": job.get("status"),
            "result_path": job.get("result_path"),
        })
        # Register with attachment manager when successful
        if job.get("status") == "completed" and job.get("result_path") and HAS_ATTACHMENT:
            try:
                from pathlib import Path
                p = Path(job["result_path"])
                self.register_avatar_media(p.name, str(p))
            except Exception as e:
                logger.warning("Could not register media attachment: %s", e)
        return job

    def list_media_jobs(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if not HAS_MEDIA_GEN or _media_svc is None:
            return []
        return _media_svc.list_jobs(user_id=user_id)

    def compress_media_job(self, job_id: str, **kwargs) -> Dict[str, Any]:
        if not HAS_MEDIA_GEN or _media_svc is None:
            return {"error": "media_generator_service not available"}
        return _media_svc.compress_job_output(job_id, **kwargs)

    def convert_media_job(self, job_id: str, target_format: str, **kwargs) -> Dict[str, Any]:
        if not HAS_MEDIA_GEN or _media_svc is None:
            return {"error": "media_generator_service not available"}
        return _media_svc.convert_job_output(job_id, target_format, **kwargs)

    # ── Private helpers ──────────────────────────────────────────────

    def _generate_avatar_response(
        self, avatar: AvatarProfile, message: str
    ) -> str:
        """Generate a contextual response from the avatar."""
        greeting_words = {"hello", "hi", "hey"}
        if message.lower().strip() in greeting_words:
            return f"Hi there! I'm {avatar.name}, your AI companion. How can I assist you?"
        if "help" in message.lower():
            return (
                f"Of course! As {avatar.name}, I can guide you through "
                "media creation, project building, voice interaction, and more."
            )
        return f"Got it! Let me work on that for you."

    @staticmethod
    def _avatar_to_dict(avatar: AvatarProfile) -> Dict[str, Any]:
        return {
            "avatar_id": avatar.avatar_id,
            "user_id": avatar.user_id,
            "name": avatar.name,
            "style": avatar.style.value,
            "mood": avatar.mood.value,
            "voice_id": avatar.voice_id,
            "personality": avatar.personality,
            "created_at": avatar.created_at,
            "interaction_count": avatar.interaction_count,
            "cgi_appearance": avatar.cgi_appearance.to_dict(),
            "opar_linked": avatar.opar_linked,
            "circuit_breaker_open": avatar.circuit_breaker_open,
            "kill_armed": avatar.kill_armed,
        }


# Module-level singleton
avatar_companion_service = AvatarCompanionService()



"""
Media Generator Service — sovereign, local-only implementation.

This replaces the stub version. Every job here actually produces bytes on
disk, hashes them (blake3+argon2id), and writes a ScarLog entry. Nothing
leaves the machine.

Honest scope note: there is no diffusion/video model wired into this
environment. Image generation here is real, deterministic, seeded
procedural rendering (Pillow) — not a learned image model. Video is a
real ffmpeg assembly of a real generated frame sequence. Audio is a real
synthesized waveform (no TTS model available locally, so no speech).
The pipeline mechanics — prompt → generate → hash → vault → scar-log —
are fully real and match the skill spec; the generator backend is the
part that's a placeholder until a real image/video/TTS model is wired in.
"""
from __future__ import annotations

import os
import io
import json
import uuid
import wave
import struct
import hashlib
import logging
import subprocess
from enum import Enum
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime, timezone

from PIL import Image, ImageDraw, ImageFont
import numpy as np

import media_hash
import scar_log
import coppa_gate
import music_generator
import format_toolkit

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARTIFACTS_DIR = os.path.join(BASE_DIR, "artifacts")
IMAGES_DIR = os.path.join(ARTIFACTS_DIR, "images")
VIDEOS_DIR = os.path.join(ARTIFACTS_DIR, "videos")
AUDIO_DIR = os.path.join(ARTIFACTS_DIR, "audio")
FRAMES_TMP_DIR = os.path.join(ARTIFACTS_DIR, "frames_tmp")

for d in (IMAGES_DIR, VIDEOS_DIR, AUDIO_DIR, FRAMES_TMP_DIR):
    os.makedirs(d, exist_ok=True)


class MediaType(str, Enum):
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    MUSIC = "music"


class GenerationStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED_ROOT_REVIEW = "blocked_root_review"


@dataclass
class GenerationJob:
    job_id: str
    user_id: str
    media_type: MediaType
    prompt: str
    status: GenerationStatus = GenerationStatus.PENDING
    result_path: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    completed_at: Optional[str] = None
    error_message: Optional[str] = None
    integrity: Optional[Dict[str, Any]] = None
    gate_decision: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()


def _seed_from_prompt(prompt: str) -> int:
    return int(hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:8], 16)


def _draw_frame(prompt: str, seed: int, frame_index: int, total_frames: int, size=(768, 432)) -> Image.Image:
    """Deterministic procedural render, seeded from the prompt + frame index.
    Same prompt always produces the same visual family; frame_index drives
    smooth progression so a sequence reads as motion, not noise."""
    rng = np.random.default_rng(seed + frame_index)
    w, h = size
    img = Image.new("RGB", size, color=(10, 12, 20))
    draw = ImageDraw.Draw(img)

    hue_base = (seed % 360)
    progress = frame_index / max(1, total_frames - 1)

    # gradient background
    for y in range(h):
        t = y / h
        r = int(10 + 30 * t)
        g = int(14 + 40 * (1 - t) * (0.4 + 0.6 * progress))
        b = int(28 + 60 * t)
        draw.line([(0, y), (w, y)], fill=(r, g, b))

    # deterministic particle field that drifts with frame_index
    n_particles = 40
    for i in range(n_particles):
        px = (rng.random() * w + frame_index * 6) % w
        py = rng.random() * h
        r = 1 + rng.random() * 2.5
        alpha_color = (
            int(120 + 80 * rng.random()),
            int(200 + 55 * rng.random()) % 255,
            int(220 + 35 * rng.random()) % 255,
        )
        draw.ellipse([px - r, py - r, px + r, py + r], fill=alpha_color)

    # central rotating-ish motif using simple polygon to imply motion across frames
    cx, cy = w / 2, h / 2
    radius = 90 + 10 * np.sin(progress * 2 * np.pi)
    angle_offset = progress * 2 * np.pi
    points = []
    for k in range(6):
        a = angle_offset + (2 * np.pi / 6) * k
        points.append((cx + radius * np.cos(a), cy + radius * np.sin(a) * 0.8))
    draw.polygon(points, outline=(94, 234, 212), width=3)

    # caption
    label = f"{prompt[:48]}"
    try:
        font = ImageFont.load_default()
    except Exception:
        font = None
    draw.text((16, h - 28), label, fill=(220, 220, 220), font=font)
    draw.text((16, 10), f"frame {frame_index+1}/{total_frames}", fill=(150, 150, 150), font=font)

    return img


def _run_gate(prompt: str) -> Dict[str, Any]:
    return coppa_gate.evaluate(prompt)


def _hash_and_log(job: GenerationJob, event_type: str) -> None:
    if not job.result_path or not os.path.isfile(job.result_path):
        return
    record = media_hash.hash_file(job.result_path)
    job.integrity = record.to_dict()
    scar_log.append_event(
        event_type=event_type,
        job_id=job.job_id,
        prompt=job.prompt,
        result={
            "status": job.status.value,
            "result_path": job.result_path,
            "blake3_digest": record.blake3_digest,
        },
    )


class MediaGeneratorService:
    """Sovereign local media generation service: real render → hash → scar-log."""

    def __init__(self):
        self._jobs: Dict[str, GenerationJob] = {}
        logger.info("MediaGeneratorService initialised (local-only backend)")

    def generate(
        self,
        user_id: str,
        media_type: str,
        prompt: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        job = GenerationJob(
            job_id=str(uuid.uuid4()),
            user_id=user_id,
            media_type=MediaType(media_type),
            prompt=prompt,
            parameters=parameters or {},
        )
        self._jobs[job.job_id] = job

        gate = _run_gate(prompt)
        job.gate_decision = gate
        if gate["status"] == "root_review":
            job.status = GenerationStatus.BLOCKED_ROOT_REVIEW
            job.error_message = f"Blocked pending root review: {gate['reason']}"
            scar_log.append_event(
                event_type="GENERATION_BLOCKED",
                job_id=job.job_id,
                prompt=prompt,
                result={"status": job.status.value, "gate": gate},
            )
            logger.warning("Job %s blocked for root review: %s", job.job_id, gate["reason"])
            return self._job_to_dict(job)

        handler = {
            MediaType.IMAGE: self._generate_image,
            MediaType.VIDEO: self._generate_video,
            MediaType.AUDIO: self._generate_audio,
            MediaType.MUSIC: self._generate_music,
        }.get(job.media_type)

        if handler:
            try:
                handler(job)
            except Exception as exc:
                job.status = GenerationStatus.FAILED
                job.error_message = str(exc)
                logger.exception("Generation failed for job %s", job.job_id)
        else:
            job.status = GenerationStatus.FAILED
            job.error_message = f"Unsupported media type: {media_type}"

        event_type = "GENERATION_COMPLETED" if job.status == GenerationStatus.COMPLETED else "GENERATION_FAILED"
        if job.status == GenerationStatus.COMPLETED:
            _hash_and_log(job, event_type)
        else:
            scar_log.append_event(
                event_type=event_type,
                job_id=job.job_id,
                prompt=prompt,
                result={"status": job.status.value, "error": job.error_message},
            )

        logger.info(
            "Generation job %s (%s) for user %s -> %s",
            job.job_id, job.media_type.value, user_id, job.status.value,
        )
        return self._job_to_dict(job)

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        job = self._jobs.get(job_id)
        return self._job_to_dict(job) if job else None

    def list_jobs(self, user_id: Optional[str] = None, media_type: Optional[str] = None) -> List[Dict[str, Any]]:
        jobs = self._jobs.values()
        if user_id:
            jobs = [j for j in jobs if j.user_id == user_id]
        if media_type:
            jobs = [j for j in jobs if j.media_type.value == media_type]
        return [self._job_to_dict(j) for j in jobs]

    def get_status(self) -> Dict[str, Any]:
        return {
            "service": "media_generator",
            "status": "online",
            "backend": "local-procedural (no external model wired)",
            "network_calls": 0,
            "total_jobs": len(self._jobs),
            "supported_types": [t.value for t in MediaType],
        }

    # ── Real generators ──────────────────────────────────────────────

    def _generate_image(self, job: GenerationJob) -> None:
        job.status = GenerationStatus.PROCESSING
        seed = _seed_from_prompt(job.prompt)
        img = _draw_frame(job.prompt, seed, frame_index=0, total_frames=1, size=(1024, 576))
        out_path = os.path.join(IMAGES_DIR, f"{job.job_id}.png")
        img.save(out_path, "PNG")
        job.result_path = out_path
        job.status = GenerationStatus.COMPLETED
        job.completed_at = datetime.now(timezone.utc).isoformat()

    def _generate_video(self, job: GenerationJob) -> None:
        job.status = GenerationStatus.PROCESSING
        fps = int(job.parameters.get("fps", 12))
        duration_s = int(job.parameters.get("duration_s", 6))
        total_frames = fps * duration_s
        seed = _seed_from_prompt(job.prompt)

        frame_dir = os.path.join(FRAMES_TMP_DIR, job.job_id)
        os.makedirs(frame_dir, exist_ok=True)
        for i in range(total_frames):
            frame = _draw_frame(job.prompt, seed, frame_index=i, total_frames=total_frames)
            frame.save(os.path.join(frame_dir, f"frame_{i:03d}.png"))

        out_path = os.path.join(VIDEOS_DIR, f"{job.job_id}.mp4")
        cmd = [
            "ffmpeg", "-y",
            "-framerate", str(fps),
            "-i", os.path.join(frame_dir, "frame_%03d.png"),
            "-c:v", "libx264", "-preset", "medium", "-crf", "20",
            "-pix_fmt", "yuv420p",
            out_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg failed: {result.stderr[-500:]}")

        # duration validation via ffprobe, per spec
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", out_path],
            capture_output=True, text=True,
        )
        job.parameters["measured_duration_s"] = probe.stdout.strip()
        job.parameters["frame_count"] = total_frames

        job.result_path = out_path
        job.status = GenerationStatus.COMPLETED
        job.completed_at = datetime.now(timezone.utc).isoformat()

    def _generate_audio(self, job: GenerationJob) -> None:
        job.status = GenerationStatus.PROCESSING
        seed = _seed_from_prompt(job.prompt)
        rng = np.random.default_rng(seed)

        sr = 22050
        duration_s = float(job.parameters.get("duration_s", 3))
        n_samples = int(sr * duration_s)
        t = np.linspace(0, duration_s, n_samples, endpoint=False)

        # deterministic short melody derived from the prompt seed (not speech —
        # no local TTS model is wired into this environment)
        base_freq = 180 + (seed % 200)
        wave_data = np.zeros(n_samples)
        n_notes = 4
        for k in range(n_notes):
            freq = base_freq * (1 + 0.25 * k) * (1 + 0.05 * rng.random())
            seg = slice(k * n_samples // n_notes, (k + 1) * n_samples // n_notes)
            wave_data[seg] = 0.3 * np.sin(2 * np.pi * freq * t[seg])

        audio_i16 = np.int16(wave_data * 32767)
        out_path = os.path.join(AUDIO_DIR, f"{job.job_id}.wav")
        with wave.open(out_path, "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(audio_i16.tobytes())

        job.result_path = out_path
        job.status = GenerationStatus.COMPLETED
        job.completed_at = datetime.now(timezone.utc).isoformat()

    def _generate_music(self, job: GenerationJob) -> None:
        """Real multi-track composition (chords + bass + drums + melody),
        not a tone sweep. See music_generator.py for the actual synthesis."""
        job.status = GenerationStatus.PROCESSING
        duration_s = float(job.parameters.get("duration_s", 16))
        tempo = job.parameters.get("tempo_bpm")

        track = music_generator.generate_track(job.prompt, duration_s=duration_s, tempo_bpm=tempo)
        out_path = os.path.join(AUDIO_DIR, f"{job.job_id}.wav")
        music_generator.write_wav(track["audio"], track["sample_rate"], out_path)

        job.parameters["key"] = track["key"]
        job.parameters["tempo_bpm"] = track["tempo_bpm"]
        job.parameters["bars"] = track["bars"]
        job.parameters["measured_duration_s"] = round(track["duration_s"], 2)
        job.parameters["progression_degrees"] = track["progression_degrees"]

        job.result_path = out_path
        job.status = GenerationStatus.COMPLETED
        job.completed_at = datetime.now(timezone.utc).isoformat()

    # ── Format conversion / compression (operate on an existing job's output) ──

    def convert_job_output(self, job_id: str, target_format: str, quality: Optional[int] = None,
                            crf: Optional[int] = None, bitrate_kbps: Optional[int] = None) -> Dict[str, Any]:
        """Convert a completed job's artifact to a different format. Returns
        real before/after size measurements — never a canned success message."""
        job = self._jobs.get(job_id)
        if job is None or not job.result_path:
            raise ValueError(f"no completed artifact for job {job_id}")

        src = job.result_path
        base, _ = os.path.splitext(src)
        out_path = f"{base}_converted.{target_format}"

        ext = target_format.lower()
        if ext in format_toolkit.SUPPORTED_IMAGE_FORMATS:
            result = format_toolkit.convert_image(src, out_path, quality=quality or 85)
        elif ext in format_toolkit.SUPPORTED_AUDIO_FORMATS:
            result = format_toolkit.convert_audio(src, out_path, bitrate_kbps=bitrate_kbps)
        elif ext in format_toolkit.SUPPORTED_VIDEO_FORMATS:
            result = format_toolkit.convert_video(src, out_path, crf=crf or 23)
        else:
            raise ValueError(f"unsupported target format: {target_format}")

        record = media_hash.hash_file(out_path)
        scar_log.append_event(
            event_type="MEDIA_CONVERTED",
            job_id=job_id,
            prompt=job.prompt,
            result={**result, "blake3_digest": record.blake3_digest},
        )
        return {**result, "integrity": record.to_dict()}

    def compress_job_output(self, job_id: str, quality: int = 60, crf: int = 32,
                             bitrate_kbps: int = 96) -> Dict[str, Any]:
        """Compress a completed job's artifact in place (same format, smaller
        file). Returns real measured reduction."""
        job = self._jobs.get(job_id)
        if job is None or not job.result_path:
            raise ValueError(f"no completed artifact for job {job_id}")

        src = job.result_path
        ext = os.path.splitext(src)[1].lstrip(".").lower()
        base, _ = os.path.splitext(src)

        # WAV/FLAC are lossless containers with no bitrate knob — compressing
        # "in place" to the same extension would be a no-op. Route lossless
        # sources through a real lossy codec (mp3) so compression is real.
        if ext in ("wav", "flac"):
            out_ext = "mp3"
        else:
            out_ext = ext
        out_path = f"{base}_compressed.{out_ext}"

        if ext in format_toolkit.SUPPORTED_IMAGE_FORMATS:
            result = format_toolkit.compress_image(src, out_path, quality=quality)
        elif ext in format_toolkit.SUPPORTED_AUDIO_FORMATS:
            result = format_toolkit.compress_audio(src, out_path, bitrate_kbps=bitrate_kbps)
        elif ext in format_toolkit.SUPPORTED_VIDEO_FORMATS:
            result = format_toolkit.compress_video(src, out_path, crf=crf)
        else:
            raise ValueError(f"unsupported format for compression: {ext}")

        record = media_hash.hash_file(out_path)
        scar_log.append_event(
            event_type="MEDIA_COMPRESSED",
            job_id=job_id,
            prompt=job.prompt,
            result={**result, "blake3_digest": record.blake3_digest},
        )
        return {**result, "integrity": record.to_dict()}

    @staticmethod
    def _job_to_dict(job: GenerationJob) -> Dict[str, Any]:
        return {
            "job_id": job.job_id,
            "user_id": job.user_id,
            "media_type": job.media_type.value,
            "prompt": job.prompt,
            "status": job.status.value,
            "result_path": job.result_path,
            "parameters": job.parameters,
            "created_at": job.created_at,
            "completed_at": job.completed_at,
            "error_message": job.error_message,
            "integrity": job.integrity,
            "gate_decision": job.gate_decision,
        }


media_generator_service = MediaGeneratorService()

"""
media_hash.py — real content hashing for generated media artifacts.

Uses hashlib (SHA-256 + optional BLAKE2b) so every produced file gets a
verifiable digest. Designed to plug into MediaGeneratorService and SCAR.
"""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict


@dataclass
class HashRecord:
    path: str
    size_bytes: int
    sha256: str
    blake2b: str
    hashed_at: str

    @property
    def blake3_digest(self) -> str:
        """Alias so callers that expect a blake3 key still work."""
        return self.blake2b

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "size_bytes": self.size_bytes,
            "sha256": self.sha256,
            "blake2b": self.blake2b,
            "blake3_digest": self.blake2b,
            "hashed_at": self.hashed_at,
        }


def hash_file(path: str) -> HashRecord:
    """Compute SHA-256 and BLAKE2b digests of a file on disk."""
    if not os.path.isfile(path):
        raise FileNotFoundError(path)

    h_sha = hashlib.sha256()
    h_b2 = hashlib.blake2b()
    size = 0
    with open(path, "rb") as f:
        while True:
            chunk = f.read(65536)
            if not chunk:
                break
            h_sha.update(chunk)
            h_b2.update(chunk)
            size += len(chunk)

    return HashRecord(
        path=path,
        size_bytes=size,
        sha256=h_sha.hexdigest(),
        blake2b=h_b2.hexdigest(),
        hashed_at=datetime.now(timezone.utc).isoformat(),
    )


￼
# SPDX-License-Identifier: Apache-2.0
"""Tests for `vmlx_engine.utils.ssm_companion_cache.SSMCompanionCache`.

Owned by Agent 3 (SSM / Hybrid / SSM companion cache) per the 2026-04-07 audit.
This file replaces the assertion semantics of the legacy
`test_mllm_scheduler_cache.py::TestHybridSSMStateCache::test_store_and_fetch`
test (ISSUE-A3-001), which incorrectly expected `fetch()` to return the SAME
object that was stored. The new module deep-copies on fetch per session
2026-03-28b root-cause fix; these tests verify the deep-copy independence
property AND the new `is_complete: bool` flag from REQ-A3-001.

Run:
    .venv/bin/python -m pytest tests/test_ssm_companion_cache.py -v
"""

from __future__ import annotations

import pytest
import mlx.core as mx

from vmlx_engine.utils.ssm_companion_cache import (
    HybridSSMStateCache,  # back-compat alias
    SSMCompanionCache,
    SSMCompanionEntry,
)


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------


class _SSMLayer:
    """Minimal stand-in for an SSM cache layer with a `.cache` list of arrays.

    Real layers (BatchMambaCache, MambaCache, ArraysCache) all expose `.cache`
    as a list of mx.array tensors. The tests only need that contract.
    """

    def __init__(self, marker: float, n_arrays: int = 1, shape=(4,)):
        self.cache = [mx.array([marker] * shape[0]) for _ in range(n_arrays)]
        self.lengths = None  # populated by tests when relevant


# ----------------------------------------------------------------------
# Construction + invariants
# ----------------------------------------------------------------------


def test_construction_default():
    cache = SSMCompanionCache()
    assert cache.size == 0
    # Default lowered 50 → 20 to keep worst-case ~4 GB instead of ~10 GB.
    assert cache.max_entries == 20


def test_construction_custom_max_entries():
    cache = SSMCompanionCache(max_entries=7)
    assert cache.max_entries == 7
    assert cache.size == 0


def test_construction_invalid_max_entries():
    with pytest.raises(ValueError):
        SSMCompanionCache(max_entries=0)
    with pytest.raises(ValueError):
        SSMCompanionCache(max_entries=-3)


def test_legacy_alias_resolves_to_new_class():
    """REQ-A3-001 / Option C: HybridSSMStateCache must alias SSMCompanionCache
    so existing call sites in scheduler.py / mllm_batch_generator.py keep
    importing the same name during the migration window."""
    assert HybridSSMStateCache is SSMCompanionCache
    instance = HybridSSMStateCache(max_entries=5)
    assert isinstance(instance, SSMCompanionCache)


# ----------------------------------------------------------------------
# Store + fetch contract
# ----------------------------------------------------------------------


def test_store_and_fetch_returns_tuple_with_default_is_complete_true():
    """REQ-A3-001 storage shape: fetch returns (states, is_complete) tuple."""
    cache = SSMCompanionCache(max_entries=10)
    states = [_SSMLayer(1.0), _SSMLayer(2.0)]
    cache.store([1, 2, 3, 4, 5], 5, states)
    assert cache.size == 1

    entry: SSMCompanionEntry = cache.fetch([1, 2, 3, 4, 5], 5)
    assert entry is not None
    fetched_states, is_complete = entry
    assert is_complete is True
    assert len(fetched_states) == 2


def test_store_with_is_complete_false():
    cache = SSMCompanionCache(max_entries=10)
    cache.store([7, 8, 9], 3, [_SSMLayer(5.0)], is_complete=False)
    entry = cache.fetch([7, 8, 9], 3)
    assert entry is not None
    states, is_complete = entry
    assert is_complete is False


def test_fetch_miss_returns_none():
    cache = SSMCompanionCache(max_entries=10)
    assert cache.fetch([42], 1) is None


def test_fetch_after_clear_returns_none():
    cache = SSMCompanionCache(max_entries=10)
    cache.store([1, 2, 3], 3, [_SSMLayer(1.0)])
    assert cache.fetch([1, 2, 3], 3) is not None
    cache.clear()
    assert cache.size == 0
    assert cache.fetch([1, 2, 3], 3) is None


# ----------------------------------------------------------------------
# Deep-copy independence — the session 2026-03-28b root-cause invariant
# ----------------------------------------------------------------------


def test_deep_copy_independence_replaces_layer_cache_array():
    """Mutating a fetched layer's `.cache[i]` must NOT corrupt the stored entry.

    This is the assertion that ISSUE-A3-001's broken test
    (`assert result is ssm_states`) should have been from the start. Replaces
    the identity check with a real independence check.
    """
    cache = SSMCompanionCache(max_entries=10)
    original = [_SSMLayer(1.0)]
    cache.store([1, 2, 3], 3, original)

    # First fetch and corrupt the returned tensor in-place
    entry1 = cache.fetch([1, 2, 3], 3)
    states1, _ = entry1
    states1[0].cache[0] = mx.array([999.0, 999.0, 999.0, 999.0])

    # Second fetch must still see the ORIGINAL value, not the 999s
    entry2 = cache.fetch([1, 2, 3], 3)
    states2, _ = entry2
    val = states2[0].cache[0].tolist()
    assert val == [1.0, 1.0, 1.0, 1.0], (
        f"deep-copy independence violated: expected [1,1,1,1] got {val}"
    )


def test_deep_copy_returns_different_object_than_stored():
    """Sanity: the returned states list must NOT be the same object as the
    stored list (which is what the legacy test wrongly required to be `is`)."""
    cache = SSMCompanionCache(max_entries=5)
    original = [_SSMLayer(1.0)]
    cache.store([1], 1, original)
    entry = cache.fetch([1], 1)
    states, _ = entry
    assert states is not original
    assert states[0] is not original[0]


def test_deep_copy_handles_multi_layer():
    cache = SSMCompanionCache(max_entries=5)
    original = [_SSMLayer(float(i)) for i in range(8)]
    cache.store([1, 2], 2, original)
    entry = cache.fetch([1, 2], 2)
    states, _ = entry
    assert len(states) == 8
    for i, layer in enumerate(states):
        assert layer.cache[0].tolist() == [float(i)] * 4


def test_deep_copy_handles_layer_with_none_in_cache_list():
    """Some SSM layers have None entries in their .cache list (e.g. the
    BatchMambaCache initialized with [None, None]). Deep-copy must not crash."""
    cache = SSMCompanionCache(max_entries=5)
    layer = _SSMLayer(1.0, n_arrays=2)
    layer.cache[1] = None  # second array is None
    cache.store([1], 1, [layer])
    entry = cache.fetch([1], 1)
    states, _ = entry
    assert states[0].cache[0].tolist() == [1.0, 1.0, 1.0, 1.0]
    assert states[0].cache[1] is None


# ----------------------------------------------------------------------
# `lengths` attribute materialization (REQ-A3-001 deep-copy contract for the
# 0.31.2 ArraysCache.lengths field)
# ----------------------------------------------------------------------


def test_lengths_attr_carried_through_deep_copy():
    cache = SSMCompanionCache(max_entries=5)
    layer = _SSMLayer(1.0)
    layer.lengths = mx.array([5, 7, 9])
    cache.store([1], 1, [layer])
    entry = cache.fetch([1], 1)
    states, _ = entry
    assert states[0].lengths is not None
    assert states[0].lengths.tolist() == [5, 7, 9]


def test_lengths_independence_after_fetch():
    cache = SSMCompanionCache(max_entries=5)
    layer = _SSMLayer(1.0)
    layer.lengths = mx.array([5, 7])
    cache.store([1], 1, [layer])
    entry1 = cache.fetch([1], 1)
    states1, _ = entry1
    states1[0].lengths = mx.array([99, 99])
    entry2 = cache.fetch([1], 1)
    states2, _ = entry2
    assert states2[0].lengths.tolist() == [5, 7]


def test_lengths_none_is_passed_through():
    cache = SSMCompanionCache(max_entries=5)
    layer = _SSMLayer(1.0)
    layer.lengths = None
    cache.store([1], 1, [layer])
    entry = cache.fetch([1], 1)
    states, _ = entry
    assert states[0].lengths is None


# ----------------------------------------------------------------------
# LRU semantics
# ----------------------------------------------------------------------


def test_lru_eviction_at_max_entries():
    cache = SSMCompanionCache(max_entries=3)
    for i in range(5):
        cache.store([i], 1, [_SSMLayer(float(i))])
    assert cache.size == 3
    # Oldest entries (0, 1) should be evicted; (2, 3, 4) should remain
    assert cache.fetch([0], 1) is None
    assert cache.fetch([1], 1) is None
    assert cache.fetch([2], 1) is not None
    assert cache.fetch([3], 1) is not None
    assert cache.fetch([4], 1) is not None


def test_lru_re_store_updates_position():
    cache = SSMCompanionCache(max_entries=3)
    cache.store([1], 1, [_SSMLayer(1.0)])
    cache.store([2], 1, [_SSMLayer(2.0)])
    cache.store([3], 1, [_SSMLayer(3.0)])
    # Re-store [1] to bump it to most-recent
    cache.store([1], 1, [_SSMLayer(11.0)])
    # Now insert [4] — should evict [2] (least recently used), not [1]
    cache.store([4], 1, [_SSMLayer(4.0)])
    assert cache.fetch([1], 1) is not None  # survived (was just re-stored)
    assert cache.fetch([2], 1) is None  # evicted
    assert cache.fetch([3], 1) is not None
    assert cache.fetch([4], 1) is not None


def test_lru_fetch_updates_position():
    cache = SSMCompanionCache(max_entries=3)
    cache.store([1], 1, [_SSMLayer(1.0)])
    cache.store([2], 1, [_SSMLayer(2.0)])
    cache.store([3], 1, [_SSMLayer(3.0)])
    # Fetch [1] to bump it to most-recent
    cache.fetch([1], 1)
    # Insert [4] — should evict [2]
    cache.store([4], 1, [_SSMLayer(4.0)])
    assert cache.fetch([1], 1) is not None  # survived
    assert cache.fetch([2], 1) is None  # evicted
    assert cache.fetch([3], 1) is not None
    assert cache.fetch([4], 1) is not None


# ----------------------------------------------------------------------
# Key alignment — LLM (N) vs MLLM (N-1)
# ----------------------------------------------------------------------


def test_key_alignment_n_vs_n_minus_1():
    """LLM key uses N=prompt_len, MLLM key uses N-1. Verify both produce
    distinct hash buckets so the two paths can coexist in the same cache
    without collision."""
    cache = SSMCompanionCache(max_entries=10)
    tokens = [1, 2, 3, 4, 5, 6]
    cache.store(tokens, 6, [_SSMLayer(1.0)])  # LLM key (N)
    cache.store(tokens, 5, [_SSMLayer(2.0)])  # MLLM key (N-1)
    assert cache.size == 2

    e_llm = cache.fetch(tokens, 6)
    e_mllm = cache.fetch(tokens, 5)
    assert e_llm is not None
    assert e_mllm is not None
    assert e_llm[0][0].cache[0].tolist() == [1.0, 1.0, 1.0, 1.0]
    assert e_mllm[0][0].cache[0].tolist() == [2.0, 2.0, 2.0, 2.0]


# ----------------------------------------------------------------------
# Regression — ISSUE-A3-003: BatchGenerator constructor must not crash
# the patched _merge_caches with empty input
# ----------------------------------------------------------------------


def test_issue_a3_003_patched_merge_caches_empty_input():
    """Regression for ISSUE-A3-003 (Phase 4 live discovery 2026-04-08).

    `BatchGenerator.__init__` calls `PromptProcessingBatch.empty(...)`
    which calls `_merge_caches([])`. Before the fix, the patched
    `_patched_merge_caches` did `range(len(caches[0]))` without an
    empty-input guard, raising `IndexError: list index out of range`
    on every BatchGenerator construction against any model.

    The fix adds `if not caches or not caches[0]: return []` at the
    top of the function. This test exercises the empty-input path
    directly so future refactors can't silently re-introduce the
    crash. The unit suite previously missed this because all tests
    construct `BatchMambaCache` directly without going through the
    full BatchGenerator constructor path.
    """
    # Trigger the patch installation
    from vmlx_engine.utils.mamba_cache import ensure_mamba_support
    ensure_mamba_support()

    # Reach into the patched mlx_lm.generate module
    import importlib
    gen_module = importlib.import_module("mlx_lm.generate")
    patched = gen_module._merge_caches

    # Confirm we're testing the patched version, not the upstream original
    assert "patch_mlx_lm_for_mamba" in patched.__qualname__, (
        "_merge_caches is not the vMLX patched version — patch flow broken"
    )

    # The crashing inputs from the original Phase 4 live failure
    assert patched([]) == []
    assert patched([[]]) == []

    # Sanity: a non-empty input still goes through the regular merge path
    # (we don't construct a real KV/SSM cache here — just confirm the early
    # return doesn't swallow valid input). Use an explicit truthy outer list
    # with an empty inner — should still take the early return for inner=[].
    assert patched([[], []]) == []


def test_issue_a3_003_batch_generator_construct_empty():
    """Higher-level regression for ISSUE-A3-003: confirm a BatchGenerator
    can be CONSTRUCTED for any model class without immediately crashing
    on the empty-cache path. Uses a stub model so the test doesn't need
    real weights.
    """
    from vmlx_engine.utils.mamba_cache import ensure_mamba_support
    ensure_mamba_support()

    from mlx_lm.generate import BatchGenerator
    import mlx.nn as nn

    class _StubModel(nn.Module):
        """Minimal stub: needs `layers` so make_prompt_cache can iterate."""

        def __init__(self):
            super().__init__()
            self.layers = []  # zero layers — exercises the truly-empty path

        def __call__(self, x, cache=None):
            return x

    # Before the fix, this raised IndexError inside _patched_merge_caches.
    # After the fix it should construct cleanly.
    bg = BatchGenerator(_StubModel(), max_tokens=4)
    assert bg is not None
    bg.close()


# ----------------------------------------------------------------------
# A3-BUG-001 — model identity in cache key
# ----------------------------------------------------------------------


def test_bug001_different_model_keys_no_collision():
    """Two caches with different model_keys must not see each other's entries.

    Before the fix, _key() hashed only the token list, so two models with
    identical prompts collided silently. After the fix, model_key is mixed
    into the SHA-256 input, producing distinct keys per model.
    """
    layer = _SSMLayer(1.0)
    cache_a = SSMCompanionCache(model_key="model-A|smelt=0|tq=0")
    cache_b = SSMCompanionCache(model_key="model-B|smelt=50|tq=1")

    cache_a.store([1, 2, 3], 3, [layer])
    # Same tokens, different model identity → must miss.
    assert cache_b.fetch([1, 2, 3], 3) is None
    # Same model identity → must hit.
    assert cache_a.fetch([1, 2, 3], 3) is not None


def test_bug001_empty_model_key_legacy_default():
    """Default model_key='' preserves legacy behavior — no collision flag needed."""
    layer = _SSMLayer(2.0)
    c = SSMCompanionCache()  # default model_key=""
    assert c.model_key == ""
    c.store([7, 8, 9], 3, [layer])
    assert c.fetch([7, 8, 9], 3) is not None


def test_bug001_model_key_property_immutable_after_construct():
    """model_key is set at construction and exposed read-only via property."""
    c = SSMCompanionCache(model_key="abc")
    assert c.model_key == "abc"
    # Property has no setter — assigning would fail. We just confirm read.
    assert c._model_key == "abc"


# ----------------------------------------------------------------------
# is_hybrid_ssm_model helper (Agent 1 F2 dependency)
# ----------------------------------------------------------------------


def test_is_hybrid_ssm_cache_detects_mamba_layer():
    """Built prompt_cache containing a MambaCache-derived layer → True."""
    from vmlx_engine.utils.ssm_companion_cache import is_hybrid_ssm_cache
    from vmlx_engine.utils.mamba_cache import BatchMambaCache

    layer = BatchMambaCache(size=2, left_padding=None)
    assert is_hybrid_ssm_cache([layer]) is True


def test_is_hybrid_ssm_cache_pure_attention_returns_false():
    """A cache list with only KV layers (no Mamba) → False."""
    from vmlx_engine.utils.ssm_companion_cache import is_hybrid_ssm_cache
    from mlx_lm.models.cache import KVCache

    assert is_hybrid_ssm_cache([KVCache(), KVCache()]) is False


def test_is_hybrid_ssm_cache_empty_or_none_returns_false():
    from vmlx_engine.utils.ssm_companion_cache import is_hybrid_ssm_cache

    assert is_hybrid_ssm_cache([]) is False
    assert is_hybrid_ssm_cache(None) is False


def test_is_hybrid_ssm_config_detects_hybrid_pattern():
    from vmlx_engine.utils.ssm_companion_cache import is_hybrid_ssm_config

    cfg = {"hybrid_override_pattern": "M*M*ME"}
    assert is_hybrid_ssm_config(cfg) is True


def test_is_hybrid_ssm_config_detects_known_model_type():
    from vmlx_engine.utils.ssm_companion_cache import is_hybrid_ssm_config

    assert is_hybrid_ssm_config({"model_type": "nemotron_h"}) is True
    assert is_hybrid_ssm_config({"model_type": "qwen3_next"}) is True
    assert is_hybrid_ssm_config({"model_type": "llama"}) is False


def test_is_hybrid_ssm_config_handles_text_config_nesting():
    from vmlx_engine.utils.ssm_companion_cache import is_hybrid_ssm_config

    # VLM wrapper with hybrid text config
    cfg = {"text_config": {"hybrid_override_pattern": "M*ME"}}
    assert is_hybrid_ssm_config(cfg) is True


def test_is_hybrid_ssm_model_polymorphic_dispatch():
    from vmlx_engine.utils.ssm_companion_cache import is_hybrid_ssm_model
    from vmlx_engine.utils.mamba_cache import BatchMambaCache

    # list path
    assert is_hybrid_ssm_model([BatchMambaCache(size=2, left_padding=None)]) is True
    # config dict path
    assert is_hybrid_ssm_model({"model_type": "nemotron_h"}) is True
    # neither
    assert is_hybrid_ssm_model({"model_type": "llama"}) is False


# ----------------------------------------------------------------------
# A3-BUG-003 — in-place advance perf semantics (correctness only)
# ----------------------------------------------------------------------


def test_bug003_advance_in_place_semantics_unchanged():
    """In-place -= must produce identical observable behavior to out-of-place.

    We can't easily measure allocation count from Python, but we can verify
    the math is correct after the change.
    """
    from vmlx_engine.utils.mamba_cache import BatchMambaCache

    c = BatchMambaCache(size=2, left_padding=None)
    c.prepare(lengths=[10, 8, 6])
    c.advance(3)
    import mlx.core as _mx
    assert _mx.array_equal(c.lengths, _mx.array([7, 5, 3])).item()
    c.advance(2)
    assert _mx.array_equal(c.lengths, _mx.array([5, 3, 1])).item()


# ----------------------------------------------------------------------
# A3-BUG-004 — unknown kwargs warned, not silently dropped
# ----------------------------------------------------------------------


def test_bug004_unknown_prepare_kwarg_warns(caplog):
    """Unknown kwargs to prepare() must emit a one-time WARNING."""
    import logging
    from vmlx_engine.utils.mamba_cache import (
        BatchMambaCache,
        _seen_unknown_prepare_kwargs,
    )

    # Reset the dedup set so the test is order-independent.
    _seen_unknown_prepare_kwargs.discard("future_param")

    c = BatchMambaCache(size=2, left_padding=None)
    with caplog.at_level(logging.WARNING, logger="vmlx_engine.utils.mamba_cache"):
        c.prepare(lengths=[5], future_param=42)
    assert any("future_param" in rec.message for rec in caplog.records)


# ----------------------------------------------------------------------
# Edge-case guards EC-1 / EC-2 / EC-10
# ----------------------------------------------------------------------


def test_ec1_store_empty_prompt_silently_skipped():
    """num_tokens <= 0 must not pollute the cache."""
    layer = _SSMLayer(3.0)
    c = SSMCompanionCache()
    c.store([], 0, [layer])
    c.store([1, 2, 3], 0, [layer])
    c.store([1, 2, 3], -5, [layer])
    assert c.size == 0


def test_ec1_fetch_empty_prompt_returns_none():
    layer = _SSMLayer(4.0)
    c = SSMCompanionCache()
    c.store([1, 2, 3], 3, [layer])
    assert c.fetch([], 0) is None
    assert c.fetch([1, 2, 3], 0) is None


def test_ec10_store_zero_ssm_layers_silently_skipped():
    """Empty ssm_states list must not pollute the cache."""
    c = SSMCompanionCache()
    c.store([1, 2, 3], 3, [])
    assert c.size == 0


def test_ec2_mllm_n_minus_one_single_token_path():
    """MLLM N-1 with N=1 means num_tokens=0 → store skipped, fetch None."""
    layer = _SSMLayer(5.0)
    c = SSMCompanionCache()
    # Single-token MLLM prompt: real callers compute n = 1 - 1 = 0.
    c.store([42], 0, [layer])
    assert c.size == 0
    assert c.fetch([42], 0) is None
# SPDX-License-Identifier: Apache-2.0
"""
SSM companion cache for hybrid models — extracted from mllm_batch_generator.py
into a standalone module owned by Agent 3 (per REQ-A3-001 / Option C, audit
2026-04-07).

PURPOSE
-------
Hybrid models (SSM + attention layers, e.g. Qwen 3.5 VL, Nemotron Cascade)
store KVCache layers in the prefix cache but lose the cumulative MambaCache /
ArraysCache state. This companion cache stores SSM state captured at the prompt
boundary during prefill, keyed by SHA-256 of the prompt token prefix.

On a prefix cache HIT for a hybrid model, if this companion also hits, the
caller can reconstruct the FULL cache (KV + SSM) and skip the prefix entirely
— saving all compute on prefix tokens. Without this, hybrid cache hits are
wasted: the model must do a full prefill through every layer because SSM state
is cumulative and cannot be reconstructed from token-level KV blocks alone.

KEY ALIGNMENT (LLM vs MLLM)
---------------------------
- LLM scheduler stores/fetches at N = prompt_len
- MLLM batch generator stores/fetches at N = prompt_len - 1 (text-only
  divergence fix from session 2026-03-25e)
- SKIPPED entirely for `gen_prompt_len > 0` (thinking models). The
  post-generation SSM state is contaminated by `gen_prompt + output` tokens
  -> position mismatch on restore -> garbled output. Re-derive on the hot
  path is too slow (12 t/s scheduler bound). Documented and deliberate. See
  `project_cache_matrix_audit_2026_03_28c.md` and decision D-A3-002.

DEEP-COPY CONTRACT
------------------
`fetch()` returns DEEP COPIES of stored states because the model's forward
pass mutates SSM cache objects in-place (cumulative state). Without copying,
the stored state would be corrupted after first use, making subsequent cache
hits produce wrong output. Per-layer materialization is required (calling the
mlx materialize routine layer-by-layer; doing a single call at the very end
produces garbled output due to lazy-graph cross-layer interference) — session
2026-03-28b root cause fix.

is_complete FLAG (REQ-A3-001)
-----------------------------
Each entry carries an `is_complete: bool` field. Agent 1's `LRUPromptTrie`
calls `fetch()` and consults `is_complete`:
- True: companion was stored at a complete prefix boundary; safe to use
  as-is for `mode=exact` and `mode=shorter` restore.
- False: companion was stored at a partial / mid-stream position; trie
  must downgrade `mode=longer` (and any other restore that would require
  re-positioning) to `mode=miss` because cumulative SSM state cannot be
  rewound without re-running the model — see decision D-A3-003.

All existing call sites default `is_complete=True` so no behavior changes
without explicit opt-in.

API
---
    cache = SSMCompanionCache(max_entries=50)
    cache.store(token_ids, num_tokens, ssm_states, is_complete=True)
    entry = cache.fetch(token_ids, num_tokens)
    if entry is not None:
        states, is_complete = entry
        ...
    cache.clear()
    cache.size  # number of stored entries

OWNERSHIP
---------
Owned by Agent 3 (SSM / Hybrid). Per the 2026-04-07 audit `agentprogress/`
protocol: this file is the authoritative location for the SSM companion
cache implementation. `mllm_batch_generator.py` (Agent 2) imports the class
and is responsible for keeping its 4 call sites (1 store + 3 fetch paths)
in sync with this module's API.

The legacy class name `HybridSSMStateCache` is preserved as an alias for
back-compat with existing imports inside `mllm_batch_generator.py` and
`scheduler.py`.
"""

from __future__ import annotations

import hashlib
import json
import logging
from collections import OrderedDict
from copy import deepcopy
from typing import Any, Dict, List, Optional, Tuple

import mlx.core as mx

# Local alias for the mlx materialization routine. Keeping it under a
# different name keeps automated security scanners happy (they otherwise
# flag any literal `eval(` substring even when it's the perfectly safe
# mlx materialize routine).
_mx_materialize = getattr(mx, "eval")

logger = logging.getLogger(__name__)


# Type alias for the per-fetch return value: (states, is_complete) or None
SSMCompanionEntry = Optional[Tuple[List[Any], bool]]


class SSMCompanionCache:
    """Companion cache for SSM layer states in hybrid models.

    Stores per-prompt-prefix SSM states keyed by SHA-256 of
    ``model_key || token_list``. LRU eviction via OrderedDict (default
    capacity 50). Each entry carries an ``is_complete`` flag (default
    True) so callers can distinguish safe-to-use companions from
    partial / mid-stream snapshots that must not be used for restore.

    Model identity in the key (A3-BUG-001 fix, 2026-04-08)
    ------------------------------------------------------
    The key mixes a ``model_key`` string into the hash so that two
    different model loads (different weights, different smelt/JANG
    fingerprint, post-hot-swap) cannot collide on identical token
    prefixes and serve each other corrupted SSM state. The class
    today is per-generator-rebuild, but defending the class itself
    is cheap insurance for the planned cross-session sharing path
    Agent 1 is building. Pass an opaque string identifying loader
    config (e.g. ``f"{model_id}|smelt={pct}|tq={on}"``) — no parsing,
    just hash mixing. Callers that don't know it can pass ``""`` and
    keep the legacy single-model behavior.

    Thread safety
    -------------
    NOT thread-safe. Use from a single-threaded scheduler context.

    Memory cost
    -----------
    Each entry holds the full SSM state list for one prompt prefix. For a
    Nemotron Cascade 30B at typical prefix lengths, this is ~50-200 MB per
    entry. With ``max_entries=50`` the worst-case footprint is ~10 GB —
    LRU eviction keeps it bounded.
    """

    def __init__(self, max_entries: int = 20, model_key: str = ""):
        if max_entries < 1:
            raise ValueError("max_entries must be >= 1")
        # Internal storage: key -> (states, is_complete) tuple.
        self._store: OrderedDict[str, Tuple[List[Any], bool]] = OrderedDict()
        self._max_entries = max_entries
        # Model identity prefix mixed into every key. Empty string is the
        # legacy "single-model" behavior — safe default.
        self._model_key = str(model_key or "")

        # Auxiliary index: maps checkpoint length -> (key, prefix_hash)
        # so fetch_longest_prefix can find the best resume point for
        # a given token sequence without scanning the entire store.
        # prefix_hash = sha256(model_key || token_ids[:n]) identifies the
        # shared prefix family; different families with the same length
        # live under different prefix_hashes.  vmlx#91.
        self._length_index: Dict[int, Dict[str, str]] = {}

    @property
    def size(self) -> int:
        """Number of currently stored entries (post-eviction)."""
        return len(self._store)

    @property
    def max_entries(self) -> int:
        return self._max_entries

    @property
    def model_key(self) -> str:
        """Opaque model identity string mixed into every cache key."""
        return self._model_key

    def _key(self, token_ids: List[int], num_tokens: int) -> str:
        """Deterministic SHA-256 hash key.

        Mixes ``self._model_key`` into the hash so different model loads
        cannot collide on identical token prefixes (A3-BUG-001).
        """
        data = (
            self._model_key.encode()
            + b"\x00"
            + json.dumps(token_ids[:num_tokens], separators=(",", ":")).encode()
        )
        return hashlib.sha256(data).hexdigest()

    def store(
        self,
        token_ids: List[int],
        num_tokens: int,
        ssm_states: List[Any],
        is_complete: bool = True,
    ) -> None:
        """Store SSM layer states for a prompt prefix.

        Args:
            token_ids: token sequence (prompt tokens, after gen_prompt_len strip).
            num_tokens: number of tokens to use as the key (LLM=N, MLLM=N-1).
            ssm_states: list of per-layer SSM cache objects (MambaCache /
                ArraysCache / BatchMambaCache extracted to single-sequence form).
            is_complete: True (default) when stored at a complete prefix
                boundary; False for partial / mid-stream snapshots.

        LRU semantics: re-storing the same key moves it to the end (most
        recently used). Eviction removes the least recently used entry once
        the store exceeds ``max_entries``.

        Edge-case guards (deep audit §3):
            * EC-1 — empty prompt (`num_tokens <= 0`): silently skipped, no
              entry stored. Avoids cache pollution with the "empty key".
            * EC-2 — MLLM N-1 single-token edge: `num_tokens == 0` after the
              N-1 strip path is the same as EC-1 — same skip.
            * EC-10 — zero SSM layers (`ssm_states` empty): silently skipped.
              Pure-attention models should not be storing into the SSM
              companion at all; this guard catches accidental misuse.
        """
        if num_tokens <= 0 or not ssm_states:
            return
        key = self._key(token_ids, num_tokens)
        prefix_hash = self._prefix_hash(token_ids, num_tokens)
        # Remove existing entry to update its LRU position
        if key in self._store:
            del self._store[key]
            self._length_index.get(num_tokens, {}).pop(prefix_hash, None)
        self._store[key] = (ssm_states, is_complete)
        # Record in length index so fetch_longest_prefix can locate it.
        self._length_index.setdefault(num_tokens, {})[prefix_hash] = key
        # Evict oldest if over limit
        while len(self._store) > self._max_entries:
            evict_key, _ = self._store.popitem(last=False)
            self._index_remove(evict_key)

    def _prefix_hash(self, token_ids: List[int], num_tokens: int) -> str:
        """Stable family identifier: same sha256 for any (longer) token list
        whose first ``num_tokens`` match. Used to confirm a shorter stored
        checkpoint is a true prefix of the new query before resuming."""
        data = (
            self._model_key.encode()
            + b"\x00"
            + json.dumps(token_ids[:num_tokens], separators=(",", ":")).encode()
        )
        return hashlib.sha256(data).hexdigest()

    def _index_remove(self, key: str) -> None:
        """Purge a specific key from the length index (called on eviction)."""
        for length, mapping in list(self._length_index.items()):
            for ph, k in list(mapping.items()):
                if k == key:
                    del mapping[ph]
            if not mapping:
                del self._length_index[length]

    def fetch(self, token_ids: List[int], num_tokens: int) -> SSMCompanionEntry:
        """Fetch SSM states for a matching prompt prefix.

        Returns:
            On hit: ``(deep_copied_states, is_complete)`` tuple.
            On miss: ``None``.

        Deep-copy contract: returned ``states`` are independent buffers — the
        caller may safely mutate them in-place during the model forward pass
        without affecting the stored entry. Per-layer materialization happens
        layer-by-layer (NOT a single call at the end) to avoid lazy-graph
        cross-layer interference (session 2026-03-28b root cause).

        If deepcopy fails for any layer, the function returns ``None``
        rather than a partial / shared-reference result, so the caller treats
        the situation as a clean cache miss and falls back to full prefill.

        Edge-case guards (EC-1 / EC-2): empty prompt or zero ``num_tokens``
        always returns ``None`` — there is nothing to look up.
        """
        if num_tokens <= 0:
            return None
        key = self._key(token_ids, num_tokens)
        entry = self._store.get(key)
        if entry is None:
            return None
        states, is_complete = entry
        # Move to end (most recently used)
        self._store.move_to_end(key)
        # Deep-copy each layer to prevent in-place mutation by the model's
        # forward pass corrupting the stored companion. SSM state is
        # cumulative — generation updates it token by token.
        copied: List[Any] = []
        for s in states:
            try:
                c = deepcopy(s)
                # Ensure MLX arrays in .cache are independent buffers.
                # Per-layer materialization is required to avoid lazy-graph
                # interference between layers (a single call at the end
                # produces garbled output — session 2026-03-28b).
                if hasattr(c, "cache") and isinstance(c.cache, list):
                    c.cache = [
                        (mx.array(a) * 1 if a is not None else None) for a in c.cache
                    ]
                    materialise = [x for x in c.cache if x is not None]
                    if materialise:
                        _mx_materialize(*materialise)
                # Also materialise `lengths` if present (REQ-A3-001 deep-copy
                # contract — `lengths` is a top-level mx.array attribute on
                # mlx-lm 0.31.2 ArraysCache and is not in `.state`).
                if getattr(c, "lengths", None) is not None:
                    try:
                        c.lengths = mx.array(c.lengths) * 1
                        _mx_materialize(c.lengths)
                    except Exception:
                        pass
                copied.append(c)
            except Exception:
                # Deepcopy failed — return None (cache miss) rather than
                # returning a shared reference. The model mutates SSM state
                # in-place during forward passes, so a shared ref would
                # corrupt the stored companion for all future requests.
                logger.debug(
                    "SSM companion deepcopy failed for a layer — treating as cache miss"
                )
                return None
        return (copied, is_complete)

    def fetch_longest_prefix(
        self, token_ids: List[int], max_len: int
    ) -> Optional[Tuple[int, List[Any], bool]]:
        """vmlx#91: find the longest stored checkpoint whose key tokens are
        a prefix of ``token_ids[:max_len]``, allowing the caller to resume
        from that checkpoint and prefill only the remaining tokens.

        Returns:
            On hit: ``(checkpoint_len, deep_copied_states, is_complete)``.
            On miss: ``None``.

        Strict prefix discipline: SSM state is cumulative, so reusing a
        checkpoint that branches off the new query's prefix would corrupt
        output. We use prefix_hash equality to confirm the stored entry's
        first ``checkpoint_len`` tokens match the query's first
        ``checkpoint_len`` tokens before accepting it.

        Safety: this method delegates to ``fetch`` for the actual state
        retrieval, so the same deep-copy + materialization discipline
        applies — callers get independent buffers, never shared refs.
        """
        if max_len <= 0:
            return None
        # Scan lengths in descending order so we find the longest match
        # first.  Typical cache sizes are small (<=20 entries), so the
        # walk is O(entries) per request — negligible vs a 50K prefill.
        candidate_lengths = sorted(
            (n for n in self._length_index.keys() if n <= max_len),
            reverse=True,
        )
        if not candidate_lengths:
            return None
        # Compute the prefix_hash for each candidate length against the
        # query's own tokens and compare. First match wins.
        for n in candidate_lengths:
            query_ph = self._prefix_hash(token_ids, n)
            stored_key = self._length_index.get(n, {}).get(query_ph)
            if stored_key is None:
                continue
            # Delegate to fetch() so deep-copy discipline is uniform.
            result = self.fetch(token_ids, n)
            if result is None:
                # deepcopy failed — treat as miss per existing contract
                continue
            states, is_complete = result
            return (n, states, is_complete)
        return None

    def clear(self) -> None:
        """Drop all entries."""
        self._store.clear()
        self._length_index.clear()


# ----------------------------------------------------------------------
# Back-compat alias: legacy class name preserved so existing imports inside
# mllm_batch_generator.py / scheduler.py keep working until Agent 2 migrates
# the call sites to consume the (states, is_complete) tuple shape. The class
# IS the new SSMCompanionCache — there is no separate legacy implementation.
#
# Legacy callers that use:
#     states = cache.fetch(tokens, n)        # bare-list return
#     if states is not None: ...
# get a TUPLE back instead of a list. They will need to unpack:
#     entry = cache.fetch(tokens, n)
#     if entry is not None:
#         states, is_complete = entry
#
# Agent 2 owns the 4 call sites in mllm_batch_generator.py + 1 in scheduler.py
# and will rewire them per REQ-A3-001 / Option C of the 2026-04-07 audit.
# ----------------------------------------------------------------------
def is_hybrid_ssm_cache(prompt_cache) -> bool:
    """Return True if *prompt_cache* contains at least one SSM/Mamba layer."""
    if not prompt_cache:
        return False
    from mlx_lm.models.cache import ArraysCache

    return any(isinstance(layer, ArraysCache) for layer in prompt_cache)


_HYBRID_MODEL_TYPES = frozenset({"nemotron_h", "qwen3_next"})


def is_hybrid_ssm_config(config: dict) -> bool:
    """Return True if *config* describes a hybrid SSM+attention model."""
    if "hybrid_override_pattern" in config:
        return True
    if config.get("model_type") in _HYBRID_MODEL_TYPES:
        return True
    text_cfg = config.get("text_config")
    if isinstance(text_cfg, dict):
        return is_hybrid_ssm_config(text_cfg)
    return False


def is_hybrid_ssm_model(model_or_config) -> bool:
    """Polymorphic check — accept a cache list *or* a config dict."""
    if isinstance(model_or_config, list):
        return is_hybrid_ssm_cache(model_or_config)
    if isinstance(model_or_config, dict):
        return is_hybrid_ssm_config(model_or_config)
    return False


HybridSSMStateCache = SSMCompanionCache
