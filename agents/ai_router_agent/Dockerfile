FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir httpx

COPY agents/ai_router_agent/ ./agents/ai_router_agent/
COPY agents/__init__.py ./agents/
COPY agents/judge_agent/ ./agents/judge_agent/
COPY event_bus/ ./event_bus/

EXPOSE 8001

CMD ["python", "-c", "import asyncio; from agents.ai_router_agent.router import AIRouterAgent; print('AI Router Agent ready')"]
