FROM python:3.12-slim

WORKDIR /app

COPY skills/claims-intent/skill.yaml skills/claims-intent/handler.py skills/claims-intent/verify.py ./
COPY skills/claims-intent/tests ./tests/
COPY sdk /sdk

RUN pip install --no-cache-dir \
        fastapi==0.115.* \
        "uvicorn[standard]==0.32.*" \
        pydantic==2.9.* \
        google-genai>=0.3 \
        Pillow>=11 \
        imagehash>=4.3 \
        python-multipart>=0.0.20 \
        slowapi>=0.1.9 \
        openai>=2.0

COPY vendor/claimsforge/agents /claimsforge/agents

# Verify the copy worked and the import resolves at build time
RUN python3 -c "import sys,os; sys.path.insert(0,'/claimsforge/agents'); print(os.listdir('/claimsforge/agents')); from intent_agent import classify; print('intent_agent OK')"

ENV CLAIMSFORGE_PATH=/claimsforge
ENV PYTHONPATH=/claimsforge/agents
ENV PYTHONUNBUFFERED=1

EXPOSE 7001
CMD ["uvicorn", "handler:app", "--host", "0.0.0.0", "--port", "7001"]
