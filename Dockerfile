# Single-stage build. The Docker VM on the target machine is memory-constrained,
# so we avoid a multi-stage `COPY --from=builder` of the ~1 GB venv (that step
# OOM-crashed the VM) and skip importing torch at build time. The embedding
# model is downloaded on first container start instead (cached in a volume).
FROM ghcr.io/astral-sh/uv:python3.13-trixie-slim

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_DEV=1 \
    UV_PYTHON_DOWNLOADS=0 \
    UV_HTTP_TIMEOUT=120 \
    UV_CACHE_DIR=/tmp/uv-cache \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/app/.cache/huggingface \
    PATH="/app/.venv/bin:$PATH"

RUN groupadd --system --gid 999 nonroot \
 && useradd --system --gid 999 --uid 999 --create-home nonroot

WORKDIR /app
RUN chown nonroot:nonroot /app
USER nonroot

# Install dependencies first (cached unless the lockfile changes).
COPY --chown=nonroot:nonroot pyproject.toml uv.lock ./
RUN uv sync --locked --no-install-project && rm -rf /tmp/uv-cache

# Application source.
COPY --chown=nonroot:nonroot . /app

# Writable runtime dirs: the ChromaDB vector store and the HuggingFace model
# cache. Both are mounted as volumes by docker-compose so they survive restarts.
RUN mkdir -p /app/backend/chroma_db /app/.cache/huggingface

# app.py resolves "../docs" and "../frontend" relative to this directory.
WORKDIR /app/backend

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=90s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/courses')"]

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
