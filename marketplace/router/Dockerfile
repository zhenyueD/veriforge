# VeriForge Router — Cloud Run image.
# Serves discovery (/skills/search, /.well-known/*, /llms.txt, /skills/tools),
# planning (/route), and the run BFF. Build context = repo root:
#   docker build -f marketplace/router/Dockerfile -t router .
FROM python:3.12-slim

WORKDIR /app
# langfuse is optional at runtime (obs.py is a no-op until LANGFUSE_* is set),
# but baked in so the Cloud Run service can emit traces with zero rebuild.
RUN pip install --no-cache-dir \
    fastapi "uvicorn[standard]" pydantic cryptography langfuse

# Preserve the repo layout so router's sys.path + registry_path() resolve
# exactly as they do under docker compose:
#   /app/marketplace/router  (working dir)   /app/marketplace/registry/registry.json
#   /app/sdk                 (veriforge SDK on sys.path)
COPY marketplace/ /app/marketplace/
COPY sdk/ /app/sdk/

WORKDIR /app/marketplace/router

ENV PYTHONUNBUFFERED=1 \
    ENDPOINT_HOST=cloudrun \
    VERIFORGE_X402_MODE=mock \
    PORT=8000

# Cloud Run injects $PORT (8080) and ignores EXPOSE; bind it dynamically.
EXPOSE 8000
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
