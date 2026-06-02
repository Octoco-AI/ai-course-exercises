"""FastAPI app. One streaming endpoint, plus health and static-UI serving.

Endpoints:
  - GET  /health               → {"status": "ok"}
  - POST /api/chat             → SSE stream; body: {"message": str, "history": list?}
  - GET  /                     → serves the built React UI from ui/dist/ if present
  - GET  /assets/{path}        → static assets for the UI
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .agent import run_agent_streaming
from .settings import Settings, load_settings
from .streaming import error_event
from .tools import ToolSet


load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Track A — Codebase Q&A agent",
    version="0.1.0",
    description="Streaming agent over the TodoMagic corpus.",
)

# Module-level singletons — lazily initialised on first request so tests don't
# need Anthropic credentials to import the module.
_settings: Settings | None = None
_tools: ToolSet | None = None


def _get_runtime() -> tuple[Settings, ToolSet]:
    global _settings, _tools
    if _settings is None:
        _settings = load_settings()
        _tools = ToolSet(
            workspace_root=_settings.workspace_root,
            chroma_persist_root=_settings.chroma_persist_root,
            chroma_collection_name=_settings.chroma_collection_name,
            patches_root=_settings.patches_root,
        )
        logger.info("runtime initialised (model=%s, workspace=%s)", _settings.model, _settings.workspace_root)
    assert _tools is not None
    return _settings, _tools


# ---- API ------------------------------------------------------------------


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    history: list[dict] | None = None


@app.post("/api/chat")
async def chat(req: ChatRequest, request: Request) -> StreamingResponse:
    """Stream the agent's response as Server-Sent Events."""
    try:
        settings, tools = _get_runtime()
    except RuntimeError as exc:
        # Configuration error (no API key, no workspace). Respond with a
        # synchronous SSE error event so the client sees it in the chat.
        # Capture the message into a local var — Python closures bind by
        # name, and `exc` is out of scope by the time the async generator runs.
        error_message = str(exc)

        async def error_stream():
            yield error_event(error_message)

        return StreamingResponse(
            error_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    async def event_stream():
        try:
            async for event in run_agent_streaming(
                req.message,
                history=req.history,
                settings=settings,
                tools=tools,
            ):
                # If the client disconnects, stop iterating — otherwise the
                # agent keeps calling tools into the void (and spending tokens).
                if await request.is_disconnected():
                    logger.info("client disconnected mid-stream; stopping agent")
                    return
                yield event
        except Exception as exc:  # noqa: BLE001
            logger.exception("unexpected error in agent stream")
            yield error_event(f"{type(exc).__name__}: {exc}")

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # disable nginx/uvicorn response buffering
        },
    )


# ---- Static UI ------------------------------------------------------------
# If the UI has been built (`cd ui && npm run build`), serve ui/dist/. If
# not, the root path returns a helpful hint.


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
                "then restart the server. The streaming endpoint at /api/chat is usable "
                "without the UI — try `curl -N -X POST http://localhost:8000/api/chat "
                "-H 'Content-Type: application/json' -d '{\"message\": \"list the files here\"}'`."
            ),
        }


# ---- dev entrypoint -------------------------------------------------------


def dev_main() -> None:
    import uvicorn

    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("backend.server:app", host=host, port=port, reload=True)


if __name__ == "__main__":
    dev_main()
