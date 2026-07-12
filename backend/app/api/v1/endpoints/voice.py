"""
Voice interaction API endpoints.
Provides voice chat and TTS capabilities using Piper TTS.
"""
import hashlib
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from typing import Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class VoiceRequest(BaseModel):
    text: str
    voice_model: Optional[str] = None
    speed: float = 1.0


class VoiceResponse(BaseModel):
    status: str
    message: str
    audio_file: Optional[str] = None
    voice_model: str = "piper-default"


class CollaborationTaskRequest(BaseModel):
    goal: str = Field(min_length=1, max_length=4000)
    acceptance_criteria: list[str] = Field(min_length=1, max_length=50)
    agent_id: str = "copilot"
    tests_required: list[str] = Field(default_factory=list, max_length=50)
    allowed_paths: list[str] = Field(default_factory=list, max_length=100)


class CollaborationRequest(BaseModel):
    task_id: str
    transcript: str = Field(min_length=1, max_length=8000)


class ProgressRequest(BaseModel):
    files_changed: list[str] = Field(default_factory=list, max_length=100)
    validation: list[dict[str, str]] = Field(default_factory=list, max_length=100)
    next_step: str = Field(min_length=1, max_length=2000)


class ApprovalRequest(BaseModel):
    action: str
    details: str = Field(min_length=1, max_length=4000)


class VoiceProcessRequest(BaseModel):
    text: str = Field(min_length=1, max_length=8000)
    session_id: Optional[str] = None
    user_id: Optional[str] = Field(default=None, max_length=255)
    voice_model: str = Field(default="en_US-lessac-medium", max_length=255)
    device_fingerprint: Optional[str] = Field(default=None, max_length=4096)
    offline_first: bool = True


def _resolve_voice_user_id(
    user_id: Optional[str],
    device_fingerprint: Optional[str],
) -> str:
    if user_id and user_id.strip():
        return user_id.strip()
    if device_fingerprint and device_fingerprint.strip():
        digest = hashlib.sha256(device_fingerprint.strip().encode("utf-8")).hexdigest()
        return f"device-{digest[:24]}"
    return "default"


def _ensure_session(
    session_id: Optional[str],
    user_id: Optional[str],
    voice_model: str,
    device_fingerprint: Optional[str],
) -> str:
    from app.services.voice_interaction_service import voice_interaction_service

    if session_id:
        if not voice_interaction_service.get_session(session_id):
            raise HTTPException(status_code=404, detail="Voice session not found")
        return session_id

    session = voice_interaction_service.create_session(
        _resolve_voice_user_id(user_id, device_fingerprint),
        voice_model,
    )
    return session.session_id


@router.post("/speak", response_model=VoiceResponse)
async def text_to_speech(request: VoiceRequest):
    """
    Convert text to speech using Piper TTS.

    Returns the path to the generated audio file.
    """
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    try:
        from app.services.piper_tts_service import piper_service
        audio_file = piper_service.text_to_speech(request.text)
        if audio_file:
            return VoiceResponse(
                status="completed",
                message="Audio generated successfully",
                audio_file=audio_file,
                voice_model=request.voice_model or "piper-default",
            )
        return VoiceResponse(
            status="unavailable",
            message="Piper TTS not available. Install piper and configure PIPER_MODEL_PATH.",
        )
    except Exception as e:
        logger.error(f"TTS error: {e}")
        return VoiceResponse(
            status="error",
            message=f"TTS generation failed: {str(e)}",
        )


@router.post("/chat", response_model=dict)
async def voice_chat(request: VoiceRequest):
    """
    Voice interaction endpoint.
    Processes text input and returns AI response with optional TTS.
    """
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    from app.services.voice_collaboration_service import voice_collaboration_service

    task = voice_collaboration_service.create_task(
        goal=request.text,
        acceptance_criteria=["Return a scoped proposal before any execution."],
        agent_id="copilot",
    )
    result = await voice_collaboration_service.collaborate(task["task_id"], request.text)
    result["input"] = request.text
    result["audio_file"] = None

    # Generate audio for response
    try:
        from app.services.piper_tts_service import piper_service
        audio_file = piper_service.text_to_speech(result["response"])
        if audio_file:
            result["audio_file"] = audio_file
    except Exception as e:
        logger.warning(f"Voice chat TTS failed: {e}")

    return result


@router.post("/process", response_model=dict)
async def process_voice(request: VoiceProcessRequest):
    """Process a text turn with the local voice interaction service."""
    from app.services.voice_interaction_service import voice_interaction_service

    session_id = _ensure_session(
        request.session_id,
        request.user_id,
        request.voice_model,
        request.device_fingerprint,
    )
    result = voice_interaction_service.process_text_input(
        session_id,
        request.text,
        offline_first=request.offline_first,
    )
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    result["offline"] = request.offline_first
    return result


@router.post("/input", response_model=dict)
async def process_voice_input(
    audio: UploadFile = File(...),
    session_id: Optional[str] = Form(None),
    user_id: Optional[str] = Form(None),
    voice_model: str = Form("en_US-lessac-medium"),
    device_fingerprint: Optional[str] = Form(None),
    process_after_transcription: bool = Form(True),
):
    """Transcribe microphone audio locally and optionally process it offline."""
    suffix = (audio.filename or "audio.webm").rsplit(".", 1)[-1]
    payload = await audio.read()
    from app.services.local_stt_service import local_stt_service

    transcription = local_stt_service.transcribe_bytes(payload, suffix)
    response = {
        "status": transcription["status"],
        "transcription": transcription,
        "offline": True,
    }
    transcript_text = str(transcription.get("text", "")).strip()
    if transcription["status"] != "completed" or not process_after_transcription or not transcript_text:
        return response

    response["processing"] = await process_voice(
        VoiceProcessRequest(
            text=transcript_text,
            session_id=session_id,
            user_id=user_id,
            voice_model=voice_model,
            device_fingerprint=device_fingerprint,
            offline_first=True,
        )
    )
    return response


@router.post("/transcribe", response_model=dict)
async def transcribe_audio(audio: UploadFile = File(...)):
    """Transcribe microphone audio with a locally provisioned STT model."""
    suffix = (audio.filename or "audio.webm").rsplit(".", 1)[-1]
    payload = await audio.read()
    from app.services.local_stt_service import local_stt_service

    return local_stt_service.transcribe_bytes(payload, suffix)


@router.post("/tasks", response_model=dict)
async def create_collaboration_task(request: CollaborationTaskRequest):
    """Create a durable, single-agent coding task."""
    from app.services.voice_collaboration_service import voice_collaboration_service

    try:
        return voice_collaboration_service.create_task(**request.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/tasks/{task_id}", response_model=dict)
async def get_collaboration_task(task_id: str):
    """Get the current durable voice-collaboration task state."""
    from app.services.voice_collaboration_service import voice_collaboration_service

    task = voice_collaboration_service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Voice collaboration task not found")
    return task


@router.post("/collaborate", response_model=dict)
async def collaborate(request: CollaborationRequest):
    """Send a transcript to the selected coordinator without granting execution."""
    from app.services.voice_collaboration_service import voice_collaboration_service

    try:
        return await voice_collaboration_service.collaborate(**request.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/tasks/{task_id}/progress", response_model=dict)
async def report_progress(task_id: str, request: ProgressRequest):
    """Record the files, validation results, and next step after an edit."""
    from app.services.voice_collaboration_service import voice_collaboration_service

    try:
        return voice_collaboration_service.report_progress(task_id, **request.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/tasks/{task_id}/approval-request", response_model=dict)
async def request_approval(task_id: str, request: ApprovalRequest):
    """Require explicit user approval before scope, execution, commit, or PR actions."""
    from app.services.voice_collaboration_service import voice_collaboration_service

    try:
        return voice_collaboration_service.request_approval(task_id, **request.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/tasks/{task_id}/approve/{action}", response_model=dict)
async def approve_action(task_id: str, action: str):
    """Record explicit approval; this endpoint never executes code."""
    from app.services.voice_collaboration_service import voice_collaboration_service

    try:
        return voice_collaboration_service.approve(task_id, action)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/status", response_model=dict)
async def voice_status():
    """Check voice system status and available models."""
    from app.services.local_stt_service import local_stt_service
    try:
        from app.services.piper_tts_service import piper_service
        piper_available = piper_service.piper_executable is not None
    except Exception:
        piper_available = False

    return {
        "piper_tts": {
            "available": piper_available,
            "engine": "piper",
            "description": "On-device text-to-speech using Piper",
        },
        "voice_models": ["piper-default"],
        "stt": local_stt_service.status(),
        "collaboration": {
            "offline_by_default": True,
            "execution_gated": True,
            "agents": ["grok", "claude", "gpt", "copilot"],
        },
        "status": "online" if piper_available else "degraded",
    }
