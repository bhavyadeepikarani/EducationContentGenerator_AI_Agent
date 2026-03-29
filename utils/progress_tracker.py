from __future__ import annotations
import sqlite3
import json
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict

from loguru import logger
from config.settings import settings


# ── SCHEMA ─────────────────────────────────────────────

SCHEMA = """
CREATE TABLE IF NOT EXISTS quiz_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    quiz_topic TEXT NOT NULL,
    attempt_date TEXT NOT NULL,
    total_questions INTEGER NOT NULL,
    correct_answers INTEGER NOT NULL,
    score_percent REAL NOT NULL,
    time_taken_sec INTEGER,
    wrong_topics TEXT
);

CREATE TABLE IF NOT EXISTS flashcard_reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    topic TEXT NOT NULL,
    reviewed_at TEXT NOT NULL,
    cards_reviewed INTEGER NOT NULL,
    mastered INTEGER DEFAULT 0,
    needs_review INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS content_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    content_type TEXT NOT NULL,
    title TEXT NOT NULL,
    source_url TEXT,
    processed_at TEXT NOT NULL,
    summary_generated INTEGER DEFAULT 0,
    quiz_generated INTEGER DEFAULT 0,
    flashcards_created INTEGER DEFAULT 0,
    audio_created INTEGER DEFAULT 0
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_quiz_student ON quiz_attempts(student_id);
CREATE INDEX IF NOT EXISTS idx_quiz_date ON quiz_attempts(attempt_date);
"""


# ── DB CONTEXT ─────────────────────────────────────────

@contextmanager
def _db():
    db_path = Path(settings.DB_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")

    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"DB error: {e}")
        raise
    finally:
        conn.close()


# ── INIT ───────────────────────────────────────────────

def init_db():
    with _db() as conn:
        conn.executescript(SCHEMA)
    logger.info(f"Database initialized at {settings.DB_PATH}")


# ── WRITE FUNCTIONS ────────────────────────────────────

def log_quiz_attempt(
    topic: str,
    total: int,
    correct: int,
    time_sec: Optional[int] = None,
    wrong_topics: Optional[List[str]] = None,
    student_id: str = "default",
):
    if total <= 0:
        logger.warning("Total questions is 0 — skipping log")
        return

    score = round((correct / total) * 100, 2)

    with _db() as conn:
        conn.execute(
            """
            INSERT INTO quiz_attempts
            (student_id, quiz_topic, attempt_date, total_questions,
             correct_answers, score_percent, time_taken_sec, wrong_topics)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                student_id,
                topic,
                datetime.utcnow().isoformat(),
                total,
                correct,
                score,
                time_sec,
                json.dumps(wrong_topics or []),
            ),
        )

    logger.info(f"Quiz logged: {topic} → {score}%")


def log_flashcard_review(
    topic: str,
    cards_reviewed: int,
    mastered: int = 0,
    needs_review: int = 0,
    student_id: str = "default",
):
    with _db() as conn:
        conn.execute(
            """
            INSERT INTO flashcard_reviews
            (student_id, topic, reviewed_at, cards_reviewed, mastered, needs_review)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                student_id,
                topic,
                datetime.utcnow().isoformat(),
                cards_reviewed,
                mastered,
                needs_review,
            ),
        )


def log_content(
    content_type: str,
    title: str,
    source_url: str = "",
    summary: bool = False,
    quiz: bool = False,
    flashcards: bool = False,
    audio: bool = False,
    student_id: str = "default",
):
    with _db() as conn:
        conn.execute(
            """
            INSERT INTO content_history
            (student_id, content_type, title, source_url, processed_at,
             summary_generated, quiz_generated, flashcards_created, audio_created)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                student_id,
                content_type,
                title,
                source_url,
                datetime.utcnow().isoformat(),
                int(summary),
                int(quiz),
                int(flashcards),
                int(audio),
            ),
        )


# ── READ FUNCTIONS ─────────────────────────────────────

def get_quiz_stats(student_id: str = "default") -> Dict:
    with _db() as conn:
        row = conn.execute(
            """
            SELECT COUNT(*) as attempts,
                   AVG(score_percent) as avg_score,
                   MAX(score_percent) as best_score
            FROM quiz_attempts WHERE student_id=?
            """,
            (student_id,),
        ).fetchone()

        recent = conn.execute(
            """
            SELECT quiz_topic, score_percent, attempt_date
            FROM quiz_attempts
            WHERE student_id=?
            ORDER BY attempt_date DESC
            LIMIT 5
            """,
            (student_id,),
        ).fetchall()

    return {
        "total_attempts": row["attempts"] or 0,
        "avg_score": round(row["avg_score"] or 0, 2),
        "best_score": round(row["best_score"] or 0, 2),
        "recent_attempts": [dict(r) for r in recent],
    }


def get_study_streak(student_id: str = "default") -> int:
    with _db() as conn:
        rows = conn.execute(
            """
            SELECT DISTINCT date(attempt_date) as d
            FROM quiz_attempts
            WHERE student_id=?
            ORDER BY d DESC
            """,
            (student_id,),
        ).fetchall()

    if not rows:
        return 0

    streak = 0
    expected = date.today()

    for row in rows:
        d = date.fromisoformat(row["d"])

        if d == expected:
            streak += 1
            expected -= timedelta(days=1)
        elif d == expected - timedelta(days=1):
            # Allow 1-day gap tolerance (optional feature)
            expected -= timedelta(days=1)
        else:
            break

    return streak


def get_content_history(student_id: str = "default", limit: int = 20) -> List[Dict]:
    with _db() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM content_history
            WHERE student_id=?
            ORDER BY processed_at DESC
            LIMIT ?
            """,
            (student_id, limit),
        ).fetchall()

    return [dict(r) for r in rows]


def get_weak_topics(student_id: str = "default", limit: int = 5) -> List[str]:
    with _db() as conn:
        rows = conn.execute(
            """
            SELECT quiz_topic, AVG(score_percent) as avg_score
            FROM quiz_attempts
            WHERE student_id=?
            GROUP BY quiz_topic
            HAVING avg_score < 60
            ORDER BY avg_score ASC
            LIMIT ?
            """,
            (student_id, limit),
        ).fetchall()

    return [r["quiz_topic"] for r in rows]