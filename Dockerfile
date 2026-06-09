FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml .
COPY . .

RUN pip install --no-cache-dir -e . && \
    pip install --no-cache-dir "PyGithub>=2.0.0"

ENV BROWSER_HEADLESS=true \
    BROWSER_NO_SANDBOX=true \
    MCP_TRANSPORT=sse \
    MCP_HOST=0.0.0.0 \
    MCP_PORT=8080

CMD ["browsermcp"]
