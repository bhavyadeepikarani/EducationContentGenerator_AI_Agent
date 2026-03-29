"""
tools/flashcard_tool.py
Flashcard generation and export.
"""

from __future__ import annotations
import json
import csv
from pathlib import Path
from typing import List

import requests
from langchain.tools import BaseTool
from loguru import logger
from pydantic import BaseModel, Field

from config.settings import settings


# ── Data models ──────────────────────────────────────────────

class Flashcard(BaseModel):
    front: str = Field(...)
    back: str = Field(...)
    tags: List[str] = Field(default_factory=list)
    deck: str = Field(default="Educational Agent")


class FlashcardInput(BaseModel):
    content: str
    topic: str
    export_format: str = "json"
    num_cards: int = 10


# ── Anki helper ──────────────────────────────────────────────

def _anki_request(action: str, **params) -> dict:
    payload = {"action": action, "version": 6, "params": params}
    try:
        resp = requests.post(settings.ANKI_CONNECT_URL, json=payload, timeout=5)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        raise ConnectionError(f"AnkiConnect error: {e}")


# ── Main Tool ───────────────────────────────────────────────

class FlashcardTool(BaseTool):
    name: str = "flashcard_generator"
    description: str = (
        "Generate flashcards from educational content and export them. "
        "Formats: 'anki', 'json', 'csv'."
    )
    args_schema: type[BaseModel] = FlashcardInput

    def _run(
        self,
        content: str,
        topic: str,
        export_format: str = "json",
        num_cards: int = 10,
    ) -> str:

        cards = self._parse_cards(content, topic, num_cards)

        if not cards:
            return "Error: Could not parse flashcards."

        fmt = export_format.lower()

        if fmt == "anki":
            return self._export_to_anki(cards, topic)
        elif fmt == "csv":
            return self._export_to_csv(cards, topic)
        else:
            return self._export_to_json(cards, topic)

    # ── Parsing ─────────────────────────────────────────────

    @staticmethod
    def _parse_cards(content: str, topic: str, num_cards: int) -> List[Flashcard]:
        content = content.strip()

        # ✅ Try JSON
        try:
            data = json.loads(content)
            if isinstance(data, list):
                return [
                    Flashcard(
                        front=item["front"],
                        back=item["back"],
                        tags=item.get("tags", [topic]),
                        deck=item.get("deck", settings.ANKI_DEFAULT_DECK),
                    )
                    for item in data
                    if isinstance(item, dict) and "front" in item and "back" in item
                ][:num_cards]
        except Exception:
            pass

        # ✅ Q/A pattern
        import re
        qa_pairs = re.findall(
            r"Q:\s*(.+?)\nA:\s*(.+?)(?=\nQ:|\Z)", content, re.DOTALL
        )
        if qa_pairs:
            return [
                Flashcard(front=q.strip(), back=a.strip(), tags=[topic])
                for q, a in qa_pairs[:num_cards]
            ]

        # ✅ "Term: Definition"
        lines = [l.strip() for l in content.split("\n") if l.strip()]
        cards: List[Flashcard] = []

        for line in lines:
            if ":" in line or " - " in line or " — " in line:
                sep = ":" if ":" in line else (" - " if " - " in line else " — ")
                parts = line.split(sep, 1)

                if len(parts) == 2:
                    cards.append(
                        Flashcard(
                            front=parts[0].strip(),
                            back=parts[1].strip(),
                            tags=[topic],
                        )
                    )

            if len(cards) >= num_cards:
                break

        return cards

    # ── Export ─────────────────────────────────────────────

    def _export_to_anki(self, cards: List[Flashcard], topic: str) -> str:
        deck = settings.ANKI_DEFAULT_DECK

        try:
            _anki_request("createDeck", deck=deck)

            notes = [
                {
                    "deckName": deck,
                    "modelName": "Basic",
                    "fields": {"Front": c.front, "Back": c.back},
                    "tags": c.tags or [topic],
                }
                for c in cards
            ]

            result = _anki_request("addNotes", notes=notes)
            added = sum(1 for r in result.get("result", []) if r is not None)

            return f"Added {added}/{len(cards)} flashcards to Anki."

        except Exception as e:
            logger.error(e)

            # ✅ FIXED fallback
            return self._export_to_json(cards, topic)

    def _export_to_json(self, cards: List[Flashcard], topic: str) -> str:
        path = settings.FLASHCARD_OUTPUT_DIR / f"{topic.replace(' ', '_')}.json"
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            json.dump([c.model_dump() for c in cards], f, indent=2)

        return str(path)

    def _export_to_csv(self, cards: List[Flashcard], topic: str) -> str:
        path = settings.FLASHCARD_OUTPUT_DIR / f"{topic.replace(' ', '_')}.csv"
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, delimiter="\t")
            for c in cards:
                writer.writerow([c.front, c.back])

        return str(path)

    async def _arun(self, *args, **kwargs):
        raise NotImplementedError