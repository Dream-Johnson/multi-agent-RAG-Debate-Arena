"""
FastAPI application — wires together the password gate, the debate
orchestrator, and the frontend static files into one running app.
"""

from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

from auth import verify_password
from debate import run_debate
from models import DebateRequest, DebateResult
from wikipedia_service import WikipediaNotFoundError

app = FastAPI(title="Multi-Agent Debate Simulator")


@app.post("/api/login")
async def login(_: None = Depends(verify_password)) -> dict:
    """
    Validate the password. verify_password() already raised a 401 if it
    was wrong, so simply reaching this line means it was correct.
    """
    return {"ok": True}


@app.post("/api/debate", response_model=DebateResult)
async def start_debate(
    request: DebateRequest, _: None = Depends(verify_password)
) -> DebateResult:
    """
    Run a full debate on the given topic and return the result.

    The first call ever made to this endpoint also lazily ensures the
    Pinecone index exists (see vectorstore.ensure_index_exists, called
    from debate._ingest_topic) — not at server startup, so a Pinecone
    problem only breaks starting a debate, not the whole app.
    """
    try:
        return await run_debate(request.topic)
    except WikipediaNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


# Mounted LAST and at the root path "/" — Starlette matches routes in the
# order they're declared, so the two API routes above always get first
# chance to match. Anything that isn't /api/login or /api/debate falls
# through to here and is served as a static file from frontend/
# (index.html, style.css, app.js, ...). html=True means a request for "/"
# serves frontend/index.html automatically.
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
