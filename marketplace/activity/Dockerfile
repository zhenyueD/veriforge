# VeriForge Activity stream — Cloud Run image.
# Serves /emit, /stream/{session_id} (long-poll), /session/{id}.
# Build context = repo root:
#   docker build -f marketplace/activity/Dockerfile -t activity .
FROM python:3.12-slim

WORKDIR /app
RUN pip install --no-cache-dir fastapi "uvicorn[standard]" pydantic

COPY marketplace/ /app/marketplace/
WORKDIR /app/marketplace/activity

ENV PYTHONUNBUFFERED=1 \
    PORT=8002

EXPOSE 8002
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8002}"]
