# 🎓 EduGen AI Agent
### Educational Content Generator — Track A Production Project

> **AI Study Assistant + Quiz Generator** powered by LangChain, Streamlit, and multiple educational APIs.

---

## 🏗️ Architecture Overview

```
edugen/
├── agents/
│   └── edu_agent.py          # LangChain ReAct Agent (core orchestrator)
├── tools/
│   ├── pdf_tool.py           # PDF extraction (PyPDF2 + pdfplumber)
│   ├── youtube_tool.py       # YouTube transcript + metadata
│   ├── google_docs_tool.py   # Google Docs read/write
│   ├── tts_tool.py           # Text-to-Speech (Google Cloud + gTTS)
│   ├── nptel_swayam_tool.py  # Indian platform course search
│   ├── flashcard_tool.py     # Anki / Quizlet / JSON flashcards
│   └── quiz_tool.py          # AI quiz generation (MCQ, T/F, SA, FB)
├── ui/
│   └── app.py                # Streamlit Student Dashboard
├── utils/
│   └── progress_tracker.py   # SQLite progress & analytics
├── config/
│   └── settings.py           # Centralised config (dotenv)
├── tests/
│   └── test_tools.py         # Pytest unit tests
├── data/                     # Auto-created at runtime
│   ├── uploads/              # User-uploaded PDFs
│   ├── generated/
│   │   ├── audio/            # MP3 audio summaries
│   │   └── quizzes/          # JSON + Markdown quizzes
│   └── flashcards/           # JSON + CSV flashcard exports
├── requirements.txt
└── .env.example
```

---

## 🚀 Quick Start

### 1. Clone & install

```bash
git clone https://github.com/your-org/edugen.git
cd edugen
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your API keys (see API Setup below)
```

### 3. Run the app

```bash
streamlit run ui/app.py
```

Open [http://localhost:8501](http://localhost:8501) 🎉

---

## 🔑 API Setup

### Required (at least one LLM)

| Key | Where to get |
|-----|-------------|
| `OPENAI_API_KEY` | [platform.openai.com](https://platform.openai.com) |
| `GOOGLE_API_KEY` | [Google AI Studio](https://aistudio.google.com) (Gemini) |

### Optional (feature-specific)

| Feature | Key/File | Where to get |
|---------|----------|-------------|
| YouTube metadata | `YOUTUBE_API_KEY` | [Google Cloud Console](https://console.cloud.google.com) → YouTube Data API v3 |
| Google Docs | `GOOGLE_APPLICATION_CREDENTIALS` | Google Cloud → IAM → Service Account → JSON key |
| Google TTS (high quality) | Same service account | Enable Cloud Text-to-Speech API |
| Anki flashcards | Install [AnkiConnect plugin](https://ankiweb.net/shared/info/2055492159) | Anki app must be running |
| NPTEL/SWAYAM | No key needed | Web scraping — public content |
| gTTS (free TTS fallback) | No key needed | Installed via pip |

---

## 🧠 Agent Capabilities

### Content Ingestion
- **PDF** — Upload textbooks, notes, papers (up to 100 pages)
- **YouTube** — Paste any educational video URL for transcript extraction
- **Google Docs** — Read student notes or teacher materials directly
- **NPTEL/SWAYAM** — Search IIT courses on any topic

### Content Generation
- **Quizzes** — MCQ, True/False, Short Answer, Fill-in-the-Blank with explanations
- **Flashcards** — Export to Anki (AnkiConnect), Quizlet (CSV), or JSON
- **Audio Summaries** — MP3 using Google Cloud TTS or free gTTS
- **Google Docs Export** — Save generated content back to Drive

### Analytics
- Quiz attempt history with scores
- Study streak tracking
- Weak topic identification
- Content processing history

---

## 💬 Example Prompts

```
"Generate a 15-question mixed quiz from the uploaded PDF with explanations"
"Summarize this YouTube video: https://youtube.com/watch?v=abc123"
"Create Anki flashcards from the key concepts in this content"
"Search NPTEL for courses on Data Structures"
"Generate an audio summary of this Google Doc: [url]"
"What are my weakest topics? Give me a targeted practice quiz"
"Create 20 flashcards and export as Quizlet CSV"
```

---

## 🧪 Running Tests

```bash
pytest tests/ -v
# or with coverage:
pytest tests/ -v --cov=. --cov-report=html
```

---

## 🚢 Deployment (Streamlit Cloud)

1. Push to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect repo → set main file as `ui/app.py`
4. Add secrets in Streamlit Cloud dashboard (same keys as `.env`)

```toml
# .streamlit/secrets.toml (Streamlit Cloud format)
OPENAI_API_KEY = "sk-..."
YOUTUBE_API_KEY = "AIza..."
GOOGLE_API_KEY = "AIza..."
```

---

## 📦 Tech Stack

| Layer | Technology |
|-------|-----------|
| Agent Framework | LangChain ReAct Agent |
| LLM | OpenAI GPT-4o-mini / Google Gemini 1.5 Flash |
| UI | Streamlit |
| PDF Processing | PyPDF2 + pdfplumber |
| YouTube | youtube-transcript-api + YouTube Data API v3 |
| Google Docs | Google Docs API v1 (OAuth2 / Service Account) |
| TTS | Google Cloud TTS + gTTS (fallback) |
| Flashcards | AnkiConnect (local) + CSV (Quizlet) + JSON |
| Indian Platforms | BeautifulSoup4 scraping (NPTEL + SWAYAM) |
| Storage | SQLite (progress) + ChromaDB (vector) |
| Testing | pytest |

---

## 📄 License

MIT © 2024 EduGen Team
