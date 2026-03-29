from __future__ import annotations
import sys
from pathlib import Path
import streamlit as st

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.edu_agent import EduGenAgent
from utils.progress_tracker import (
    init_db, log_quiz_attempt, log_content,
    get_quiz_stats, get_study_streak, get_content_history, get_weak_topics,
)
from config.settings import settings


# ── PAGE CONFIG ─────────────────────────────────────────

st.set_page_config(
    page_title="EduGen AI Agent",
    page_icon="🎓",
    layout="wide",
)

# ── SESSION INIT ───────────────────────────────────────

def init_session():
    if "agent" not in st.session_state:
        st.session_state.agent = EduGenAgent(session_id="streamlit_session")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "db_ready" not in st.session_state:
        init_db()
        st.session_state.db_ready = True


init_session()


# ── SIDEBAR ────────────────────────────────────────────

with st.sidebar:
    st.title("🎓 EduGen AI")

    page = st.radio(
        "Navigation",
        ["💬 Study Chat", "📊 Dashboard", "📁 History", "⚙️ Settings"],
        label_visibility="collapsed",
    )

    st.divider()

    if st.button("🔄 New Session"):
        st.session_state.agent.reset_memory()
        st.session_state.messages = []
        st.rerun()

    st.divider()

    # Streak
    streak = get_study_streak()
    st.metric("🔥 Study Streak", f"{streak} days")

    # Weak topics
    weak = get_weak_topics()
    if weak:
        st.write("📌 Weak Topics")
        for t in weak:
            st.caption(f"• {t}")


# ── PAGE 1: CHAT ───────────────────────────────────────

if page == "💬 Study Chat":
    st.title("💬 Study Chat")

    # Upload section
    with st.expander("📎 Upload Content"):
        uploaded_pdf = st.file_uploader("Upload PDF", type=["pdf"])

        if uploaded_pdf:
            save_path = settings.UPLOAD_DIR / uploaded_pdf.name
            settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

            with open(save_path, "wb") as f:
                f.write(uploaded_pdf.read())

            st.success(f"Saved: {uploaded_pdf.name}")
            st.session_state.last_upload_path = str(save_path)

        yt_url = st.text_input("YouTube URL")
        if yt_url:
            st.session_state.last_yt_url = yt_url

        gdoc_url = st.text_input("Google Doc URL")
        if gdoc_url:
            st.session_state.last_gdoc_url = gdoc_url

    # Suggestions
    st.write("### 💡 Suggestions")
    suggestions = [
        "Generate a quiz from uploaded PDF",
        "Create flashcards from YouTube video",
        "Search NPTEL for Machine Learning",
        "Summarize document and create audio",
    ]

    cols = st.columns(2)
    for i, sug in enumerate(suggestions):
        if cols[i % 2].button(sug):
            st.session_state.pending_input = sug

    st.divider()

    # Display chat
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.chat_message("user").write(msg["content"])
        else:
            with st.chat_message("assistant"):
                st.write(msg["content"])

                if msg.get("steps"):
                    with st.expander("🔧 Steps"):
                        for action, obs in msg["steps"]:
                            st.code(f"{action.tool} → {action.tool_input}")
                            st.caption(str(obs)[:200])

                if msg.get("audio_path"):
                    st.audio(msg["audio_path"])

    # Input
    pending = st.session_state.pop("pending_input", None)
    user_input = st.chat_input("Ask something...") or pending

    if user_input:
        st.session_state.messages.append({
            "role": "user",
            "content": user_input
        })

        with st.spinner("Thinking..."):
            result = st.session_state.agent.run(user_input)

        output = result.get("output", "")
        steps = result.get("steps", [])

        st.session_state.messages.append({
            "role": "assistant",
            "content": output,
            "steps": steps,
        })

        # Logging
        text = user_input.lower()
        if "pdf" in text:
            log_content("pdf", "Uploaded PDF", quiz="quiz" in output.lower())
        elif "youtube" in text:
            log_content("youtube", "YouTube Video")

        st.rerun()


# ── PAGE 2: DASHBOARD ──────────────────────────────────

elif page == "📊 Dashboard":
    st.title("📊 Dashboard")

    stats = get_quiz_stats()

    col1, col2, col3 = st.columns(3)
    col1.metric("Quizzes", stats.get("total_attempts", 0))
    col2.metric("Avg Score", f"{stats.get('avg_score', 0)}%")
    col3.metric("Best Score", f"{stats.get('best_score', 0)}%")

    st.divider()

    st.subheader("Recent Attempts")

    for attempt in stats.get("recent_attempts", []):
        st.write(
            f"{attempt['quiz_topic']} → {attempt['score_percent']}% "
            f"({attempt['attempt_date'][:10]})"
        )


# ── PAGE 3: HISTORY ────────────────────────────────────

elif page == "📁 History":
    st.title("📁 Content History")

    history = get_content_history(limit=50)

    if not history:
        st.info("No history yet.")
    else:
        for item in history:
            st.write(
                f"📄 {item['title']} "
                f"({item['processed_at'][:16]})"
            )


# ── PAGE 4: SETTINGS ───────────────────────────────────

elif page == "⚙️ Settings":
    st.title("⚙️ Settings")

    st.subheader("API Status")

    st.text("OpenAI Key: " + ("✅" if settings.OPENAI_API_KEY else "❌"))
    st.text("Google Key: " + ("✅" if settings.GOOGLE_API_KEY else "❌"))
    st.text("YouTube Key: " + ("✅" if settings.YOUTUBE_API_KEY else "❌"))

    st.divider()

    if st.button("Clear Chat"):
        st.session_state.messages = []
        st.session_state.agent.reset_memory()
        st.success("Cleared")