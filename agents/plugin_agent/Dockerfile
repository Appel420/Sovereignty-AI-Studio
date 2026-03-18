FROM python:3.11-slim

WORKDIR /app

COPY agents/plugin_agent/ ./agents/plugin_agent/
COPY agents/__init__.py ./agents/
COPY agents/judge_agent/ ./agents/judge_agent/
COPY plugin_sdk/ ./plugin_sdk/
COPY event_bus/ ./event_bus/

ENV PLUGIN_SDK_DIR=/app/plugin_sdk

EXPOSE 8002

CMD ["python", "-c", "from agents.plugin_agent.plugin_manager import PluginAgent; print('Plugin Agent ready')"]
