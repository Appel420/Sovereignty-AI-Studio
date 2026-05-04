FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir aiohttp httpx

COPY agents/ ./agents/
COPY event_bus/ ./event_bus/
COPY platform_connectors/ ./platform_connectors/
COPY plugin_sdk/ ./plugin_sdk/
COPY gateway/ ./gateway/

ENV PLUGIN_SDK_DIR=/app/plugin_sdk
ENV GATEWAY_PORT=9898

EXPOSE 9898

CMD ["python", "-m", "gateway.main"]
