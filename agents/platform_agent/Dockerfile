FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir httpx websockets

COPY agents/platform_agent/ ./agents/platform_agent/
COPY agents/__init__.py ./agents/
COPY agents/judge_agent/ ./agents/judge_agent/
COPY platform_connectors/ ./platform_connectors/
COPY event_bus/ ./event_bus/

EXPOSE 9899

CMD ["python", "-c", "from agents.platform_agent.platform_manager import PlatformAgent; print('Platform Agent ready')"]
