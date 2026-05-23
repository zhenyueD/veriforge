FROM python:3.12-slim

WORKDIR /app

# Install runtime dependencies. ClaimsForge requirements are inherited via
# the mounted /claimsforge volume at runtime — see docker-compose.yml.
RUN pip install --no-cache-dir \
        fastapi==0.115.* \
        "uvicorn[standard]==0.32.*" \
        pydantic==2.9.* \
        google-genai>=0.3 \
        Pillow>=11

COPY skill.yaml handler.py verify.py ./
COPY tests/ ./tests/

ENV CLAIMSFORGE_PATH=/claimsforge
ENV PYTHONUNBUFFERED=1

EXPOSE 7001
CMD ["uvicorn", "handler:app", "--host", "0.0.0.0", "--port", "7001"]
