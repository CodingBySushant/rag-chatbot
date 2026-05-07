# =============================================================================
# MULTI-STAGE BUILD
#
# WHY TWO STAGES?
#   Stage 1 (builder): Installs gcc, compilers, build tools needed to compile
#   Python packages that have C extensions (numpy, tokenizers, etc.)
#
#   Stage 2 (runtime): Fresh clean image — only copies compiled packages from
#   Stage 1. No compilers, no temp files, no build cruft.
#
#   Result: image ~950MB instead of ~1.8GB. Smaller = faster Cloud Run cold starts.
# =============================================================================

# ── Stage 1: builder ──────────────────────────────────────────────────────────
# python:3.11-slim = official Debian Bookworm slim + Python 3.11.
# Never use :latest in production — it changes silently and breaks builds.
FROM python:3.11-slim AS builder

WORKDIR /app

# Install OS-level build tools.
# build-essential = gcc, g++, make — needed by packages with C extensions.
# --no-install-recommends skips suggested packages (~100MB saved).
# rm in the SAME RUN command clears apt cache inside the layer.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements.txt BEFORE the rest of the code.
# WHY: Docker builds layer by layer. If requirements.txt is unchanged,
# Docker reuses the cached pip layer — saving 3-5 min per build.
# Copying everything first means any code change busts the pip cache.
COPY requirements.txt .

# Install into /install prefix so Stage 2 can COPY just the packages.
# --no-cache-dir = don't store .whl files inside the layer (saves disk).
RUN pip install --upgrade pip \
    && pip install --prefix=/install --no-cache-dir -r requirements.txt


# ── Stage 2: runtime ──────────────────────────────────────────────────────────
# Fresh python:3.11-slim — zero compilers, zero build tools, zero temp files.
FROM python:3.11-slim AS runtime

WORKDIR /app

# Copy compiled packages from builder. /install maps cleanly into /usr/local
# so Python finds everything on the standard sys.path automatically.
COPY --from=builder /install /usr/local

# Copy application source. .dockerignore excludes .env, __pycache__,
# qdrant_storage/, venv/ etc. — see .dockerignore.
COPY . .

# Create a non-root user and switch to it.
# WHY: Running as root inside a container is a security risk. If the app is
# compromised, the attacker gets root inside the container. Non-root limits
# the blast radius. Required practice at every serious company.
RUN useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser /app
USER appuser

# Cloud Run injects PORT env var at runtime (usually 8080).
# Default 8000 so local docker run -p 8000:8000 also works.
ENV PORT=8000
EXPOSE ${PORT}

# Shell form (not exec form) so $PORT expands at container startup.
# --host 0.0.0.0 is REQUIRED — without it Cloud Run can't reach the app.
# --workers 1 because Cloud Run scales horizontally (more containers),
# not vertically (more workers). Multiple workers waste RAM here.
CMD uvicorn api:app --host 0.0.0.0 --port ${PORT} --workers 1
