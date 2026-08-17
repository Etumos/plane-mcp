FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY plane_mcp/ ./plane_mcp/

RUN pip install --no-cache-dir '.[http]'

ENV PLANE_MCP_HTTP=1 \
    PLANE_MCP_HOST=0.0.0.0 \
    PLANE_MCP_PORT=8000

EXPOSE 8000

ENTRYPOINT ["plane-project-mcp"]
