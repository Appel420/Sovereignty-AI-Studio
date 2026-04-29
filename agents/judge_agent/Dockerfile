FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir prometheus-client

COPY agents/judge_agent/ ./agents/judge_agent/
COPY agents/__init__.py ./agents/

ENV JUDGE_METRICS_PORT=9898

EXPOSE 9898

CMD ["python", "-m", "agents.judge_agent.judge"]
