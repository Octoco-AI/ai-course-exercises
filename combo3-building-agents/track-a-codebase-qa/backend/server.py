"""FastAPI app. Health check for now; Module 3 adds the streaming endpoint.

Endpoints:
  - GET  /health               → {"status": "ok"}
  - POST /api/chat             → Module 3, Part A. Not implemented yet.
  - GET  /                     → serves the built React UI from ui/dist/ if present
  - GET  /assets/{path}        → static assets for the UI
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .settings import Settings, load_settings
from .tools import ToolSet, build_toolset


load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Track A — Codebase Q&A agent",
    version="0.1.0",
    description="Agent over the TodoMagic workspace.",
)

_settings: Settings | None = None
_tools: ToolSet | None = None


def _get_runtime() -> tuple[Settings, ToolSet]:
    global _settings, _tools
    if _settings is None:
        _settings = load_settings()
        _tools = build_toolset(_settings.workspace_root)
        logger.info("runtime initialised (model=%s, workspace=%s)", _settings.model, _settings.workspace_root)
    assert _tools is not None
    return _settings, _tools


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Module 3, Part A — POST /api/chat
#
# Add a `ChatRequest(BaseModel)` with `message: str` + `history: list[dict]
# | None`, then a handler that calls `_get_runtime()`, builds a
# `StreamingResponse(run_agent_streaming(...), media_type="text/event-stream",
# headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})`. Wire
# the imports (`from .agent import run_agent_streaming`, `from fastapi
# import Request`, `from fastapi.responses import StreamingResponse`,
# `from pydantic import BaseModel`).
# ---------------------------------------------------------------------------


_ui_dist = Path(__file__).parent.parent / "ui" / "dist"

if _ui_dist.exists():
    app.mount("/assets", StaticFiles(directory=_ui_dist / "assets"), name="ui-assets")

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(_ui_dist / "index.html")

else:

    @app.get("/")
    def index_fallback() -> dict[str, str]:
        return {
            "status": "no-ui",
            "hint": (
                "The UI hasn't been built yet. Run `cd ui && npm install && npm run build`, "
                "then restart the server. Until Module 3 wires /api/chat, use "
                "`run_agent.py` from the repo root to talk to the agent."
            ),
        }


def dev_main() -> None:
    import uvicorn

    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("backend.server:app", host=host, port=port, reload=True)


if __name__ == "__main__":
    dev_main()
