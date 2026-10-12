# ==============================================================================
# Dockerfile: Deal Desk Decisions Ledger Remote MCP Server (Cloud Run SSE)
# Exposes: /sse, /messages/, /health
# Default Port: 8080 (or Cloud Run $PORT)
# ==============================================================================
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

COPY server.py /app/server.py

EXPOSE 8080

CMD ["python", "/app/server.py"]
