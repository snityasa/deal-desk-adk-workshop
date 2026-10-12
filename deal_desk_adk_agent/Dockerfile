# ==============================================================================
# Dockerfile: Autonomous B2B Deal Desk & Margin Optimizer (Google ADK Multi-Agent)
# Serves ADK Web UI (`/`) + A2A Protocol Endpoints (`/a2a/deal_desk_adk_agent`)
# Default Port: 8081 (or Cloud Run $PORT)
# ==============================================================================
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/workspace \
    PORT=8081 \
    ADK_DISABLE_LOCAL_STORAGE=1

WORKDIR /workspace

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /workspace/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /workspace/requirements.txt

# Copy agent package into /workspace/deal_desk_adk_agent
COPY . /workspace/deal_desk_adk_agent

# Provide /workspace/app symlink alias for A2A/ADK compatibility
RUN ln -s /workspace/deal_desk_adk_agent /workspace/app

EXPOSE 8081

CMD ["python", "/workspace/deal_desk_adk_agent/server.py"]
