# Multi-stage build: compile the Vite UI, then copy the bundle into the
# Python backend image. Running the container starts FastAPI; it serves
# both /api/chat and the static UI from /ui/dist.

# ---- UI build stage ----
FROM node:22-alpine AS ui-build
WORKDIR /ui
COPY ui/package.json ui/package-lock.json* ./
RUN npm install --legacy-peer-deps
COPY ui/ ./
RUN npm run build

# ---- Backend runtime stage ----
FROM python:3.12-slim-bookworm
WORKDIR /app

# Install system deps that chromadb needs on slim images.
RUN apt-get update \
 && apt-get install -y --no-install-recommends gcc libstdc++6 \
 && rm -rf /var/lib/apt/lists/*

# Python deps first (cache-friendly)
COPY pyproject.toml README.md* ./
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -e . \
 || true  # retry below once sources are in

# Copy sources.
COPY backend/ ./backend/

# Copy built UI from the earlier stage.
COPY --from=ui-build /ui/dist ./ui/dist

# Workspace + patches live inside the container and are expected to be
# volume-mounted at runtime (docker-compose handles this).
RUN mkdir -p /app/workspace /app/patches
ENV WORKSPACE_ROOT=/app/workspace \
    PATCHES_ROOT=/app/patches

# Chroma index is also expected via mount (read-only works).
ENV CHROMA_PERSIST_ROOT=/app/chroma-index \
    CHROMA_COLLECTION_NAME=track-a-codebase

# Re-run the pip install now that all source is present (ensures -e install
# picks up the package layout).
RUN pip install --no-cache-dir -e .

EXPOSE 8000

CMD ["uvicorn", "backend.server:app", "--host", "0.0.0.0", "--port", "8000"]
