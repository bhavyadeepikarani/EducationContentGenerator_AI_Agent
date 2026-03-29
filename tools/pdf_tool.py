"""
tools/pdf_tool.py
Stable PDF extraction tool (Python 3.13 safe)
"""

from __future__ import annotations
import re
from pathlib import Path
from typing import Optional

import pdfplumber
import PyPDF2
from langchain.tools import BaseTool
from loguru import logger
from pydantic import BaseModel, Field

from config.settings import settings


# ── Input Schema ───────────────────────────────────────

class PDFInput(BaseModel):
    file_path: str
    max_pages: Optional[int] = None
    extract_tables: bool = False


# ── Tool ───────────────────────────────────────────────

class PDFProcessorTool(BaseTool):
    name = "pdf_processor"
    description = "Extract text from PDF files"

    args_schema = PDFInput

    def _run(self, file_path: str, max_pages=None, extract_tables=False) -> str:
        try:
            path = Path(file_path)

            if not path.exists():
                return f"Error: File not found at {file_path}"

            max_pages = max_pages or settings.MAX_PDF_PAGES

            try:
                return self._extract_pdfplumber(path, max_pages, extract_tables)
            except Exception as e:
                logger.warning(f"pdfplumber failed: {e}")
                return self._extract_pypdf2(path, max_pages)

        except Exception as e:
            logger.error(e)
            return f"Error processing PDF: {e}"

    # ── pdfplumber (primary) ───────────────────────────

    def _extract_pdfplumber(self, path: Path, max_pages, extract_tables):
        chunks = []

        with pdfplumber.open(path) as pdf:
            total_pages = min(len(pdf.pages), max_pages)

            for i in range(total_pages):
                try:
                    page = pdf.pages[i]
                    text = page.extract_text() or ""
                    text = self._clean_text(text)

                    chunks.append(f"[Page {i+1}]\n{text}")

                    if extract_tables:
                        tables = page.extract_tables() or []
                        for j, table in enumerate(tables):
                            rows = [
                                " | ".join(str(c) for c in row if c)
                                for row in table if row
                            ]
                            chunks.append(f"[Table {j+1} Page {i+1}]\n" + "\n".join(rows))

                except Exception as e:
                    logger.warning(f"Page {i+1} failed: {e}")
                    continue

        return "\n\n".join(chunks)

    # ── PyPDF2 fallback ────────────────────────────────

    def _extract_pypdf2(self, path: Path, max_pages):
        chunks = []

        with open(path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            total_pages = min(len(reader.pages), max_pages)

            for i in range(total_pages):
                try:
                    text = reader.pages[i].extract_text() or ""
                    chunks.append(f"[Page {i+1}]\n{self._clean_text(text)}")
                except Exception as e:
                    logger.warning(f"PyPDF2 page {i+1} failed: {e}")

        return "\n\n".join(chunks)

    # ── Cleaner ────────────────────────────────────────

    @staticmethod
    def _clean_text(text: str) -> str:
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]{2,}", " ", text)
        return text.strip()

    async def _arun(self, *args, **kwargs):
        raise NotImplementedError


# ── Helper functions ───────────────────────────────────

def extract_pdf_text(file_path: str | Path, max_pages: int = 50) -> str:
    tool = PDFProcessorTool()
    return tool._run(str(file_path), max_pages=max_pages)


def chunk_text(text: str, chunk_size: int = 1500, overlap: int = 150) -> list[str]:
    """
    Safe chunking (fixes infinite loop bug)
    """
    if overlap >= chunk_size:
        overlap = chunk_size // 2  # safety fix

    words = text.split()
    chunks = []

    start = 0
    while start < len(words):
        end = start + chunk_size
        chunks.append(" ".join(words[start:end]))
        start += chunk_size - overlap

    return chunks