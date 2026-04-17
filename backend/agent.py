"""
RAG chat agent.

Uses LangChain's ConversationChain + ChromaDB retrieval to answer
questions about a YouTube channel's content and produce learning paths.
"""

import os
import json
import logging
from typing import Optional

from openai import OpenAI
from embeddings import search, get_all_video_metadata

logger = logging.getLogger(__name__)

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

_openai_client: Optional[OpenAI] = None

# In-memory session history store: session_id → list of messages
_sessions: dict[str, list[dict]] = {}


def _get_openai() -> OpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))
    return _openai_client


SYSTEM_PROMPT = """You are a helpful AI learning guide agent.
You have been given metadata and excerpts from a YouTube channel's videos.
Your job is to help users learn from the channel by:
1. Explaining what topics the channel covers.
2. Suggesting a structured, ordered learning path for any topic the user wants to learn.
3. Recommending the best videos to watch first, second, third, etc.
4. Answering questions about the channel's content.

When listing videos always format them like this (so the frontend can render them as cards):
[VIDEO: <title> | <url> | <thumbnail_url>]

Always be friendly, concise, and helpful. If you don't know something from the context provided, say so honestly.
"""


def _build_context(channel_id: str, query: str) -> str:
    """Retrieve the most relevant video chunks for the query."""
    results = search(channel_id, query, n_results=10)
    if not results:
        return "No relevant videos found."

    lines = []
    for r in results:
        lines.append(
            f"- Title: {r['video_title']}\n"
            f"  URL: {r['video_url']}\n"
            f"  Thumbnail: {r['thumbnail']}\n"
            f"  Relevance: {r['score']}\n"
            f"  Excerpt: {r['chunk_text'][:300]}"
        )
    return "\n\n".join(lines)


def get_topics(channel_id: str) -> dict:
    """
    Ask GPT-4o to cluster the channel's videos into topics/modules.

    Returns: { topics: [ { name, description, videos: [...] } ] }
    """
    videos = get_all_video_metadata(channel_id)
    if not videos:
        return {"topics": []}

    # Build a compact list for the prompt (avoid token overflow)
    video_list = "\n".join(
        f"- [{v['video_id']}] {v['video_title']} (views: {v['view_count']})"
        for v in videos[:200]
    )

    prompt = (
        "You are analysing a YouTube channel. "
        "Given the following list of video titles and IDs, identify the main topics "
        "or subject areas the channel covers. "
        "Group the videos under each topic. "
        "Return a JSON object with the shape:\n"
        '{"topics": [{"name": "...", "description": "...", "video_ids": ["id1", "id2", ...]}]}\n\n'
        f"Videos:\n{video_list}\n\n"
        "Return only valid JSON, no markdown fences."
    )

    client = _get_openai()
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content or "{}"
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.error("Failed to parse topics JSON: %s", raw)
        data = {"topics": []}

    # Enrich topics with full video metadata
    video_map = {v["video_id"]: v for v in videos}
    for topic in data.get("topics", []):
        topic["videos"] = [
            video_map[vid_id]
            for vid_id in topic.get("video_ids", [])
            if vid_id in video_map
        ]

    return data


def get_learning_path(channel_id: str, topic: str) -> dict:
    """
    Generate an ordered learning path for a given topic within the channel.

    Returns: { topic, steps: [ { order, video_title, video_url, thumbnail, reason } ] }
    """
    results = search(channel_id, topic, n_results=20)
    if not results:
        return {"topic": topic, "steps": []}

    video_list = "\n".join(
        f"- [{r['video_id']}] {r['video_title']} | {r['video_url']}"
        for r in results
    )

    prompt = (
        f"You are a learning guide for a YouTube channel. "
        f"The user wants to learn about: '{topic}'. "
        f"Given these relevant videos, create an ordered learning path from beginner to advanced. "
        f"Return JSON with shape:\n"
        '{"topic": "...", "steps": [{"order": 1, "video_id": "...", "video_title": "...", '
        '"video_url": "...", "reason": "why to watch this video at this step"}]}\n\n'
        f"Videos:\n{video_list}\n\n"
        "Return only valid JSON, no markdown fences."
    )

    client = _get_openai()
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content or "{}"
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.error("Failed to parse learning path JSON: %s", raw)
        data = {"topic": topic, "steps": []}

    # Enrich steps with thumbnails from search results
    result_map = {r["video_id"]: r for r in results}
    for step in data.get("steps", []):
        vid = result_map.get(step.get("video_id"), {})
        step.setdefault("thumbnail", vid.get("thumbnail", ""))
        step.setdefault("video_url", vid.get("video_url", ""))

    return data


def chat(
    channel_id: str,
    message: str,
    session_id: str,
    channel_title: str = "",
) -> str:
    """
    Conversational RAG chat with memory per session.

    Returns the assistant's reply as a string.
    """
    # Initialise session history
    if session_id not in _sessions:
        _sessions[session_id] = []

    history = _sessions[session_id]

    # Retrieve relevant context
    context = _build_context(channel_id, message)

    # Build system message with channel info + context
    system_message = (
        SYSTEM_PROMPT
        + f"\n\nChannel: {channel_title or channel_id}\n\n"
        + "Relevant video excerpts for this query:\n"
        + context
    )

    messages = [{"role": "system", "content": system_message}]
    messages.extend(history[-20:])  # keep last 20 turns to stay within token limits
    messages.append({"role": "user", "content": message})

    client = _get_openai()
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=messages,
        temperature=0.5,
    )
    reply = response.choices[0].message.content or ""

    # Persist turn in session history
    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": reply})

    return reply


def clear_session(session_id: str) -> None:
    """Clear conversation history for a session."""
    _sessions.pop(session_id, None)
