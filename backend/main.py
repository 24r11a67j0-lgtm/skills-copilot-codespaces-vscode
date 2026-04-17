"""
FastAPI application — Content Learning Guide Agent API.
"""

import logging
import uuid
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl

load_dotenv()

from fetcher import fetch_channel_videos, extract_channel_id
from embeddings import index_channel, channel_exists, search, get_all_video_metadata
from agent import get_topics, get_learning_path, chat, clear_session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Content Learning Guide Agent API starting up…")
    yield
    logger.info("Shutting down…")


app = FastAPI(
    title="Content Learning Guide Agent",
    description=(
        "An AI agent that analyses YouTube channels and guides users "
        "through the content as a structured learning path."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- In-memory job tracker (channel_id → status) ---
_index_jobs: dict[str, dict] = {}


# ─────────────────────────── Pydantic models ──────────────────────────────

class AnalyseRequest(BaseModel):
    channel_url: str
    force_reindex: bool = False


class ChatRequest(BaseModel):
    channel_id: str
    message: str
    session_id: str = ""
    channel_title: str = ""


class LearningPathRequest(BaseModel):
    channel_id: str
    topic: str


class SearchRequest(BaseModel):
    channel_id: str
    query: str
    n_results: int = 8


# ─────────────────────────────── Helpers ──────────────────────────────────

def _run_index_job(channel_url: str, channel_id: str, force: bool) -> None:
    """Background task: fetch + index a channel."""
    try:
        _index_jobs[channel_id] = {"status": "fetching", "progress": 0}
        data = fetch_channel_videos(channel_url)
        _index_jobs[channel_id] = {"status": "indexing", "progress": 50}
        index_channel(data)
        _index_jobs[channel_id] = {
            "status": "ready",
            "progress": 100,
            "channel_title": data["channel_title"],
            "video_count": len(data["videos"]),
        }
        logger.info("Channel indexed: %s (%d videos)", data["channel_title"], len(data["videos"]))
    except Exception as exc:  # noqa: BLE001
        logger.exception("Indexing failed for %s", channel_url)
        _index_jobs[channel_id] = {"status": "error", "error": str(exc)}


# ──────────────────────────────── Routes ──────────────────────────────────

@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/analyse")
def analyse_channel(req: AnalyseRequest, background_tasks: BackgroundTasks):
    """
    Start indexing a YouTube channel in the background.
    Poll /status/{channel_id} to check progress.
    """
    try:
        channel_id = extract_channel_id(str(req.channel_url))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not req.force_reindex and channel_exists(channel_id):
        job = _index_jobs.get(channel_id, {"status": "ready", "progress": 100})
        return {"channel_id": channel_id, "job": job}

    background_tasks.add_task(_run_index_job, str(req.channel_url), channel_id, req.force_reindex)
    _index_jobs[channel_id] = {"status": "queued", "progress": 0}
    return {"channel_id": channel_id, "job": _index_jobs[channel_id]}


@app.get("/status/{channel_id}")
def get_status(channel_id: str):
    """Return the current indexing job status for a channel."""
    job = _index_jobs.get(channel_id)
    if job is None:
        # Check if it was previously indexed (e.g. server restart)
        if channel_exists(channel_id):
            return {"channel_id": channel_id, "status": "ready", "progress": 100}
        raise HTTPException(status_code=404, detail="Channel not found. Call /analyse first.")
    return {"channel_id": channel_id, **job}


@app.get("/topics/{channel_id}")
def topics(channel_id: str):
    """Return topic clusters discovered in the channel."""
    if not channel_exists(channel_id):
        raise HTTPException(status_code=404, detail="Channel not indexed yet.")
    return get_topics(channel_id)


@app.post("/learning-path")
def learning_path(req: LearningPathRequest):
    """Return an ordered learning path for a topic within the channel."""
    if not channel_exists(req.channel_id):
        raise HTTPException(status_code=404, detail="Channel not indexed yet.")
    return get_learning_path(req.channel_id, req.topic)


@app.post("/search")
def search_videos(req: SearchRequest):
    """Semantic search across the channel's indexed content."""
    if not channel_exists(req.channel_id):
        raise HTTPException(status_code=404, detail="Channel not indexed yet.")
    results = search(req.channel_id, req.query, req.n_results)
    return {"results": results}


@app.post("/chat")
def chat_endpoint(req: ChatRequest):
    """
    Chat with the agent about a channel's content.
    Pass a consistent session_id to maintain conversation history.
    A new session_id is auto-generated if not provided.
    """
    if not channel_exists(req.channel_id):
        raise HTTPException(status_code=404, detail="Channel not indexed yet.")

    session_id = req.session_id or str(uuid.uuid4())
    reply = chat(
        channel_id=req.channel_id,
        message=req.message,
        session_id=session_id,
        channel_title=req.channel_title,
    )
    return {"session_id": session_id, "reply": reply}


@app.delete("/session/{session_id}")
def delete_session(session_id: str):
    """Clear conversation history for a session."""
    clear_session(session_id)
    return {"status": "cleared"}


@app.get("/videos/{channel_id}")
def list_videos(channel_id: str):
    """Return metadata for all indexed videos in a channel."""
    if not channel_exists(channel_id):
        raise HTTPException(status_code=404, detail="Channel not indexed yet.")
    videos = get_all_video_metadata(channel_id)
    return {"videos": videos}
