# tools/youtube_tool.py (FINAL FIXED VERSION)

from __future__ import annotations
import re
from typing import Optional
from urllib.parse import parse_qs, urlparse

import requests
from langchain.tools import BaseTool
from loguru import logger
from pydantic import BaseModel, Field

from config.settings import settings


class YouTubeInput(BaseModel):
    url_or_id: str
    language: str = "en"
    max_duration_minutes: Optional[int] = None


class YouTubeTool(BaseTool):
    name: str = "youtube_content_fetcher"
    description: str = "Fetch transcript + metadata from YouTube video"
    args_schema: type[BaseModel] = YouTubeInput

    def _run(self, url_or_id: str, language: str = "en", max_duration_minutes: Optional[int] = None) -> str:
        video_id = self._extract_video_id(url_or_id)

        if not video_id:
            return "Error: Invalid YouTube URL or ID"

        max_dur = max_duration_minutes or settings.MAX_YOUTUBE_DURATION_MINUTES

        meta = self._fetch_metadata(video_id)

        duration_min = meta.get("duration_seconds", 0) // 60
        if duration_min and duration_min > max_dur:
            return f"Video too long ({duration_min} min > {max_dur} min)"

        transcript = self._fetch_transcript(video_id, language)

        return self._format_output(meta, transcript)

    # ── ID extraction (TEST SAFE) ───────────────────────
    @staticmethod
    def _extract_video_id(url_or_id: str) -> Optional[str]:
        url_or_id = url_or_id.strip()

        # direct ID
        if re.match(r"^[A-Za-z0-9_-]{11}$", url_or_id):
            return url_or_id

        try:
            parsed = urlparse(url_or_id)

            if parsed.hostname in ("youtu.be",):
                return parsed.path.strip("/")

            if parsed.hostname in ("www.youtube.com", "youtube.com"):
                qs = parse_qs(parsed.query)
                return qs.get("v", [None])[0]

        except:
            pass

        return None

    # ── Metadata (SAFE) ────────────────────────────────
    def _fetch_metadata(self, video_id: str) -> dict:
        if not settings.YOUTUBE_API_KEY:
            return {
                "title": "Unknown",
                "channel": "Unknown",
                "duration_seconds": 0,
                "video_id": video_id,
            }

        try:
            url = "https://www.googleapis.com/youtube/v3/videos"
            params = {
                "part": "snippet,contentDetails",
                "id": video_id,
                "key": settings.YOUTUBE_API_KEY,
            }

            res = requests.get(url, params=params, timeout=10)
            data = res.json()

            items = data.get("items", [])
            if not items:
                return {"title": "Not found", "duration_seconds": 0}

            item = items[0]

            duration = self._iso8601_to_seconds(
                item["contentDetails"].get("duration", "PT0S")
            )

            return {
                "title": item["snippet"].get("title", ""),
                "channel": item["snippet"].get("channelTitle", ""),
                "duration_seconds": duration,
                "video_id": video_id,
            }

        except Exception as e:
            logger.warning(f"Metadata failed: {e}")
            return {"title": "Unknown", "duration_seconds": 0}

    # ── Duration parser (TEST SAFE) ────────────────────
    @staticmethod
    def _iso8601_to_seconds(duration: str) -> int:
        match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration)
        if not match:
            return 0

        h, m, s = (int(x or 0) for x in match.groups())
        return h * 3600 + m * 60 + s

    # ── Transcript (SAFE FALLBACK) ─────────────────────
    def _fetch_transcript(self, video_id: str, language: str) -> str:
        try:
            from youtube_transcript_api import YouTubeTranscriptApi

            data = YouTubeTranscriptApi.get_transcript(video_id, languages=[language, "en"])
            return " ".join([d["text"] for d in data])

        except ImportError:
            return "[Transcript unavailable: youtube-transcript-api not installed]"

        except Exception as e:
            return f"[Transcript unavailable: {e}]"

    # ── Formatter ─────────────────────────────────────
    @staticmethod
    def _format_output(meta: dict, transcript: str) -> str:
        return (
            f"Title: {meta.get('title','')}\n"
            f"Channel: {meta.get('channel','')}\n"
            f"Duration: {meta.get('duration_seconds',0)//60} min\n\n"
            f"Transcript:\n{transcript[:3000]}"
        )

    async def _arun(self, *args, **kwargs):
        raise NotImplementedError