FROM alpine:3.21
RUN apk add --no-cache python3 py3-pip tzdata git openssh
WORKDIR /app
COPY . .
RUN python3 -m venv /app/.venv \
    && /app/.venv/bin/pip install --no-cache-dir -r requirements.txt
RUN mkdir -p /app/logs && chmod 700 /app/logs
ENV PYTHONUNBUFFERED=1
ENV PATH="/app/.venv/bin:$PATH"
CMD ["python3", "-m", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]