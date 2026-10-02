import json
import os
import re
import time
import uuid
from collections import defaultdict
from datetime import datetime
from html import escape

import streamlit as st
import streamlit.components.v1 as components

from agents import (
    CoachAgent,
    EvidenceAgent,
    GroqGateway,
    InterviewerAgent,
    ResearchAgent,
    StrategyAgent,
)
from db import init_db, save_session
from report import build_markdown_report, build_pdf_report
from utils import extract_uploaded_text, safe_clamp

st.set_page_config(
    page_title="Intervia — Interview Intelligence",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

CATEGORIES = [
    "Behavioral & Situational 🎭",
    "Technical & Role-Specific 💻",
    "HR & Screening Basics 🤝",
    "Leadership & Management 👔",
    "Case & Analytical Interviews 📊",
    "Competency & Skill-Based 🧠",
    "Reverse Interviewing — Questions for the Employer 🔍",
]
DURATIONS = {"30 Minutes": 30, "60 Minutes": 60, "120 Minutes": 120, "180 Minutes": 180}
TARGET_QUESTIONS = {30: 8, 60: 15, 120: 28, 180: 40}

st.markdown(
    """
    <style>
    :root {
        --bg:#090c16; --bg-2:#0d111d; --panel:#131824; --panel-2:#171d2b;
        --panel-3:#1c2333; --line:#262e40; --line-2:#303a50;
        --muted:#9aa5b8; --text:#f4f6fb; --text-soft:#d4dae6;
        --accent:#8c82ff; --accent-2:#68d7ff; --accent-3:#6ff0bd;
        --good:#63e6b1; --warn:#ffd166; --danger:#ff647c;
        --shadow:0 22px 60px rgba(0,0,0,.34);
    }

    html, body, [data-testid="stAppViewContainer"] { background:#090c16 !important; }
    .stApp {
        background:
            radial-gradient(circle at 82% -10%, rgba(120,105,255,.18), transparent 28%),
            radial-gradient(circle at 18% 12%, rgba(64,206,255,.07), transparent 24%),
            linear-gradient(180deg,#090c16 0%,#0b0f19 58%,#090c15 100%);
    }
    [data-testid="stHeader"] { background:rgba(9,12,22,.70) !important; }
    [data-testid="stToolbar"] { background:transparent !important; }
    [data-testid="stSidebar"] {
        background:linear-gradient(180deg,#151925 0%,#10141f 100%) !important;
        border-right:1px solid #202637 !important;
        box-shadow:14px 0 40px rgba(0,0,0,.20);
    }
    [data-testid="stSidebar"] > div:first-child { padding-top:18px; }
    [data-testid="stSidebar"] * { color:var(--text); }
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap:.55rem; }

    .studio-topbar {
        display:flex; align-items:center; justify-content:space-between; gap:18px;
        padding:10px 2px 16px; margin-bottom:2px;
        color:#aeb7c9; font-size:11px; font-weight:800; letter-spacing:.055em;
        text-transform:uppercase;
    }
    .studio-crumbs { display:flex; align-items:center; gap:8px; flex-wrap:wrap; }
    .studio-crumbs .dim { color:#687287; }
    .studio-badge {
        display:inline-flex; align-items:center; gap:7px; padding:6px 10px;
        border-radius:8px; border:1px solid #2d3547; background:#171c28;
        color:#dce2ee; letter-spacing:.04em; text-transform:none;
    }
    .studio-badge.accent { border-color:rgba(140,130,255,.36); color:#c9c3ff; }
    .studio-badge.live { border-color:rgba(99,230,177,.26); color:#69e8b6; }
    .studio-badge.warn { border-color:rgba(255,209,102,.28); color:#ffd56f; }

    .hero {
        position:relative; overflow:hidden; padding:30px 34px; margin-bottom:18px;
        border:1px solid #2a3144; border-radius:22px;
        background:linear-gradient(135deg,rgba(30,35,51,.96),rgba(16,20,31,.98) 58%,rgba(26,29,52,.94));
        box-shadow:var(--shadow);
    }
    .hero:after {
        content:""; position:absolute; width:330px; height:330px; right:-130px; top:-180px;
        border-radius:50%; background:rgba(139,128,255,.16); filter:blur(4px); pointer-events:none;
    }
    .eyebrow { color:#a8a0ff; font-size:10px; font-weight:900; letter-spacing:.18em; text-transform:uppercase; }
    .hero h1 { color:var(--text); margin:7px 0 10px; font-size:39px; line-height:1.08; letter-spacing:-.035em; }
    .muted,.small { color:var(--muted)!important; }

    .card,.cockpit {
        padding:20px; border:1px solid #272f41; border-radius:18px;
        background:linear-gradient(180deg,rgba(24,29,42,.98),rgba(17,21,31,.98));
        box-shadow:0 16px 44px rgba(0,0,0,.20); margin-bottom:14px;
    }
    .card:hover,.cockpit:hover { border-color:#323c52; }
    .agent { display:flex; justify-content:space-between; gap:16px; align-items:center; padding:13px 0; border-bottom:1px solid #252c3c; color:var(--text); }
    .agent:last-child { border-bottom:0; }
    .agent-name { font-weight:750; }
    .status { font-size:10px; font-weight:900; letter-spacing:.10em; padding:5px 9px; border-radius:999px; border:1px solid rgba(99,230,177,.28); color:var(--good); background:rgba(99,230,177,.07); }
    .status.active { color:#bcb6ff; border-color:rgba(140,130,255,.36); background:rgba(140,130,255,.09); }
    .status.waiting { color:var(--warn); border-color:rgba(255,209,102,.30); background:rgba(255,209,102,.07); }
    .status.optional { color:#9aa6bb; border-color:rgba(154,166,187,.24); background:rgba(154,166,187,.06); }

    .question {
        font-size:25px; line-height:1.40; font-weight:760; color:var(--text); padding:25px;
        border:1px solid #30394e; border-left:4px solid var(--accent);
        background:linear-gradient(135deg,#171c29,#121722); border-radius:17px;
        box-shadow:0 16px 42px rgba(0,0,0,.22);
    }
    .category { display:inline-block; padding:6px 10px; border:1px solid #38445b; border-radius:8px; color:#e2e7f1; font-size:11px; background:#181e2b; margin-bottom:10px; font-weight:800; }
    .mode-box { padding:16px; border:1px solid #30394e; border-radius:14px; background:#121722; }
    .cockpit-title { color:#f4f7ff; font-size:12px; font-weight:900; letter-spacing:.08em; text-transform:uppercase; margin-bottom:7px; }

    /* Screenshot-inspired Streamlit controls */
    div[data-testid="stButton"] > button {
        min-height:44px; border-radius:11px; font-weight:850;
        border:1px solid #30394d !important; background:#181e2b !important;
        color:#e9edf5 !important; box-shadow:none; transition:.18s ease;
    }
    div[data-testid="stButton"] > button:hover { border-color:#555d76 !important; transform:translateY(-1px); }
    div[data-testid="stButton"] > button[kind="primary"] {
        color:#0b0d16 !important;
        background:linear-gradient(100deg,#8d82ff 0%,#9d8dff 48%,#67d9ff 100%) !important;
        border-color:transparent !important; box-shadow:0 12px 30px rgba(116,104,255,.24);
    }
    div[data-testid="stButton"] > button[kind="primary"]:hover { box-shadow:0 16px 36px rgba(116,104,255,.34); }
    div[data-baseweb="tab-list"] {
        gap:5px; background:#141925 !important; padding:5px; border:1px solid #272f41;
        border-radius:14px; box-shadow:0 10px 28px rgba(0,0,0,.16);
    }
    button[data-baseweb="tab"] { color:#aeb7c8!important; border-radius:10px; font-weight:800; }
    button[data-baseweb="tab"][aria-selected="true"] {
        color:#f7f7ff!important; background:linear-gradient(100deg,rgba(140,130,255,.30),rgba(104,215,255,.10));
        box-shadow:inset 0 0 0 1px rgba(140,130,255,.18);
    }
    label, [data-testid="stWidgetLabel"] p { color:#e7ebf4!important; font-weight:700!important; }
    input, textarea { color:#f4f6fb!important; caret-color:#a99fff; }
    [data-baseweb="input"], [data-baseweb="textarea"], [data-baseweb="select"] > div {
        background:#111622 !important; border-color:#2d3548 !important; border-radius:10px !important;
    }
    [data-baseweb="input"]:focus-within, [data-baseweb="textarea"]:focus-within { border-color:#7469e8 !important; box-shadow:0 0 0 1px rgba(116,105,232,.35); }
    [data-testid="stMetric"] { background:#121824; border:1px solid #272f40; border-radius:14px; padding:12px 14px; }
    [data-testid="stMetricLabel"] { color:#9ba6ba !important; }
    [data-testid="stMetricValue"] { color:#f4f6fb !important; }
    [data-testid="stProgressBar"] > div { background:#222a3a; }
    [data-testid="stProgressBar"] [role="progressbar"] { background:linear-gradient(90deg,#5fe3b1,#8b82ff,#68d7ff); }
    [data-testid="stExpander"] { background:#121722; border:1px solid #272f40; border-radius:13px; }
    [data-testid="stAlert"] { border-radius:12px; }
    .footer { margin-top:30px; padding:18px 20px; border-top:1px solid #242b3b; color:#758196; text-align:center; }

    .reset-panel {
        padding:16px; border-radius:15px; border:1px solid #30384b;
        background:linear-gradient(145deg,#181d2a,#111621); margin:8px 0 12px;
    }
    .reset-panel .reset-title { color:#f3f5fa; font-weight:900; font-size:13px; letter-spacing:.04em; }
    .reset-panel .reset-copy { color:#929db1; font-size:11px; line-height:1.55; margin-top:5px; }
    .reset-active { border-color:rgba(255,209,102,.26); background:linear-gradient(145deg,rgba(55,47,31,.42),#151923); }
    .reset-ready { border-color:rgba(99,230,177,.20); }

    @media (max-width: 900px) {
        .hero { padding:24px; }
        .hero h1 { font-size:31px; }
        .studio-topbar { align-items:flex-start; flex-direction:column; }
        .question { font-size:21px; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def render_speech_controls(text: str, key: str, title: str, language: str, autoplay: bool = False):
    """Browser-native question playback. It automatically ends/cancels when the utterance ends."""
    payload = json.dumps(text or "", ensure_ascii=False)
    lang_payload = json.dumps(language or "en-US")
    safe_key = re.sub(r"[^A-Za-z0-9_]", "_", key)
    auto_delay = 350 if autoplay else 999999
    components.html(
        f"""
        <div style="font-family:Arial,sans-serif;padding:8px 0;">
          <div style="color:#91a2c0;font-size:12px;font-weight:700;margin-bottom:7px;">🔊 {escape(title)}</div>
          <button id="play_{safe_key}" style="border:1px solid #33466f;background:#151f3b;color:#fff;border-radius:10px;padding:9px 14px;cursor:pointer;margin-right:6px;">▶ Play</button>
          <button id="stop_{safe_key}" style="border:1px solid #33466f;background:#0d1830;color:#c9d4ea;border-radius:10px;padding:9px 14px;cursor:pointer;">■ Stop</button>
          <span id="status_{safe_key}" style="color:#91a2c0;font-size:12px;margin-left:8px;"></span>
        </div>
        <script>
        const text_{safe_key} = {payload};
        const lang_{safe_key} = {lang_payload};
        const play_{safe_key} = document.getElementById('play_{safe_key}');
        const stop_{safe_key} = document.getElementById('stop_{safe_key}');
        const status_{safe_key} = document.getElementById('status_{safe_key}');
        let utterance_{safe_key} = null;
        function stopSpeech_{safe_key}(label='Stopped') {{
          if ('speechSynthesis' in window) window.speechSynthesis.cancel();
          utterance_{safe_key} = null;
          status_{safe_key}.textContent = label;
        }}
        function speak_{safe_key}() {{
          if (!('speechSynthesis' in window)) {{ status_{safe_key}.textContent='Browser speech is not supported.'; return; }}
          stopSpeech_{safe_key}('');
          utterance_{safe_key} = new SpeechSynthesisUtterance(text_{safe_key});
          utterance_{safe_key}.lang = lang_{safe_key};
          utterance_{safe_key}.rate = 0.96;
          utterance_{safe_key}.pitch = 1.0;
          utterance_{safe_key}.onstart = () => status_{safe_key}.textContent='Speaking…';
          utterance_{safe_key}.onend = () => {{ utterance_{safe_key}=null; status_{safe_key}.textContent='Question finished'; }};
          utterance_{safe_key}.onerror = () => {{ utterance_{safe_key}=null; status_{safe_key}.textContent='Speech playback failed'; }};
          window.speechSynthesis.speak(utterance_{safe_key});
        }}
        play_{safe_key}.onclick = speak_{safe_key};
        stop_{safe_key}.onclick = () => stopSpeech_{safe_key}();
        window.addEventListener('beforeunload', () => stopSpeech_{safe_key}(''));
        setTimeout(() => {{ if ({str(autoplay).lower()}) speak_{safe_key}(); }}, {auto_delay});
        </script>
        """,
        height=78,
        scrolling=False,
    )


def render_timer(started_at: float, duration_minutes: int):
    remaining = max(0, int(duration_minutes * 60 - (time.time() - started_at)))
    components.html(
        f"""
        <div style="padding:8px 0;text-align:right;font-family:Arial,sans-serif;">
          <span style="color:#91a2c0;font-size:12px;">SESSION TIME REMAINING</span>
          <div id="timer" style="font-size:24px;font-weight:800;color:#e8edff;">--:--</div>
        </div>
        <script>
        let remaining = {remaining};
        const el = document.getElementById('timer');
        function tick() {{
          const m = Math.floor(Math.max(0, remaining) / 60);
          const s = Math.max(0, remaining) % 60;
          el.textContent = String(m).padStart(2,'0') + ':' + String(s).padStart(2,'0');
          if (remaining <= 0) el.textContent = '00:00 — TIME';
          remaining -= 1;
        }}
        tick(); setInterval(tick, 1000);
        </script>
        """,
        height=70,
        scrolling=False,
    )


def duration_state(started_at: float, duration_minutes: int):
    elapsed = max(0.0, time.time() - started_at)
    remaining = max(0.0, duration_minutes * 60 - elapsed)
    return elapsed, remaining, remaining <= 0


def question_target(duration_minutes: int, elapsed_seconds: float, completed: int) -> int:
    base = TARGET_QUESTIONS[duration_minutes]
    if elapsed_seconds <= 0:
        return base
    # Faster answers allow more questions; slower answers naturally reduce the target.
    avg_turn = elapsed_seconds / max(1, completed)
    projected = int((duration_minutes * 60) / max(avg_turn, 120))
    return max(3, min(base * 2, max(base, projected)))


def speech_metrics(text: str, estimated_seconds: float | None = None):
    words = re.findall(r"\b[\w']+\b", text or "")
    filler_list = ["um", "uh", "erm", "like", "you know", "basically", "actually", "sort of", "kind of"]
    lowered = (text or "").lower()
    fillers = sum(len(re.findall(r"\b" + re.escape(f) + r"\b", lowered)) for f in filler_list)
    words_count = len(words)
    seconds = estimated_seconds or max(10, words_count / 2.3) if words_count else 0
    wpm = round(words_count / (seconds / 60), 1) if seconds else 0
    return {"words": words_count, "filler_words": fillers, "estimated_seconds": round(seconds, 1), "words_per_minute": wpm}


init_db()

DEFAULT_SESSION_STATE = {
    "session_id": None,
    "evidence": None,
    "research": None,
    "turns": [],
    "question": None,
    "started": False,
    "started_at": None,
    "session_duration": 30,
    "question_mode": "Text Questions",
    "answer_mode": "⌨️ Type Answers",
    "categories": CATEGORIES[:],
    "company": "",
    "company_track": "",
    "camera_enabled": False,
    "groq_model": "",
    "reset_notice": False,
}

for key, default in DEFAULT_SESSION_STATE.items():
    if key not in st.session_state:
        st.session_state[key] = uuid.uuid4().hex if key == "session_id" else (default[:] if isinstance(default, list) else default)


def reset_interview_session():
    """Clear only the active interview and its widgets; keep the API key and app configuration intact."""
    dynamic_prefixes = ("answer_input_", "answer_audio_", "camera_", "question_")
    for key in list(st.session_state.keys()):
        if key in {
            "cv", "jd", "target_role_input", "company_input", "mode_input",
            "categories_input", "duration_input", "question_mode_input",
            "answer_mode_input", "research_input", "camera_enabled_input",
            "speech_language_input", "answer_length_input", "company_track_input",
            "jd_text_input", "confirm_reset_input",
        } or key.startswith(dynamic_prefixes):
            del st.session_state[key]

    for key, default in DEFAULT_SESSION_STATE.items():
        if key == "session_id":
            st.session_state[key] = uuid.uuid4().hex
        elif isinstance(default, list):
            st.session_state[key] = default[:]
        elif key == "reset_notice":
            st.session_state[key] = True
        else:
            st.session_state[key] = default


def configured_secret(name: str, default: str = "") -> str:
    """Read Streamlit Cloud secrets first, then local environment variables."""
    try:
        value = st.secrets.get(name, "")
    except Exception:
        value = ""
    return str(value or os.getenv(name, default) or "").strip()


with st.sidebar:
    st.markdown("## 🎯 Intervia")
    st.caption("Evidence-Grounded Interview Intelligence")
    api_key = st.text_input("Groq API key", type="password", value=configured_secret("GROQ_API_KEY"), key="api_key_input")
    target_role = st.text_input("Target role", value="Senior Renewable Energy Engineer", disabled=st.session_state.started, key="target_role_input")
    company = st.text_input("Company / employer (optional)", value=st.session_state.company, disabled=st.session_state.started, key="company_input")

    st.markdown("### Interview Design")
    setup_tab, new_tab = st.tabs(["Interview categories and Interview mode", "New Interview Session"])
    with setup_tab:
        mode = st.selectbox(
            "Interview mode",
            ["Mixed", "Technical", "Behavioral", "Case / Situational", "HR / Screening", "Leadership"],
            disabled=st.session_state.started,
            help="Controls the interviewer's primary question style. Categories below provide the specific areas to test."
            ,key="mode_input"
        )
        categories = st.multiselect(
            "Interview categories",
            CATEGORIES,
            default=st.session_state.categories,
            disabled=st.session_state.started,
            help="Select one or more categories. The adaptive strategy agent balances them as the session progresses."
            ,key="categories_input"
        )

    with new_tab:
        st.markdown("**Start clean, keep your Groq key.**")
        st.caption("This resets the active interview, evidence pack, uploaded files, answers, coaching, timer and adaptive question. Your API key and project deployment remain untouched.")
        if st.session_state.started or st.session_state.turns or st.session_state.evidence:
            st.markdown("<div class='reset-panel reset-active'><div class='reset-title'>● Active interview session</div><div class='reset-copy'>Resetting creates a fresh session ID and clears the current interview workspace. Your Groq key and deployment remain untouched.</div></div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='reset-panel reset-ready'><div class='reset-title'>✓ Ready for a new session</div><div class='reset-copy'>No active interview is currently running. Start a clean session whenever you are ready.</div></div>", unsafe_allow_html=True)
        confirm_reset = st.checkbox("Confirm: clear the current interview session", key="confirm_reset_input")
        if st.button("↻  Reset & Start New Interview", type="primary", use_container_width=True, disabled=not confirm_reset, key="reset_sidebar_button"):
            reset_interview_session()
            st.rerun()

    duration_label = st.selectbox("Practice session duration", list(DURATIONS.keys()), index=0 if st.session_state.session_duration == 30 else list(DURATIONS.values()).index(st.session_state.session_duration), disabled=st.session_state.started, key="duration_input")
    duration_minutes = DURATIONS[duration_label]

    question_mode = st.radio(
        "Question format",
        ["Text Questions", "Audio Questions"],
        index=0 if st.session_state.question_mode == "Text Questions" else 1,
        disabled=st.session_state.started,
        horizontal=True,
        help="Text Questions shows the question on screen. Audio Questions also reads it aloud using the browser's built-in speech synthesis."
        ,key="question_mode_input"
    )
    answer_mode = st.radio(
        "Answer format",
        ["⌨️ Type Answers", "🎙️ Speak Answers"],
        index=0 if st.session_state.answer_mode.startswith("⌨") else 1,
        disabled=st.session_state.started,
        horizontal=True,
        help="Type Answers uses a text box. Speak Answers records your microphone response and sends it to Groq Whisper for transcription."
        ,key="answer_mode_input"
    )
    use_research = st.checkbox("Company / role analysis", value=False, disabled=st.session_state.started, help="Optional AI analysis of the supplied role, JD and company context. It does not invent current company facts.", key="research_input")
    camera_enabled = st.checkbox("Camera presentation snapshot", value=st.session_state.camera_enabled, disabled=st.session_state.started, help="Optional snapshot analysis of observable framing/posture cues. It does not infer emotions or personality.", key="camera_enabled_input")
    speech_language = st.selectbox("Question voice", ["English (US)", "English (UK)"], index=0, disabled=st.session_state.started, key="speech_language_input")
    speech_locale = "en-US" if speech_language == "English (US)" else "en-GB"
    answer_length = st.selectbox("AI practice-answer length", ["Short", "Standard", "Detailed"], disabled=st.session_state.started, key="answer_length_input")
    st.divider()
    st.caption("Tip: for a realistic session, choose the modalities once here. Intervia keeps them fixed for the complete session.")
    st.caption("Production: keep secrets in Streamlit Secrets, not GitHub.")

    if not st.session_state.started:
        st.session_state.session_duration = duration_minutes
        st.session_state.question_mode = question_mode
        st.session_state.answer_mode = answer_mode
        st.session_state.categories = categories or CATEGORIES[:]
        st.session_state.company = company
        st.session_state.company_track = ""
        st.session_state.camera_enabled = camera_enabled

st.markdown(
    f"""<div class="studio-topbar"><div class="studio-crumbs"><span>Workspace</span><span class="dim">›</span><span>Interview Studio</span><span class="studio-badge accent">Session #{escape(st.session_state.session_id[:6])}</span></div><div class="studio-crumbs"><span class="studio-badge">Model: {escape(st.session_state.get('groq_model') or 'Automatic discovery')}</span><span class="studio-badge live">● Secure workspace</span></div></div>""",
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero">
      <div class="eyebrow">Adaptive Interview Intelligence</div>
      <h1>Practice against the job — with text or voice, on your schedule.</h1>
      <div class="muted">Choose question and answer modalities once, select a session length and interview categories, then Intervia automatically adapts the Q&A pace to the remaining time.</div>
    </div>
    """,
    unsafe_allow_html=True,
)

status_col, reset_col = st.columns([4, 1])
with status_col:
    if st.session_state.get("reset_notice"):
        st.success("✨ New interview session is ready. Your previous session state has been cleared.")
        st.session_state.reset_notice = False
    elif st.session_state.started:
        st.info("Interview session active · use **New Interview Session** when you want a clean reset.")
    else:
        st.caption("Session workspace ready · your API key is preserved when you start a new interview.")
with reset_col:
    if st.button("↻ New Interview", use_container_width=True, key="reset_dashboard_button", help="Clear the current interview and return to a fresh session."):
        reset_interview_session()
        st.rerun()

if not st.session_state.started:
    st.info("Before starting: configure **Interview categories and Interview mode**, choose **Text or Audio Questions**, **Type or Speak Answers**, and select your practice session duration.")

left, right = st.columns([1.35, 1])
with left:
    st.markdown("### 1. Build the evidence pack")
    cv_file = st.file_uploader("CV / Resume", type=["pdf", "docx", "txt"], key="cv")
    jd_file = st.file_uploader("Job Description", type=["pdf", "docx", "txt"], key="jd")
    jd_text = st.text_area("Or paste the job description", height=150, placeholder="Paste the JD here if you do not have a file.", key="jd_text_input")
    company_track = st.text_area("Optional company-specific question context", height=90, placeholder="Paste publicly sourced interview themes/questions or a company-specific question bank here. Keep it factual and non-confidential.", disabled=st.session_state.started, key="company_track_input")

    if st.button("Build evidence pack", type="primary", use_container_width=True, disabled=st.session_state.started):
        if not api_key:
            st.error("Enter a Groq API key first.")
        elif not cv_file:
            st.error("Upload a CV / Resume.")
        elif not (jd_file or jd_text.strip()):
            st.error("Upload or paste the Job Description.")
        else:
            st.session_state.company_track = company_track
            cv_text = extract_uploaded_text(cv_file)
            final_jd = extract_uploaded_text(jd_file) if jd_file else jd_text
            st.session_state.evidence = EvidenceAgent().build(
                cv_text=safe_clamp(cv_text, 14000),
                jd_text=safe_clamp(final_jd, 12000),
                target_role=target_role,
                industry="Not specified — grounded in CV/JD and role context",
            )
            st.session_state.research = None
            st.session_state.turns = []
            st.session_state.question = None
            st.session_state.started = False
            st.session_state.started_at = None
            if use_research:
                try:
                    gateway = GroqGateway(api_key)
                    st.session_state.research = ResearchAgent(gateway).run(
                        target_role, "Not specified — grounded in CV/JD and role context", safe_clamp(final_jd, 6000), company=company, company_track=company_track
                    )
                except Exception:
                    st.warning("Company / role analysis is temporarily unavailable. The interview will continue using the CV and Job Description.")
            st.success("Evidence pack created. Candidate evidence, JD requirements and role analysis remain separate.")

with right:
    st.markdown("### Agent cockpit")
    for name, status in [
        ("Evidence Intelligence", "READY" if st.session_state.evidence else "WAITING"),
        ("Career & Market Research", "READY" if st.session_state.research else ("OPTIONAL" if not use_research else "WAITING")),
        ("Interview Strategy", "ACTIVE" if st.session_state.started else "READY"),
        ("AI Interviewer", "ACTIVE" if st.session_state.question else "READY"),
        ("Performance Coach", "READY"),
    ]:
        st.markdown(f'<div class="agent"><span>{name}</span><span class="status">{status}</span></div>', unsafe_allow_html=True)
    st.markdown("### Session design")
    model_label = st.session_state.get("groq_model") or "Automatic model discovery"
    st.markdown(f"<div class='card'><b>{duration_label}</b><br><span class='small'>Mode: {escape(mode)} · Categories: {len(categories or CATEGORIES)}</span><br><span class='small'>Questions: {escape(question_mode)} · Answers: {escape(answer_mode)}</span><br><span class='small'>Groq model: {escape(model_label)}</span><br><span class='small'>Target pacing: approximately {TARGET_QUESTIONS[duration_minutes]} core questions, automatically adjusted for answer speed and remaining time.</span></div>", unsafe_allow_html=True)

if st.session_state.evidence:
    ev = st.session_state.evidence
    st.markdown("### Evidence snapshot")
    c1, c2, c3 = st.columns(3)
    c1.metric("Candidate facts", len(ev.get("candidate_facts", [])))
    c2.metric("JD requirements", len(ev.get("jd_requirements", [])))
    c3.metric("Skill gaps", len(ev.get("gaps", [])))
    with st.expander("View grounding data"):
        st.write("**Candidate evidence**", ev.get("candidate_facts", []))
        st.write("**JD requirements**", ev.get("jd_requirements", []))
        st.write("**Matched skills**", ev.get("matches", []))
        st.write("**Gaps / unknowns**", ev.get("gaps", []))

    if not st.session_state.started:
        if st.button("🚀 Start complete adaptive interview", type="primary", use_container_width=True):
            if not categories:
                st.error("Select at least one interview category.")
            elif not api_key:
                st.error("Groq API key is required.")
            else:
                gateway = GroqGateway(api_key)
                st.session_state.groq_model = gateway.selected_model()
                strategy = StrategyAgent()
                interviewer = InterviewerAgent(gateway)
                now = time.time()
                st.session_state.started_at = now
                elapsed, remaining, _ = duration_state(now, duration_minutes)
                target_count = question_target(duration_minutes, elapsed, 0)
                plan = strategy.plan([], mode, duration_label, ev, categories=categories, remaining_minutes=round(remaining/60, 1), target_questions=target_count)
                try:
                    q = interviewer.ask_question(
                        ev,
                        st.session_state.research,
                        plan,
                        target_role,
                        "Not specified — grounded in CV/JD and role context",
                        mode,
                        company=company,
                    )
                except Exception:
                    st.error("❌ The adaptive interview could not generate Question 1.")
                    st.info("Check your Groq API key and model access, then try again.")
                else:
                    st.session_state.question = q
                    st.session_state.started = True
                    st.session_state.session_duration = duration_minutes
                    st.session_state.question_mode = question_mode
                    st.session_state.answer_mode = answer_mode
                    st.session_state.categories = categories
                    st.session_state.company = company
                    st.session_state.camera_enabled = camera_enabled
                    st.rerun()

if st.session_state.started and st.session_state.question:
    st.markdown("---")
    st.markdown("### 2. Live interview studio")
    elapsed, remaining, expired = duration_state(st.session_state.started_at, st.session_state.session_duration)
    turn_no = len(st.session_state.turns) + 1
    target_count = question_target(st.session_state.session_duration, elapsed, len(st.session_state.turns))
    progress = min(1.0, len(st.session_state.turns) / max(1, target_count))
    top1, top2, top3 = st.columns([1.6, 1, 1])
    with top1:
        st.progress(progress, text=f"Question {turn_no} · adaptive target {target_count}")
    with top2:
        st.metric("Elapsed", f"{int(elapsed//60):02d}:{int(elapsed%60):02d}")
    with top3:
        render_timer(st.session_state.started_at, st.session_state.session_duration)

    if expired:
        st.warning("⏱️ Your selected practice session time has ended. Your report is ready below.")
        st.session_state.question = None
    else:
        q_obj = st.session_state.question if isinstance(st.session_state.question, dict) else {"category": "General", "question": str(st.session_state.question)}
        question_text = q_obj["question"].strip()
        category = q_obj.get("category", "General")
        st.markdown(f"<span class='category'>{escape(category)}</span>", unsafe_allow_html=True)
        st.markdown(f'<div class="question">{escape(question_text)}</div>', unsafe_allow_html=True)
        render_speech_controls(
            question_text,
            f"question_{turn_no}",
            "Generated interview question",
            speech_locale,
            autoplay=(st.session_state.question_mode == "Audio Questions"),
        )
        if st.session_state.question_mode == "Audio Questions":
            st.caption("Audio mode: the question is spoken automatically when available; playback stops automatically when the question finishes. Browser autoplay restrictions may require pressing Play once.")

        st.markdown("#### Your answer")
        st.caption(f"Answer mode locked for this session: **{st.session_state.answer_mode}**")
        answer = ""
        voice_transcript = ""
        audio = None
        if st.session_state.answer_mode == "⌨️ Type Answers":
            answer = st.text_area("Type your answer", key=f"answer_input_{turn_no}", height=190, placeholder="Answer as if you were in the real interview.")
        else:
            audio = st.audio_input("🎙️ Record your answer", sample_rate=16000, key=f"answer_audio_{turn_no}")
            st.caption("Speak naturally. Submit the recording when you finish; Whisper will transcribe it before coaching.")

        camera = None
        if st.session_state.camera_enabled:
            camera = st.camera_input("Optional camera snapshot for presentation-cue feedback", key=f"camera_{turn_no}")
            st.caption("MVP camera analysis is a snapshot, not continuous video. It evaluates only observable framing/posture/camera cues; it does not infer emotions, personality, health or mental state.")

        submit = st.button("Submit answer & get coaching", type="primary", use_container_width=True)
        if submit:
            elapsed_now, remaining_now, expired_now = duration_state(st.session_state.started_at, st.session_state.session_duration)
            if expired_now:
                st.warning("The session time has ended. Finish with the report below.")
                st.session_state.question = None
                st.rerun()
            elif not api_key:
                st.error("Groq API key is required.")
            else:
                gateway = GroqGateway(api_key)
                if st.session_state.answer_mode == "🎙️ Speak Answers" and audio is not None:
                    try:
                        voice_transcript = gateway.transcribe(audio.getvalue(), getattr(audio, "name", "answer.wav")).strip()
                        answer = voice_transcript
                    except Exception as exc:
                        st.error("Voice transcription failed. Please record again or use text.")
                else:
                    answer = (answer or "").strip()

                if not answer:
                    st.error("Provide an answer before submitting.")
                else:
                    coach = CoachAgent(gateway)
                    result = coach.evaluate(
                        question=question_text,
                        answer=answer,
                        evidence=st.session_state.evidence,
                        target_role=target_role,
                        mode=mode,
                        answer_length=answer_length,
                    )
                    metrics = speech_metrics(answer) if voice_transcript else {"words": len(answer.split()), "filler_words": None, "estimated_seconds": None, "words_per_minute": None}
                    camera_feedback = None
                    if camera is not None:
                        try:
                            camera_feedback = gateway.analyze_camera(camera.getvalue(), getattr(camera, "type", "image/jpeg"))
                        except Exception as exc:
                            camera_feedback = {"available": False, "message": "Camera analysis is unavailable for this snapshot."}
                    result["speech_metrics"] = metrics
                    result["presentation_cues"] = camera_feedback
                    st.session_state.turns.append({
                        "question": question_text,
                        "category": category,
                        "answer": answer,
                        "answer_mode": "voice" if voice_transcript else "text",
                        "voice_transcript": voice_transcript,
                        "feedback": result,
                        "timestamp": datetime.now().isoformat(timespec="seconds"),
                        "elapsed_seconds": round(elapsed_now, 1),
                    })
                    save_session(st.session_state.session_id, target_role, "Not specified — grounded in CV/JD and role context", st.session_state.turns)

                    # Generate next question only if time remains.
                    elapsed_after, remaining_after, expired_after = duration_state(st.session_state.started_at, st.session_state.session_duration)
                    if expired_after:
                        st.session_state.question = None
                    else:
                        strategy = StrategyAgent()
                        target_count = question_target(st.session_state.session_duration, elapsed_after, len(st.session_state.turns))
                        plan = strategy.plan(
                            st.session_state.turns,
                            mode,
                            duration_label,
                            st.session_state.evidence,
                            categories=st.session_state.categories,
                            remaining_minutes=round(remaining_after / 60, 1),
                            target_questions=target_count,
                        )
                        interviewer = InterviewerAgent(gateway)
                        try:
                            st.session_state.question = interviewer.ask_question(
                                st.session_state.evidence,
                                st.session_state.research,
                                plan,
                                target_role,
                                "Not specified — grounded in CV/JD and role context",
                                mode,
                                company=company,
                            )
                        except Exception:
                            st.error("❌ The next adaptive question could not be generated.")
                            st.info("Your completed answer has been saved. Check Groq availability and try again.")
                    st.rerun()

    if st.session_state.turns:
        latest = st.session_state.turns[-1]["feedback"]
        st.markdown("### Latest coaching")
        cols = st.columns(6)
        for col, key, label in zip(cols, ["technical", "relevance", "evidence", "communication", "structure", "confidence"], ["Technical", "Relevance", "Evidence", "Communication", "Structure", "Confidence"]):
            col.metric(label, latest.get("scores", {}).get(key, 0))
        st.metric("Overall", latest.get("overall", 0))
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.write("**Strengths**", latest.get("strengths", []))
        st.write("**Missing / improve**", latest.get("missing_points", []))
        st.write("**Verification notes**", latest.get("verification_notes", []))
        st.write("**Practice answer**", latest.get("practice_answer", ""))
        st.write("**Next improvement**", latest.get("next_improvement", ""))
        sm = latest.get("speech_metrics", {})
        if sm:
            st.write("**Speech analytics**", sm)
        if latest.get("presentation_cues"):
            st.write("**Presentation cues**", latest["presentation_cues"])
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("### Category readiness")
        category_scores = defaultdict(list)
        for t in st.session_state.turns:
            category_scores[t.get("category", "General")].append(t.get("feedback", {}).get("overall", 0))
        readiness_cols = st.columns(min(4, max(1, len(category_scores))))
        for idx, (cat, vals) in enumerate(category_scores.items()):
            readiness_cols[idx % len(readiness_cols)].metric(cat.split(" ")[0], round(sum(vals)/len(vals)))

        st.markdown("### 3. Session report")
        md = build_markdown_report(
            target_role=target_role,
            industry="Not specified — grounded in CV/JD and role context",
            mode=mode,
            turns=st.session_state.turns,
            evidence=st.session_state.evidence,
        )
        pdf = build_pdf_report(
            target_role=target_role,
            industry="Not specified — grounded in CV/JD and role context",
            mode=mode,
            turns=st.session_state.turns,
            evidence=st.session_state.evidence,
        )
        st.download_button("Download Markdown report", md, file_name="intervia_report.md", mime="text/markdown")
        st.download_button("Download PDF report", pdf, file_name="intervia_report.pdf", mime="application/pdf")


st.markdown(
    "<div class='footer'>Intervia Interview Intelligence · Premium modular interview workspace · Start a new session anytime without changing your deployment or Groq secret.</div>",
    unsafe_allow_html=True,
)
