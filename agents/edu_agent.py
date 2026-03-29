"""
agents/edu_agent.py
Gemini-based Educational AI Agent (Python 3.13 safe)
"""

from __future__ import annotations
from typing import Optional

from langchain.agents import AgentExecutor, create_react_agent
from langchain.memory import ConversationBufferWindowMemory
from langchain_core.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from loguru import logger

from config.settings import settings
from tools.pdf_tool import PDFProcessorTool
from tools.youtube_tool import YouTubeTool
from tools.google_docs_tool import GoogleDocsReaderTool, GoogleDocsWriterTool
from tools.tts_tool import TextToSpeechTool
from tools.nptel_swayam_tool import NPTELSwayamTool
from tools.flashcard_tool import FlashcardTool
from tools.quiz_tool import QuizGeneratorTool


# ── System prompt ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are EduGen — an expert AI Study Assistant and Quiz Generator.

You help students learn by:
1. Processing educational content (PDFs, YouTube videos, Google Docs, NPTEL/SWAYAM courses)
2. Generating quizzes with MCQ, True/False, Short Answer, and Fill-in-the-Blank questions
3. Creating flashcards for spaced repetition (Anki / Quizlet compatible)
4. Producing audio summaries of educational material
5. Tracking student progress and identifying knowledge gaps

AVAILABLE TOOLS:
{tools}

TOOL NAMES: {tool_names}

GUIDELINES:
- Always confirm what content source you're working with before generating content
- When generating quizzes, ask about difficulty and number of questions if not specified
- Generate flashcards after producing a quiz for the same content (good practice)
- Offer to create an audio summary for accessibility
- Be encouraging, clear, and pedagogically sound in all explanations
- If content is too long, focus on the most important concepts

SCRATCHPAD FORMAT (strict ReAct):
Question: the input question you must answer
Thought: your reasoning about what to do next
Action: the tool to use (must be one of [{tool_names}])
Action Input: the input to the tool
Observation: the result of the tool
... (repeat Thought/Action/Observation as needed)
Thought: I now know the final answer
Final Answer: your complete response to the user

{agent_scratchpad}"""

HUMAN_PROMPT = "{input}"


# ── LLM (Gemini ONLY) ─────────────────────────────────────────────────────────

def build_llm():
    """Construct Gemini LLM only."""
    if not settings.GOOGLE_API_KEY:
        raise ValueError("GOOGLE_API_KEY not set in .env")

    logger.info("Using Gemini (Google) as LLM backend")

    return ChatGoogleGenerativeAI(
        model="gemini-1.5-flash",
        google_api_key=settings.GOOGLE_API_KEY,
        temperature=settings.LLM_TEMPERATURE,
    )


# ── Tools ────────────────────────────────────────────────────────────────────

def build_tools(llm) -> list:
    quiz_tool = QuizGeneratorTool()
    quiz_tool.llm = llm  # inject LLM

    return [
        PDFProcessorTool(),
        YouTubeTool(),
        GoogleDocsReaderTool(),
        GoogleDocsWriterTool(),
        TextToSpeechTool(),
        NPTELSwayamTool(),
        FlashcardTool(),
        quiz_tool,
    ]


# ── Agent builder ────────────────────────────────────────────────────────────

def build_agent(session_id: str = "default") -> AgentExecutor:
    llm = build_llm()
    tools = build_tools(llm)

    prompt = PromptTemplate.from_template(SYSTEM_PROMPT + "\n\nHuman: " + HUMAN_PROMPT)

    memory = ConversationBufferWindowMemory(
        memory_key="chat_history",
        k=10,
        return_messages=True,
        output_key="output",
    )

    agent = create_react_agent(llm=llm, tools=tools, prompt=prompt)

    executor = AgentExecutor(
        agent=agent,
        tools=tools,
        memory=memory,
        verbose=True,
        max_iterations=8,
        max_execution_time=120,
        handle_parsing_errors=True,
        return_intermediate_steps=True,
    )

    logger.success(f"EduGen agent ready | session={session_id}")
    return executor


# ── Wrapper ──────────────────────────────────────────────────────────────────

class EduGenAgent:

    def __init__(self, session_id: str = "default"):
        self.session_id = session_id
        self._executor: Optional[AgentExecutor] = None

    @property
    def executor(self) -> AgentExecutor:
        if self._executor is None:
            self._executor = build_agent(self.session_id)
        return self._executor

    def run(self, user_input: str) -> dict:
        try:
            result = self.executor.invoke({"input": user_input})
            return {
                "output": result.get("output", ""),
                "steps": result.get("intermediate_steps", []),
                "error": None,
            }
        except Exception as e:
            logger.error(f"Agent error: {e}")
            return {
                "output": f"I encountered an error: {e}",
                "steps": [],
                "error": str(e),
            }

    def reset_memory(self):
        if self._executor:
            self._executor.memory.clear()