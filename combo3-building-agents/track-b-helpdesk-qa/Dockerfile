# Same multi-stage pattern as Track A: build UI in Node, copy into Python container.

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

RUN apt-get update \
 && apt-get install -y --no-install-recommends gcc libstdc++6 \
 && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md* ./
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -e . \
 || true

COPY backend/ ./backend/
COPY --from=ui-build /ui/dist ./ui/dist

RUN mkdir -p /app/workspace /app/draft-replies /app/escalations
ENV WORKSPACE_ROOT=/app/workspace \
    DRAFT_REPLIES_ROOT=/app/draft-replies \
    ESCALATIONS_ROOT=/app/escalations \
    CHROMA_PERSIST_ROOT=/app/chroma-index \
    CHROMA_COLLECTION_NAME=track-b-helpdesk

RUN pip install --no-cache-dir -e .

EXPOSE 8000

CMD ["uvicorn", "backend.server:app", "--host", "0.0.0.0", "--port", "8000"]
