# VeriForge MCP server — container image for Smithery / any MCP host.
# Serves the streamable-http transport on $PORT at /mcp.
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY server.py backend.py ./

# Smithery injects PORT; http transport binds 0.0.0.0:$PORT/mcp.
ENV MCP_TRANSPORT=streamable-http \
    PORT=8081 \
    VERIFORGE_ROUTER_URL=http://localhost:8000
EXPOSE 8081

CMD ["python", "server.py"]
