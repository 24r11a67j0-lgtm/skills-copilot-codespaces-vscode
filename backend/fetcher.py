"""
YouTube channel fetcher.

Retrieves all video metadata (title, description, tags, view count,
upload date, duration) and transcripts for a given YouTube channel URL.
"""

import os
import re
import logging
from typing import Optional
from urllib.parse import urlparse, parse_qs

from googleapiclient.discovery import build
from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled

logger = logging.getLogger(__name__)

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")

# Maximum number of videos to fetch per channel (YouTube quota protection)
MAX_VIDEOS = 500


def _build_youtube_client():
    if not YOUTUBE_API_KEY:
        raise ValueError("YOUTUBE_API_KEY environment variable is not set.")
    return build("youtube", "v3", developerKey=YOUTUBE_API_KEY)


def extract_channel_id(url: str) -> str:
    """
    Resolve a YouTube channel/user/handle URL to a channel ID.

    Supported formats:
      - https://www.youtube.com/channel/UC...
      - https://www.youtube.com/@handle
      - https://www.youtube.com/user/username
      - https://www.youtube.com/c/customname
    """
    youtube = _build_youtube_client()
    parsed = urlparse(url)
    path_parts = [p for p in parsed.path.split("/") if p]

    if not path_parts:
        raise ValueError(f"Cannot parse channel URL: {url}")

    # Direct channel ID in URL
    if path_parts[0] == "channel" and len(path_parts) > 1:
        return path_parts[1]

    # @handle format
    if path_parts[0].startswith("@"):
        handle = path_parts[0]
        response = youtube.search().list(
            part="snippet",
            q=handle,
            type="channel",
            maxResults=1,
        ).execute()
        items = response.get("items", [])
        if not items:
            raise ValueError(f"Channel not found for handle: {handle}")
        return items[0]["snippet"]["channelId"]

    # /user/ or /c/ format
    if path_parts[0] in ("user", "c") and len(path_parts) > 1:
        username = path_parts[1]
        response = youtube.channels().list(
            part="id",
            forUsername=username,
        ).execute()
        items = response.get("items", [])
        if items:
            return items[0]["id"]
        # Fall back to search
        response = youtube.search().list(
            part="snippet",
            q=username,
            type="channel",
            maxResults=1,
        ).execute()
        items = response.get("items", [])
        if not items:
            raise ValueError(f"Channel not found for username: {username}")
        return items[0]["snippet"]["channelId"]

    raise ValueError(f"Unrecognised YouTube URL format: {url}")


def _get_uploads_playlist_id(youtube, channel_id: str) -> str:
    """Return the 'uploads' playlist ID for a channel."""
    response = youtube.channels().list(
        part="contentDetails",
        id=channel_id,
    ).execute()
    items = response.get("items", [])
    if not items:
        raise ValueError(f"Channel not found: {channel_id}")
    return items[0]["contentDetails"]["relatedPlaylists"]["uploads"]


def _fetch_all_video_ids(youtube, uploads_playlist_id: str) -> list[str]:
    """Page through a playlist and collect all video IDs (up to MAX_VIDEOS)."""
    video_ids: list[str] = []
    next_page_token: Optional[str] = None

    while len(video_ids) < MAX_VIDEOS:
        kwargs = dict(
            part="contentDetails",
            playlistId=uploads_playlist_id,
            maxResults=50,
        )
        if next_page_token:
            kwargs["pageToken"] = next_page_token

        response = youtube.playlistItems().list(**kwargs).execute()
        for item in response.get("items", []):
            video_ids.append(item["contentDetails"]["videoId"])

        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break

    return video_ids


def _fetch_video_details(youtube, video_ids: list[str]) -> list[dict]:
    """Fetch snippet + statistics for batches of up to 50 video IDs."""
    details = []
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i : i + 50]
        response = youtube.videos().list(
            part="snippet,statistics,contentDetails",
            id=",".join(batch),
        ).execute()
        details.extend(response.get("items", []))
    return details


def _fetch_transcript(video_id: str) -> str:
    """Return the full transcript text for a video, or an empty string."""
    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        return " ".join(entry["text"] for entry in transcript_list)
    except (NoTranscriptFound, TranscriptsDisabled):
        logger.debug("No transcript available for video %s", video_id)
        return ""
    except Exception as exc:  # noqa: BLE001
        logger.warning("Transcript fetch failed for %s: %s", video_id, exc)
        return ""


def fetch_channel_videos(channel_url: str) -> dict:
    """
    Main entry point.

    Returns a dict with:
      - channel_id: str
      - channel_title: str
      - videos: list of video dicts (id, title, description, tags,
                view_count, like_count, published_at, duration, transcript)
    """
    youtube = _build_youtube_client()

    channel_id = extract_channel_id(channel_url)
    logger.info("Resolved channel ID: %s", channel_id)

    # Channel title
    ch_response = youtube.channels().list(part="snippet", id=channel_id).execute()
    channel_title = ch_response["items"][0]["snippet"]["title"]

    uploads_playlist_id = _get_uploads_playlist_id(youtube, channel_id)
    video_ids = _fetch_all_video_ids(youtube, uploads_playlist_id)
    logger.info("Found %d video IDs", len(video_ids))

    raw_details = _fetch_video_details(youtube, video_ids)

    videos = []
    for item in raw_details:
        vid_id = item["id"]
        snippet = item.get("snippet", {})
        stats = item.get("statistics", {})
        video = {
            "id": vid_id,
            "url": f"https://www.youtube.com/watch?v={vid_id}",
            "title": snippet.get("title", ""),
            "description": snippet.get("description", ""),
            "tags": snippet.get("tags", []),
            "published_at": snippet.get("publishedAt", ""),
            "thumbnail": (
                snippet.get("thumbnails", {}).get("high", {}).get("url", "")
                or snippet.get("thumbnails", {}).get("default", {}).get("url", "")
            ),
            "view_count": int(stats.get("viewCount", 0)),
            "like_count": int(stats.get("likeCount", 0)),
            "duration": item.get("contentDetails", {}).get("duration", ""),
            "transcript": _fetch_transcript(vid_id),
        }
        videos.append(video)
        logger.debug("Fetched video: %s", video["title"])

    return {
        "channel_id": channel_id,
        "channel_title": channel_title,
        "channel_url": channel_url,
        "videos": videos,
    }
