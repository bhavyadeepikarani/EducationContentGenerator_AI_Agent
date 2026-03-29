"""
tools/tts_tool.py
Text-to-Speech tool: Google Cloud TTS (primary) with gTTS fallback.
Generates audio summaries of educational content.
"""

from __future__ import annotations
import hashlib
import os
from pathlib import Path
from typing import Literal, Optional

from langchain.tools import BaseTool
from loguru import logger
from pydantic import BaseModel, Field

from config.settings import settings


class TTSInput(BaseModel):
    text: str = Field(..., description="Text to convert to speech (max ~5000 chars)")
    filename: Optional[str] = Field(None, description="Output filename without extension")
    language: str = Field("en-US", description="BCP-47 language code e.g. en-US, hi-IN")
    voice_gender: Literal["MALE", "FEMALE", "NEUTRAL"] = Field(
        "FEMALE", description="Voice gender for Google Cloud TTS"
    )
    speaking_rate: float = Field(1.0, description="Speaking rate: 0.25–4.0, default 1.0")


class TextToSpeechTool(BaseTool):
    """
    Converts educational summaries or explanations to audio.
    Uses Google Cloud TTS for high quality; falls back to gTTS (free).
    """

    name: str = "text_to_speech"
    description: str = (
        "Convert educational text (summaries, explanations, flashcard content) to an MP3 audio file. "
        "Input: text content and optional filename. "
        "Output: path to the generated MP3 file."
    )
    args_schema: type[BaseModel] = TTSInput

    def _run(
        self,
        text: str,
        filename: Optional[str] = None,
        language: str = "en-US",
        voice_gender: str = "FEMALE",
        speaking_rate: float = 1.0,
    ) -> str:
        text = text.strip()
        if not text:
            return "Error: No text provided for TTS"

        # Deterministic filename from content hash if not specified
        if not filename:
            h = hashlib.md5(text[:200].encode()).hexdigest()[:8]
            filename = f"audio_{h}"

        output_path = settings.AUDIO_OUTPUT_DIR / f"{filename}.mp3"
        settings.AUDIO_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        # Try Google Cloud TTS first
        if os.path.exists(settings.GOOGLE_APPLICATION_CREDENTIALS):
            try:
                return self._google_cloud_tts(text, output_path, language, voice_gender, speaking_rate)
            except Exception as e:
                logger.warning(f"Google Cloud TTS failed ({e}), falling back to gTTS")

        # Fallback: gTTS
        return self._gtts_fallback(text, output_path, language)

    # ── Google Cloud TTS ─────────────────────────────────────────────────────

    @staticmethod
    def _google_cloud_tts(
        text: str,
        output_path: Path,
        language: str,
        voice_gender: str,
        speaking_rate: float,
    ) -> str:
        from google.cloud import texttospeech

        client = texttospeech.TextToSpeechClient()

        # Chunk long texts (Google TTS limit: 5000 bytes)
        chunks = TextToSpeechTool._chunk_for_tts(text, max_bytes=4800)
        audio_chunks: list[bytes] = []

        for chunk in chunks:
            synthesis_input = texttospeech.SynthesisInput(text=chunk)
            voice = texttospeech.VoiceSelectionParams(
                language_code=language,
                ssml_gender=getattr(texttospeech.SsmlVoiceGender, voice_gender),
            )
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                speaking_rate=speaking_rate,
            )
            response = client.synthesize_speech(
                input=synthesis_input, voice=voice, audio_config=audio_config
            )
            audio_chunks.append(response.audio_content)

        with open(output_path, "wb") as f:
            for chunk in audio_chunks:
                f.write(chunk)

        logger.success(f"Google Cloud TTS saved: {output_path}")
        return str(output_path)

    # ── gTTS fallback ────────────────────────────────────────────────────────

    @staticmethod
    def _gtts_fallback(text: str, output_path: Path, language: str) -> str:
        from gtts import gTTS

        lang_code = language.split("-")[0]  # "en-US" → "en"
        tts = gTTS(text=text, lang=lang_code, slow=False)
        tts.save(str(output_path))
        logger.success(f"gTTS fallback saved: {output_path}")
        return str(output_path)

    # ── Helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _chunk_for_tts(text: str, max_bytes: int = 4800) -> list[str]:
        """Split text at sentence boundaries to stay within TTS byte limits."""
        import re

        sentences = re.split(r"(?<=[.!?])\s+", text)
        chunks: list[str] = []
        current = ""
        for sent in sentences:
            candidate = (current + " " + sent).strip()
            if len(candidate.encode("utf-8")) > max_bytes:
                if current:
                    chunks.append(current)
                current = sent
            else:
                current = candidate
        if current:
            chunks.append(current)
        return chunks or [text[:max_bytes]]

    async def _arun(self, *args, **kwargs):
        raise NotImplementedError
