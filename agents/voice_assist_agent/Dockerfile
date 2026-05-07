FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir pyttsx3 || true

COPY agents/voice_assist_agent/ ./agents/voice_assist_agent/
COPY agents/__init__.py ./agents/
COPY agents/judge_agent/ ./agents/judge_agent/
COPY event_bus/ ./event_bus/

EXPOSE 9899

CMD ["python", "-c", "from agents.voice_assist_agent.voice_manager import VoiceAssistAgent; print('Voice Assist Agent ready')"]
