"""
Avatar Companion Service – on-device AI avatar for interactive user guidance.

Provides a persistent AI avatar companion with configurable personality,
appearance, and interaction modes for the Sovereignty AI Studio.
"""
import uuid
import logging
from enum import Enum
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class AvatarMood(str, Enum):
    NEUTRAL = "neutral"
    HAPPY = "happy"
    THINKING = "thinking"
    ALERT = "alert"
    FOCUSED = "focused"


class AvatarStyle(str, Enum):
    MINIMAL = "minimal"
    REALISTIC = "realistic"
    ANIME = "anime"
    ROBOTIC = "robotic"


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

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()


class AvatarCompanionService:
    """Manages AI avatar companions for users."""

    def __init__(self):
        self._avatars: Dict[str, AvatarProfile] = {}
        logger.info("AvatarCompanionService initialised")

    def create_avatar(
        self,
        user_id: str,
        name: str = "Ara",
        style: str = "minimal",
        voice_id: str = "en_US-lessac-medium",
        personality: str = "helpful",
    ) -> Dict[str, Any]:
        """Create a new avatar companion for a user."""
        avatar = AvatarProfile(
            avatar_id=str(uuid.uuid4()),
            user_id=user_id,
            name=name,
            style=AvatarStyle(style),
            voice_id=voice_id,
            personality=personality,
        )
        self._avatars[avatar.avatar_id] = avatar
        logger.info("Avatar '%s' (%s) created for user %s", name, avatar.avatar_id, user_id)
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
        avatar.mood = AvatarMood(mood)
        return self._avatar_to_dict(avatar)

    def interact(self, avatar_id: str, message: str) -> Dict[str, Any]:
        """Handle an interaction with the avatar companion."""
        avatar = self._avatars.get(avatar_id)
        if not avatar:
            return {"error": "Avatar not found"}

        avatar.interaction_count += 1
        avatar.mood = AvatarMood.THINKING

        response = self._generate_avatar_response(avatar, message)
        avatar.mood = AvatarMood.HAPPY

        return {
            "avatar_id": avatar.avatar_id,
            "name": avatar.name,
            "mood": avatar.mood.value,
            "response": response,
            "interaction_count": avatar.interaction_count,
        }

    def delete_avatar(self, avatar_id: str) -> bool:
        if avatar_id in self._avatars:
            del self._avatars[avatar_id]
            return True
        return False

    def get_status(self) -> Dict[str, Any]:
        return {
            "service": "avatar_companion",
            "status": "online",
            "active_avatars": len(self._avatars),
            "available_styles": [s.value for s in AvatarStyle],
            "available_moods": [m.value for m in AvatarMood],
        }

    # ── Private helpers ──────────────────────────────────────────────

    def _generate_avatar_response(
        self, avatar: AvatarProfile, message: str
    ) -> str:
        """Generate a contextual response from the avatar via sovereign AI router.

        Routes through xAI → Anthropic → OpenAI with automatic fallback.
        Falls back to acknowledgement only if no providers are configured.
        """
        try:
            import asyncio
            from app.services.ai_router import ai_router

            if not ai_router.available_providers:
                logger.warning("No AI providers configured – returning acknowledgement")
                return f"[{avatar.name}] Received: '{message}'"

            system_prompt = (
                f"You are {avatar.name}, an AI companion avatar in the "
                f"Sovereignty AI Studio. Your personality is {avatar.personality}. "
                f"Your current mood is {avatar.mood.value}. "
                "Help the user with media creation, project building, voice "
                "interaction, and creative workflows. Be concise and in character."
            )

            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    result = pool.submit(
                        asyncio.run,
                        ai_router.chat(
                            prompt=message,
                            system=system_prompt,
                            max_tokens=512,
                            temperature=0.7,
                        ),
                    ).result(timeout=30)
            else:
                result = asyncio.run(
                    ai_router.chat(
                        prompt=message,
                        system=system_prompt,
                        max_tokens=512,
                        temperature=0.7,
                    )
                )

            return result.get("text", f"[{avatar.name}] Received: '{message}'")
        except Exception as exc:
            logger.error("Avatar AI response failed: %s", exc)
            return f"[{avatar.name} – AI unavailable] Received: '{message}'"

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
        }


# Module-level singleton
avatar_companion_service = AvatarCompanionService()
