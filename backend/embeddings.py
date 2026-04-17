"""
Embedding pipeline.

Chunks video transcripts/descriptions, generates embeddings via OpenAI,
and stores them in a local ChromaDB collection keyed by channel_id.
"""

import os
import json
import logging
from typing import Optional

import chromadb
from chromadb.config import Settings
from openai import OpenAI

logger = logging.getLogger(__name__)

CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
CHUNK_SIZE = 400   # tokens (approximate, based on words)
CHUNK_OVERLAP = 50

_chroma_client: Optional[chromadb.PersistentClient] = None
_openai_client: Optional[OpenAI] = None


def _get_chroma() -> chromadb.PersistentClient:
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(
            path=CHROMA_PERSIST_DIR,
            settings=Settings(anonymized_telemetry=False),
        )
    return _chroma_client


def _get_openai() -> OpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))
    return _openai_client


def _collection_name(channel_id: str) -> str:
    # ChromaDB collection names must be 3-63 chars, alphanumeric + hyphens
    safe = "".join(c if c.isalnum() or c == "-" else "-" for c in channel_id)
    return safe[:63] or "channel"


def _chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping word-based chunks."""
    words = text.split()
    if not words:
        return []
    chunks = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunks.append(" ".join(words[start:end]))
        start += chunk_size - overlap
    return chunks


def _embed_texts(texts: list[str]) -> list[list[float]]:
    """Batch-embed a list of texts using OpenAI embeddings."""
    if not texts:
        return []
    client = _get_openai()
    # OpenAI allows up to 2048 inputs per request; batch for safety
    all_embeddings: list[list[float]] = []
    batch_size = 100
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        response = client.embeddings.create(model=EMBEDDING_MODEL, input=batch)
        all_embeddings.extend([item.embedding for item in response.data])
    return all_embeddings


def index_channel(channel_data: dict) -> None:
    """
    Index all videos from a channel into ChromaDB.

    Each chunk is stored with metadata:
      video_id, video_title, video_url, thumbnail, chunk_index, published_at
    """
    channel_id = channel_data["channel_id"]
    videos = channel_data["videos"]
    collection_name = _collection_name(channel_id)

    chroma = _get_chroma()

    # Delete existing collection if re-indexing
    try:
        chroma.delete_collection(collection_name)
    except Exception:  # noqa: BLE001
        pass

    collection = chroma.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )

    # Store channel-level metadata in a separate collection
    meta_collection = chroma.get_or_create_collection(name="channel_meta")
    meta_collection.upsert(
        ids=[channel_id],
        documents=[json.dumps({
            "channel_id": channel_data["channel_id"],
            "channel_title": channel_data["channel_title"],
            "channel_url": channel_data["channel_url"],
            "video_count": len(videos),
        })],
        metadatas=[{"channel_id": channel_id}],
    )

    all_chunks: list[str] = []
    all_ids: list[str] = []
    all_metadatas: list[dict] = []

    for video in videos:
        # Use transcript if available, otherwise fall back to description
        source_text = video.get("transcript") or video.get("description", "")
        # Prepend title so each chunk carries context
        source_text = f"{video['title']}. {source_text}"
        chunks = _chunk_text(source_text)
        if not chunks:
            continue
        for idx, chunk in enumerate(chunks):
            chunk_id = f"{video['id']}__chunk{idx}"
            all_ids.append(chunk_id)
            all_chunks.append(chunk)
            all_metadatas.append({
                "video_id": video["id"],
                "video_title": video["title"],
                "video_url": video["url"],
                "thumbnail": video.get("thumbnail", ""),
                "published_at": video.get("published_at", ""),
                "view_count": video.get("view_count", 0),
                "chunk_index": idx,
                "tags": json.dumps(video.get("tags", [])),
            })

    if not all_chunks:
        logger.warning("No chunks to index for channel %s", channel_id)
        return

    embeddings = _embed_texts(all_chunks)

    # Upsert in batches of 500 (ChromaDB limit)
    batch = 500
    for i in range(0, len(all_chunks), batch):
        collection.upsert(
            ids=all_ids[i : i + batch],
            documents=all_chunks[i : i + batch],
            embeddings=embeddings[i : i + batch],
            metadatas=all_metadatas[i : i + batch],
        )

    logger.info("Indexed %d chunks for channel %s", len(all_chunks), channel_id)


def search(channel_id: str, query: str, n_results: int = 8) -> list[dict]:
    """
    Semantic search over the indexed channel.

    Returns a list of result dicts with keys:
      chunk_text, video_id, video_title, video_url, thumbnail, score
    """
    collection_name = _collection_name(channel_id)
    chroma = _get_chroma()

    try:
        collection = chroma.get_collection(collection_name)
    except Exception:  # noqa: BLE001
        return []

    query_embedding = _embed_texts([query])[0]
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        include=["documents", "metadatas", "distances"],
    )

    output = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        output.append({
            "chunk_text": doc,
            "video_id": meta.get("video_id"),
            "video_title": meta.get("video_title"),
            "video_url": meta.get("video_url"),
            "thumbnail": meta.get("thumbnail"),
            "published_at": meta.get("published_at"),
            "view_count": meta.get("view_count", 0),
            "score": round(1 - dist, 4),  # cosine similarity
        })

    # Deduplicate by video, keeping highest score
    seen: dict[str, dict] = {}
    for item in output:
        vid_id = item["video_id"]
        if vid_id not in seen or item["score"] > seen[vid_id]["score"]:
            seen[vid_id] = item
    return list(seen.values())


def get_all_video_metadata(channel_id: str) -> list[dict]:
    """Return metadata for every unique video in the collection (for topic analysis)."""
    collection_name = _collection_name(channel_id)
    chroma = _get_chroma()

    try:
        collection = chroma.get_collection(collection_name)
    except Exception:  # noqa: BLE001
        return []

    # Fetch only chunk_index==0 to get one entry per video
    results = collection.get(
        where={"chunk_index": 0},
        include=["metadatas"],
    )

    seen: dict[str, dict] = {}
    for meta in results.get("metadatas", []):
        vid_id = meta.get("video_id")
        if vid_id and vid_id not in seen:
            seen[vid_id] = {
                "video_id": vid_id,
                "video_title": meta.get("video_title"),
                "video_url": meta.get("video_url"),
                "thumbnail": meta.get("thumbnail"),
                "published_at": meta.get("published_at"),
                "view_count": meta.get("view_count", 0),
            }
    return list(seen.values())


def channel_exists(channel_id: str) -> bool:
    """Check if a channel has already been indexed."""
    collection_name = _collection_name(channel_id)
    chroma = _get_chroma()
    try:
        col = chroma.get_collection(collection_name)
        return col.count() > 0
    except Exception:  # noqa: BLE001
        return False
