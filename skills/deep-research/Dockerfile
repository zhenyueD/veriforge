# deep-research skill — bundles MiroMind's MiroFlow framework + its deps.
# Build context is the repo root (needs external/MiroFlow + sdk/ + this skill).
#   docker compose build deep-research
FROM python:3.12-slim

# Node 20 — MiroFlow spawns the serper search tool via `npx serper-search-scrape-mcp-server`.
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# uv + the skill's own web framework
RUN pip install --no-cache-dir uv fastapi "uvicorn[standard]" pydantic cryptography

# MiroFlow framework + its (heavy) deps, synced into /miroflow/.venv (linux).
COPY external/MiroFlow/ /miroflow/
WORKDIR /miroflow
RUN uv sync --no-dev

# The thin skill wrapper.
COPY sdk/veriforge.py /app/veriforge.py
COPY skills/deep-research/handler.py /app/handler.py
COPY skills/deep-research/verify.py /app/verify.py

ENV MIROFLOW_DIR=/miroflow \
    MIROFLOW_PY=/miroflow/.venv/bin/python \
    MIROFLOW_CONFIG=agent_llm_gpt4o \
    PYTHONUNBUFFERED=1
WORKDIR /app
EXPOSE 7008
CMD ["uvicorn", "handler:app", "--host", "0.0.0.0", "--port", "7008"]
