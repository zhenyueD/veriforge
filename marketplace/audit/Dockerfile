# VeriForge Audit chain — Cloud Run image.
# Serves /append, /verify/{trace_id}, /reputation, /session/{id}.
# Build context = repo root:
#   docker build -f marketplace/audit/Dockerfile -t audit .
FROM python:3.12-slim

WORKDIR /app
RUN pip install --no-cache-dir fastapi "uvicorn[standard]" pydantic cryptography

COPY marketplace/ /app/marketplace/
WORKDIR /app/marketplace/audit

ENV PYTHONUNBUFFERED=1 \
    VERIFORGE_DEMO=1 \
    PORT=8001

EXPOSE 8001
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8001}"]
