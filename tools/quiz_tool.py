# tools/quiz_tool.py (FIXED)

from __future__ import annotations
import json
import re
from pathlib import Path
from typing import Literal, Optional

from langchain.tools import BaseTool
from loguru import logger
from pydantic import BaseModel, Field

from config.settings import settings


class QuizQuestion(BaseModel):
    question: str
    question_type: Literal["mcq", "true_false", "short_answer", "fill_blank"]
    options: Optional[list[str]] = None
    correct_answer: str = ""
    explanation: str = ""
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    topic_tag: str = ""


class Quiz(BaseModel):
    title: str
    topic: str
    questions: list[QuizQuestion]
    total_marks: int = 0

    def model_post_init(self, __context):
        self.total_marks = len(self.questions)


class QuizInput(BaseModel):
    content: str
    topic: str
    num_questions: int = 10
    difficulty: str = "mixed"
    question_types: str = "mcq,true_false,short_answer"
    llm_client: Optional[object] = Field(None, exclude=True)


class QuizGeneratorTool(BaseTool):
    name: str = "quiz_generator"
    description: str = "Generate quiz from text"
    args_schema: type[BaseModel] = QuizInput

    llm: Optional[object] = None

    def _run(self, content, topic, num_questions=10, difficulty="mixed", question_types="mcq,true_false,short_answer", llm_client=None):
        active_llm = llm_client or self.llm
        if not active_llm:
            return "Error: No LLM configured."

        q_types = [t.strip() for t in question_types.split(",")]

        prompt = self._build_prompt(content, topic, num_questions, difficulty, q_types)

        try:
            response = active_llm.invoke(prompt)
            raw = response.content if hasattr(response, "content") else str(response)

            questions = self._parse_llm_response(raw, topic)

            if not questions:
                return "Error: Could not parse questions."

            quiz = Quiz(title=f"{topic} Quiz", topic=topic, questions=questions[:num_questions])
            return self._save_and_format(quiz)

        except Exception as e:
            logger.error(e)
            return f"Error: {e}"

    @staticmethod
    def _build_prompt(content, topic, n, difficulty, q_types):
        return f"Generate {n} quiz questions in JSON array format from this content:\n{content[:4000]}"

    @staticmethod
    def _parse_llm_response(raw: str, topic: str):
        raw = raw.strip()

        # remove markdown fences
        raw = re.sub(r"```.*?```", lambda m: m.group(0).replace("```", ""), raw, flags=re.DOTALL)

        match = re.search(r"\[.*\]", raw, re.DOTALL)
        if not match:
            return []

        try:
            data = json.loads(match.group())
        except:
            return []

        questions = []
        for item in data:
            try:
                questions.append(
                    QuizQuestion(
                        question=item.get("question", ""),
                        question_type=item.get("type", "short_answer"),
                        options=item.get("options"),
                        correct_answer=str(item.get("correct", "")),
                        explanation=item.get("explanation", ""),
                        difficulty=item.get("difficulty", "medium"),
                        topic_tag=topic,
                    )
                )
            except:
                continue

        return questions

    def _save_and_format(self, quiz: Quiz):
        settings.QUIZ_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        path = settings.QUIZ_OUTPUT_DIR / f"{quiz.topic}.json"

        with open(path, "w", encoding="utf-8") as f:
            json.dump(quiz.model_dump(), f, indent=2)

        return str(path)

    async def _arun(self, *args, **kwargs):
        raise NotImplementedError