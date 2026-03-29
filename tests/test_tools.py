"""
tests/test_tools.py
Unit tests for EduGen tools (Gemini-safe version)
Run: pytest tests/ -v
"""

import json
import tempfile
from pathlib import Path

import pytest


# ── PDF Tool ─────────────────────────────────────────

class TestPDFTool:
    def test_extract_nonexistent_file(self):
        from tools.pdf_tool import PDFProcessorTool
        tool = PDFProcessorTool()
        result = tool._run("/nonexistent/file.pdf")
        assert "Error" in result

    def test_chunk_text(self):
        from tools.pdf_tool import chunk_text
        text = " ".join([f"word{i}" for i in range(1000)])
        chunks = chunk_text(text, chunk_size=100, overlap=10)
        assert len(chunks) > 1
        assert all(len(c.split()) <= 110 for c in chunks)

    def test_clean_text(self):
        from tools.pdf_tool import PDFProcessorTool
        dirty = "Hello  World\n\n\n\nTest   text"
        clean = PDFProcessorTool._clean_text(dirty)
        assert "\n\n\n" not in clean
        assert "  " not in clean


# ── YouTube Tool ─────────────────────────────────────

class TestYouTubeTool:
    def test_extract_video_id_full_url(self):
        from tools.youtube_tool import YouTubeTool
        tool = YouTubeTool()
        vid_id = tool._extract_video_id(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        )
        assert vid_id == "dQw4w9WgXcQ"

    def test_extract_video_id_short(self):
        from tools.youtube_tool import YouTubeTool
        tool = YouTubeTool()
        vid_id = tool._extract_video_id(
            "https://youtu.be/dQw4w9WgXcQ"
        )
        assert vid_id == "dQw4w9WgXcQ"

    def test_extract_video_id_bare(self):
        from tools.youtube_tool import YouTubeTool
        tool = YouTubeTool()
        vid_id = tool._extract_video_id("dQw4w9WgXcQ")
        assert vid_id == "dQw4w9WgXcQ"

    def test_iso8601_to_seconds(self):
        from tools.youtube_tool import YouTubeTool
        assert YouTubeTool._iso8601_to_seconds("PT1H30M45S") == 5445
        assert YouTubeTool._iso8601_to_seconds("PT10M") == 600
        assert YouTubeTool._iso8601_to_seconds("PT45S") == 45


# ── Quiz Tool ───────────────────────────────────────

class TestQuizTool:
    SAMPLE_QUESTIONS = json.dumps([
        {
            "type": "mcq",
            "question": "What is 2+2?",
            "options": ["A. 3", "B. 4", "C. 5", "D. 6"],
            "correct": "B",
            "explanation": "Basic arithmetic",
            "difficulty": "easy",
        },
        {
            "type": "true_false",
            "question": "The sky is green.",
            "correct": "False",
            "explanation": "The sky is blue.",
            "difficulty": "easy",
        },
    ])

    def test_parse_json_questions(self):
        from tools.quiz_tool import QuizGeneratorTool
        tool = QuizGeneratorTool()
        questions = tool._parse_llm_response(self.SAMPLE_QUESTIONS, "Math")
        assert len(questions) == 2
        assert questions[0].question_type == "mcq"
        assert questions[1].question_type == "true_false"

    def test_parse_fenced_json(self):
        from tools.quiz_tool import QuizGeneratorTool
        tool = QuizGeneratorTool()
        fenced = f"```json\n{self.SAMPLE_QUESTIONS}\n```"
        questions = tool._parse_llm_response(fenced, "Test")
        assert len(questions) == 2

    def test_build_prompt_contains_topic(self):
        from tools.quiz_tool import QuizGeneratorTool
        prompt = QuizGeneratorTool._build_prompt(
            "Some content", "Python", 5, "medium", ["mcq"]
        )
        assert "Python" in prompt
        assert "mcq" in prompt


# ── Flashcard Tool ──────────────────────────────────

class TestFlashcardTool:
    def test_parse_json_cards(self):
        from tools.flashcard_tool import FlashcardTool
        tool = FlashcardTool()
        data = json.dumps([
            {"front": "Q1", "back": "A1"},
            {"front": "Q2", "back": "A2"},
        ])
        cards = tool._parse_cards(data, "Test", 10)
        assert len(cards) == 2
        assert cards[0].front == "Q1"

    def test_parse_qa_pattern(self):
        from tools.flashcard_tool import FlashcardTool
        tool = FlashcardTool()
        text = (
            "Q: What is AI?\nA: Artificial Intelligence\n"
            "Q: What is ML?\nA: Machine Learning\n"
        )
        cards = tool._parse_cards(text, "Tech", 10)
        assert len(cards) == 2

    def test_export_json(self):
        from tools.flashcard_tool import FlashcardTool, Flashcard
        tool = FlashcardTool()

        cards = [Flashcard(front="Q1", back="A1", tags=["test"])]

        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            output_dir.mkdir(exist_ok=True)

            path = tool._export_to_json(cards, "test_topic", output_dir=output_dir)

            assert Path(path).exists()


# ── Progress Tracker ────────────────────────────────

class TestProgressTracker:
    def test_init_and_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.db"

            from utils.progress_tracker import (
                init_db,
                log_quiz_attempt,
                get_quiz_stats,
            )

            init_db(db_path=db_path)
            log_quiz_attempt(
                "Algebra", 10, 8,
                student_id="test_student",
                db_path=db_path
            )

            stats = get_quiz_stats("test_student", db_path=db_path)

            assert stats["total_attempts"] == 1
            assert stats["avg_score"] == 80.0

    def test_streak_calculation(self):
        from utils.progress_tracker import get_study_streak
        streak = get_study_streak("no_such_user")
        assert streak == 0