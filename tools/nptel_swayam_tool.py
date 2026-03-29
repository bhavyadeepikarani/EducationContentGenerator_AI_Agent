"""
tools/nptel_swayam_tool.py

Stable NPTEL + SWAYAM course search tool.
- Safe scraping (won’t crash)
- Timeout protected
- Fallback results if scraping fails
"""

from __future__ import annotations
from typing import Literal

import requests
from bs4 import BeautifulSoup
from langchain.tools import BaseTool
from loguru import logger
from pydantic import BaseModel, Field

from config.settings import settings


HEADERS = {
    "User-Agent": "Mozilla/5.0 (EduGenBot/1.0)"
}


# ── Input Schema ─────────────────────────────────────────

class NPTELInput(BaseModel):
    query: str = Field(..., description="Course topic")
    platform: Literal["nptel", "swayam", "both"] = "both"
    max_results: int = 5


# ── Tool ────────────────────────────────────────────────

class NPTELSwayamTool(BaseTool):
    name = "nptel_swayam_search"
    description = "Search courses from NPTEL and SWAYAM"

    args_schema = NPTELInput

    def _run(self, query: str, platform="both", max_results=5) -> str:
        results = []

        try:
            if platform in ("nptel", "both"):
                results.extend(self._search_nptel(query, max_results))

            if platform in ("swayam", "both"):
                results.extend(self._search_swayam(query, max_results))

        except Exception as e:
            logger.error(f"Search error: {e}")

        # Fallback if nothing found
        if not results:
            return self._fallback_results(query)

        return self._format_results(results[:max_results])

    # ── NPTEL Search ────────────────────────────────────

    def _search_nptel(self, query: str, max_results: int):
        try:
            url = f"{settings.NPTEL_BASE_URL}/course.html"
            resp = requests.get(
                url,
                params={"discipline": query},
                headers=HEADERS,
                timeout=5,
            )
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "html.parser")

            results = []
            cards = soup.select("a")

            for c in cards:
                text = c.get_text(strip=True)
                link = c.get("href", "")

                if text and query.lower() in text.lower():
                    results.append({
                        "platform": "NPTEL",
                        "title": text,
                        "url": link if link.startswith("http") else url + link
                    })

                if len(results) >= max_results:
                    break

            return results

        except Exception as e:
            logger.warning(f"NPTEL failed: {e}")
            return []

    # ── SWAYAM Search ───────────────────────────────────

    def _search_swayam(self, query: str, max_results: int):
        try:
            url = f"{settings.SWAYAM_BASE_URL}/explorer"
            resp = requests.get(
                url,
                params={"searchText": query},
                headers=HEADERS,
                timeout=5,
            )
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "html.parser")

            results = []
            cards = soup.select("a")

            for c in cards:
                text = c.get_text(strip=True)
                link = c.get("href", "")

                if text and query.lower() in text.lower():
                    results.append({
                        "platform": "SWAYAM",
                        "title": text,
                        "url": link if link.startswith("http") else url + link
                    })

                if len(results) >= max_results:
                    break

            return results

        except Exception as e:
            logger.warning(f"SWAYAM failed: {e}")
            return []

    # ── Fallback (VERY IMPORTANT) ───────────────────────

    def _fallback_results(self, query: str) -> str:
        return f"""
No live results found (network/site issue).

Suggested courses for '{query}':

1. NPTEL - Introduction to {query}
2. SWAYAM - Fundamentals of {query}
3. IIT Course - Advanced {query}
4. NPTEL - Applied {query}
5. SWAYAM - Beginner to Advanced {query}
"""

    # ── Formatter ──────────────────────────────────────

    def _format_results(self, results):
        lines = ["Found courses:\n"]

        for i, r in enumerate(results, 1):
            lines.append(f"{i}. [{r['platform']}] {r['title']}")
            if r.get("url"):
                lines.append(f"   URL: {r['url']}")
            lines.append("")

        return "\n".join(lines)

    async def _arun(self, *args, **kwargs):
        raise NotImplementedError