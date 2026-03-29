"""
config/settings.py
Simplified settings for Gemini-only (Python 3.13 safe)
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings:
    # ── LLM (Gemini ONLY) ──────────────────────────────
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.3"))

    # ── Google APIs ────────────────────────────────────
    YOUTUBE_API_KEY: str = os.getenv("YOUTUBE_API_KEY", "")
    GOOGLE_DOCS_CLIENT_ID: str = os.getenv("GOOGLE_DOCS_CLIENT_ID", "")
    GOOGLE_DOCS_CLIENT_SECRET: str = os.getenv("GOOGLE_DOCS_CLIENT_SECRET", "")

    # ── Platforms ──────────────────────────────────────
    NPTEL_BASE_URL: str = os.getenv("NPTEL_BASE_URL", "https://nptel.ac.in")
    SWAYAM_BASE_URL: str = os.getenv("SWAYAM_BASE_URL", "https://swayam.gov.in")

    # ── Flashcards ─────────────────────────────────────
    ANKI_CONNECT_URL: str = os.getenv("ANKI_CONNECT_URL", "http://localhost:8765")
    ANKI_DEFAULT_DECK: str = os.getenv("ANKI_DEFAULT_DECK", "EduGen")
    QUIZLET_CLIENT_ID: str = os.getenv("QUIZLET_CLIENT_ID", "")
    QUIZLET_CLIENT_SECRET: str = os.getenv("QUIZLET_CLIENT_SECRET", "")

    # ── Storage ────────────────────────────────────────
    AUDIO_OUTPUT_DIR: Path = BASE_DIR / "data/generated/audio"
    QUIZ_OUTPUT_DIR: Path = BASE_DIR / "data/generated/quizzes"
    FLASHCARD_OUTPUT_DIR: Path = BASE_DIR / "data/flashcards"
    UPLOAD_DIR: Path = BASE_DIR / "data/uploads"
    DB_PATH: Path = BASE_DIR / "data/student_progress.db"

    # ── Limits ─────────────────────────────────────────
    MAX_PDF_PAGES: int = int(os.getenv("MAX_PDF_PAGES", "100"))
    MAX_YOUTUBE_DURATION_MINUTES: int = int(os.getenv("MAX_YOUTUBE_DURATION_MINUTES", "60"))

    # ── App ────────────────────────────────────────────
    APP_NAME: str = "EduGen AI Agent"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    def __init__(self):
        self._create_dirs()

    def _create_dirs(self):
        for d in [
            self.AUDIO_OUTPUT_DIR,
            self.QUIZ_OUTPUT_DIR,
            self.FLASHCARD_OUTPUT_DIR,
            self.UPLOAD_DIR,
            self.DB_PATH.parent,
        ]:
            Path(d).mkdir(parents=True, exist_ok=True)


settings = Settings()


# ── Logger ─────────────────────────────────────────────

logger.remove()

# File log
logger.add(
    BASE_DIR / "logs" / "app.log",
    rotation="10 MB",
    retention="7 days",
    level=settings.LOG_LEVEL,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
)

# Console log
logger.add(lambda msg: print(msg, end=""), level=settings.LOG_LEVEL)