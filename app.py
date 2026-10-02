
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
    CoachAgent, EvidenceAgent, GroqGateway, InterviewerAgent,
    ResearchAgent, StrategyAgent,
)
from db import init_db, save_session
from report import build_markdown_report, build_pdf_report
from utils import extract_uploaded_text, safe_clamp


st.set_page_config(
    page_title="Intervia — AI Interview Intelligence",
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

# ---------------------------- Ultra-premium dashboard theme ----------------------------
st.markdown("""
<style>
/* ================================================================
   INTERVIA // ULTRA COMPACT EXECUTIVE DARK UI
   UI-only layer: application logic and workflows are unchanged.
   ================================================================ */
:root{
 --bg:#070B14;
 --bg2:#0A1020;
 --panel:#0F1728;
 --panel2:#121C30;
 --panel3:#0B1323;
 --line:#25324A;
 --line2:#344563;
 --text:#EAF0FA;
 --text2:#C9D4E6;
 --muted:#8D9BB2;
 --muted2:#6F7E98;
 --blue:#4CC9F0;
 --blue2:#72D8FF;
 --violet:#7C6CFF;
 --violet2:#A69BFF;
 --green:#38D9A0;
 --yellow:#F5C451;
 --red:#FF647C;
}
*{box-sizing:border-box}
html,body{background:var(--bg)!important}
.stApp{
 background:
  radial-gradient(900px 360px at 76% -7%,rgba(124,108,255,.15),transparent 62%),
  radial-gradient(700px 320px at 8% 0%,rgba(76,201,240,.07),transparent 64%),
  linear-gradient(180deg,#070B14 0%,#080D18 100%);
 color:var(--text)!important;
}
.block-container{padding:10px 18px 20px!important;max-width:1560px!important}
[data-testid="stSidebar"]{
 background:linear-gradient(180deg,#0A101C 0%,#0B1220 100%)!important;
 border-right:1px solid #202D43!important;
}
[data-testid="stSidebar"] *{color:var(--text2)}
[data-testid="stSidebar"] .stButton button{background:#111A2B!important}
[data-testid="stSidebar"] .stMarkdown{margin-bottom:3px!important}
label,[data-testid="stWidgetLabel"] p,[data-testid="stWidgetLabel"] label{
 color:#BFCBE0!important;font-weight:700!important;font-size:10px!important;letter-spacing:.01em!important;
}
[data-testid="stCaptionContainer"] p,.stCaption{color:#7F8DA5!important;font-size:9px!important}
input,textarea,[data-baseweb="input"] input,[data-baseweb="textarea"] textarea{
 color:#EAF0FA!important;
 -webkit-text-fill-color:#EAF0FA!important;
 background:#0B1424!important;
 border-color:#2A3852!important;
}
input::placeholder,textarea::placeholder{color:#687792!important;-webkit-text-fill-color:#687792!important}
[data-baseweb="select"]>div{background:#0B1424!important;border-color:#2A3852!important;color:#EAF0FA!important}
[data-baseweb="select"] span{color:#EAF0FA!important}
[data-baseweb="popover"] *{color:#EAF0FA!important}
[data-baseweb="menu"]{background:#101A2C!important;border:1px solid #2A3852!important}
[data-baseweb="menu"] *{color:#EAF0FA!important}
[data-baseweb="radio"] label,[data-baseweb="checkbox"] label{color:#C9D4E6!important}
[data-testid="stFileUploader"] section{background:#0B1424!important;border:1px dashed #31415E!important;padding:8px!important}
[data-testid="stFileUploader"] section *{color:#AEBBD0!important}
[data-testid="stExpander"]{background:#0B1322!important;border:1px solid #24324A!important;border-radius:11px!important}
[data-testid="stExpander"] summary{color:#C9D4E6!important;font-size:10px!important}
hr{border-color:#202D43!important;margin:7px 0!important}

/* Native Streamlit tabs: compact, high-contrast, one-row desktop layout. */
div[data-baseweb="tab-list"]{
 display:grid!important;grid-template-columns:repeat(6,minmax(0,1fr));gap:4px!important;
 background:#0B1220!important;padding:4px!important;border:1px solid #202D43!important;border-radius:12px!important;
}
button[data-baseweb="tab"]{
 min-height:30px!important;height:30px!important;padding:4px 6px!important;border-radius:8px!important;
 color:#9EACC2!important;font-size:9px!important;font-weight:800!important;white-space:nowrap!important;
}
button[data-baseweb="tab"][aria-selected="true"]{
 background:linear-gradient(90deg,rgba(124,108,255,.30),rgba(76,201,240,.13))!important;
 color:#F2F6FF!important;border:1px solid rgba(124,108,255,.42)!important;
 box-shadow:0 5px 16px rgba(70,80,180,.15)!important;
}

/* Buttons */
div[data-testid="stButton"]>button,.stDownloadButton>button{
 min-height:34px!important;height:auto!important;padding:6px 10px!important;
 border-radius:9px!important;border:1px solid #31415D!important;background:#101A2B!important;
 color:#DCE6F5!important;font-size:10px!important;font-weight:850!important;
 box-shadow:none!important;transition:all .12s ease!important;
}
div[data-testid="stButton"]>button:hover,.stDownloadButton>button:hover{
 border-color:var(--blue)!important;box-shadow:0 6px 18px rgba(76,201,240,.10)!important;
 color:#FFFFFF!important;
}
div[data-testid="stButton"]>button[kind="primary"]{
 background:linear-gradient(90deg,#7567FF,#4CC9F0)!important;
 color:#07111D!important;border:0!important;box-shadow:0 8px 22px rgba(76,120,255,.20)!important;
}

/* Dense metrics */
.metric-card{
 background:linear-gradient(180deg,#111B2E,#0C1525)!important;border:1px solid #24334B!important;
 border-radius:12px!important;padding:9px 11px!important;min-height:62px!important;
 box-shadow:0 7px 22px rgba(0,0,0,.14)!important;
}
.metric-k{font-size:8px!important;letter-spacing:.12em!important;text-transform:uppercase;color:#8190AA!important;font-weight:900!important}
.metric-v{font-size:19px!important;font-weight:900!important;color:#EDF3FC!important;margin-top:2px!important;line-height:1.05!important}
.metric-s{font-size:8px!important;color:#57D9AA!important;margin-top:2px!important}

.topbar{display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #202D43;padding:2px 1px 8px;margin-bottom:7px;min-height:31px}
.brand{font-weight:950;letter-spacing:.01em;font-size:14px;color:#EAF0FA!important}
.brand span{color:var(--blue2)!important}
.crumb{color:#71809A!important;font-size:9px;font-weight:800}
.chip{display:inline-block;border:1px solid #2A3852;background:#0E1727;color:#AEBBD0;border-radius:999px;padding:3px 7px;font-size:8px;font-weight:900;margin-left:4px;line-height:1.2}
.chip.lav{color:#C8C1FF;border-color:#5149A0;background:rgba(124,108,255,.10)}
.chip.green{color:#65E3B5;border-color:#24634E;background:rgba(56,217,160,.08)}
.chip.red{color:#FF8B9C;border-color:#713545;background:rgba(255,100,124,.09)}
.navrow{
 display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:4px;overflow:hidden;
 background:#0B1220;border:1px solid #202D43;border-radius:12px;padding:4px;margin-bottom:7px;
}
.navpill{padding:6px 4px;border-radius:8px;color:#8493AA;font-size:8.5px;font-weight:900;white-space:nowrap;text-align:center;overflow:hidden;text-overflow:ellipsis}
.navpill.active{background:linear-gradient(90deg,#6E63EE,#4E82F7);color:#F8FAFF;box-shadow:0 5px 15px rgba(90,92,230,.18)}
.hero2{
 padding:11px 14px;border:1px solid #293750;border-radius:13px;
 background:linear-gradient(135deg,rgba(124,108,255,.11),rgba(14,22,38,.97) 58%,rgba(76,201,240,.045));
 box-shadow:0 10px 28px rgba(0,0,0,.17);margin-bottom:7px;
}
.hero2 h1{font-size:22px!important;line-height:1.05!important;margin:3px 0 3px!important;letter-spacing:-.025em!important;color:#EDF3FC!important}
.eyebrow{font-size:8px;color:#AFA7FF;font-weight:950;letter-spacing:.16em;text-transform:uppercase}
.subhero{color:#8E9DB5;font-size:9.5px;max-width:980px;line-height:1.35}
.panel{background:linear-gradient(180deg,#101A2B,#0D1625);border:1px solid #233149;border-radius:12px;padding:10px!important;box-shadow:0 8px 25px rgba(0,0,0,.13);margin-bottom:7px!important}
.panel-title{font-size:9px;letter-spacing:.09em;text-transform:uppercase;color:#D9E2F1!important;font-weight:950;margin-bottom:5px}
.panel-sub{font-size:8.5px;color:#8291A9!important;line-height:1.35}
.question-card{padding:13px!important;border:1px solid #35466A;border-radius:12px;background:linear-gradient(135deg,#101A2C,#0C1525);box-shadow:0 10px 28px rgba(0,0,0,.18)}
.question-card .q{font-size:18px!important;line-height:1.28!important;font-weight:850!important;color:#EDF3FC!important}
.category-pill{display:inline-block;padding:4px 7px;border:1px solid #3D4F76;border-radius:999px;color:#BFCBE0;background:#111D31;font-size:8px;font-weight:900;margin-bottom:6px}
.status-row{display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #202D43;padding:6px 0}
.status-row:last-child{border-bottom:0}
.status-name{font-size:9px;font-weight:800;color:#CBD6E6!important}
.status-badge{font-size:7.5px;font-weight:950;letter-spacing:.09em;border-radius:999px;padding:3px 6px;border:1px solid #24634E;color:#5FE0AF;background:rgba(56,217,160,.08)}
.status-badge.active{border-color:#574DB0;color:#BEB6FF;background:rgba(124,108,255,.10)}
.status-badge.wait{border-color:#6B5A32;color:#F7D57D;background:rgba(245,196,81,.07)}
.status-badge.off{border-color:#33415A;color:#8291A9;background:rgba(120,135,160,.07)}
.evidence-kpi{background:#0A1322;border:1px solid #23324A;border-radius:9px;padding:7px!important}
.evidence-kpi .k{font-size:7px;color:#7D8CA5;text-transform:uppercase;letter-spacing:.1em;font-weight:900}
.evidence-kpi .v{font-size:17px;font-weight:900;margin-top:2px;color:#EAF0FA}
.score-ring{border-radius:11px;padding:11px;background:radial-gradient(circle at 80% 10%,rgba(76,201,240,.08),transparent 45%),#0C1524;border:1px solid #293A55}
.feedback-item{padding:7px 9px;border-left:2px solid var(--violet);background:#0B1423;border-radius:7px;margin:4px 0;color:#C9D4E6!important;font-size:9px;line-height:1.4}
.smallnote{font-size:8px;color:#71809A!important;line-height:1.3}
.footer{padding:8px 3px 2px;color:#596A84;text-align:center;font-size:8px}
.stProgress{margin:3px 0!important}.stProgress>div>div{height:6px!important}.stProgress>div>div>div{background:linear-gradient(90deg,var(--violet),var(--blue))!important}
[data-testid="stMetricValue"]{font-size:18px!important;color:#EDF3FC!important}
[data-testid="stMetricLabel"]{font-size:8px!important;color:#8190A8!important}
[data-testid="stMetricDelta"]{font-size:8px!important}
[data-testid="stHorizontalBlock"]{gap:.45rem!important}
[data-testid="stVerticalBlock"]{gap:.35rem!important}
.stTextInput,.stTextArea,.stSelectbox,.stMultiSelect,.stRadio,.stCheckbox,.stSlider,.stFileUploader{margin-bottom:2px!important}

/* Keep the compact executive layout readable on narrower screens. */
@media (max-width:1100px){
 .block-container{padding-left:10px!important;padding-right:10px!important}
 .navrow{grid-template-columns:repeat(3,minmax(0,1fr))}
 .topbar{gap:6px;align-items:flex-start}.topbar>div:last-child{max-width:58%;text-align:right}
 .hero2 h1{font-size:19px!important}
}
@media (max-width:720px){
 .navrow{grid-template-columns:repeat(2,minmax(0,1fr))}
 .topbar{display:block}.topbar>div:last-child{max-width:100%;text-align:left;margin-top:4px}
 .chip{margin-left:0;margin-right:3px}
 .hero2{padding:9px 10px}.question-card .q{font-size:16px!important}
}

/* ---- Live Adaptive Interview: premium calibration panel (added) ---- */
.aria-card{background:linear-gradient(180deg,#111B2E,#0C1525);border:1px solid #2A3A56;border-radius:14px;padding:14px}
.aria-head{display:flex;align-items:center;gap:10px}
.aria-avatar{width:40px;height:40px;border-radius:50%;background:linear-gradient(135deg,#7C6CFF,#4CC9F0);display:flex;align-items:center;justify-content:center;font-size:18px;flex-shrink:0}
.aria-name{font-size:12.5px;font-weight:900;color:#F2F6FF}
.aria-sub{font-size:8.5px;color:#9FB0D6}
.probe-badge{margin-left:auto;background:#182238;color:#9FB0D6;font-size:7.5px;font-weight:900;padding:4px 8px;border-radius:999px;border:1px solid #2A3A56;white-space:nowrap}
.prompt-label{font-size:7.5px;letter-spacing:.1em;text-transform:uppercase;color:#8FA0D0;margin-top:10px;font-weight:900}
.prompt-quote{font-size:14px;color:#EDF3FC;font-weight:650;margin-top:5px;line-height:1.45}
.focus-row{display:flex;flex-wrap:wrap;gap:6px;margin-top:10px}
.focus-tag{font-size:7.5px;font-weight:800;color:#BFCBE0;background:#111D31;border:1px solid #30415E;border-radius:999px;padding:4px 8px}
.you-row{display:flex;align-items:center;gap:8px;margin-top:12px;padding-top:10px;border-top:1px solid #202D43}
.you-row .name{font-size:9.5px;font-weight:900;color:#EAF0FA}
.you-row .meta{font-size:7.5px;color:#5FE0AF}
.tip-card{margin-top:10px;background:#0B1424;border-left:2px solid var(--violet);border-radius:8px;padding:8px 10px;font-size:8.5px;color:#C9D4E6;line-height:1.45}
.voice-toggle-row{display:flex;gap:6px;align-items:center;margin-bottom:8px}
.toggle-pill{font-size:7.5px;font-weight:900;padding:5px 10px;border-radius:999px;border:1px solid #2A3852}
.toggle-pill.on{background:linear-gradient(90deg,#7567FF,#4CC9F0);color:#07111D;border:0}
.toggle-pill.off{color:#8190AA;background:#101A2B}
.online-chip{margin-left:auto;font-size:7.5px;color:#5FE0AF;font-weight:900}
.neural-card{background:radial-gradient(circle at 70% 0%,rgba(124,108,255,.12),transparent 55%),#0B1322;border:1px solid #2A3A56;border-radius:14px;padding:14px;text-align:center}
.neural-label{font-size:7.5px;letter-spacing:.14em;color:#8190AA;font-weight:900}
.wave{display:flex;align-items:center;justify-content:center;gap:4px;height:40px;margin:8px 0}
.wave-bar{width:4px;border-radius:2px;background:linear-gradient(180deg,#7C6CFF,#4CC9F0);animation:wavepulse 1s ease-in-out infinite}
.wave-bar:nth-child(1){height:12px;animation-delay:0s}
.wave-bar:nth-child(2){height:24px;animation-delay:.1s}
.wave-bar:nth-child(3){height:36px;animation-delay:.2s}
.wave-bar:nth-child(4){height:20px;animation-delay:.3s}
.wave-bar:nth-child(5){height:32px;animation-delay:.4s}
.wave-bar:nth-child(6){height:14px;animation-delay:.5s}
.wave-bar:nth-child(7){height:26px;animation-delay:.6s}
@keyframes wavepulse{0%,100%{transform:scaleY(.4)}50%{transform:scaleY(1)}}
.live-stat-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:6px;margin-top:10px}
.live-stat{background:#0F1A2C;border:1px solid #24334B;border-radius:10px;padding:7px;text-align:center}
.live-stat .k{font-size:6.5px;color:#7D8CA5;text-transform:uppercase;letter-spacing:.08em;font-weight:900}
.live-stat .v{font-size:15px;font-weight:900;color:#EDF3FC;margin-top:2px}
.live-stat .s{font-size:7px;color:#5FE0AF;margin-top:1px}
.transcript-preview{background:#0B1424;border:1px solid #2A3852;border-radius:10px;padding:10px;font-size:9.5px;color:#DCE6F5;line-height:1.55;margin-top:10px}
mark.filler{background:#4A3A14;color:#F5C451;border-radius:3px;padding:0 2px}
</style>
""", unsafe_allow_html=True)

# ---------------------------- Helpers ----------------------------
def configured_secret(name: str, default: str = "") -> str:
    try:
        value = st.secrets.get(name, "")
    except Exception:
        value = ""
    return str(value or os.getenv(name, default) or "").strip()


def render_speech_controls(text: str, key: str, title: str, language: str, autoplay: bool = False):
    payload = json.dumps(text or "", ensure_ascii=False)
    lang_payload = json.dumps(language or "en-US")
    safe_key = re.sub(r"[^A-Za-z0-9_]", "_", key)
    delay = 450 if autoplay else 999999
    components.html(f"""
    <div style="font-family:Arial,sans-serif;padding:5px 0">
      <span style="color:#7F8DA6;font-size:10px;font-weight:800;letter-spacing:.08em">{escape(title).upper()}</span>
      <button id="p_{safe_key}" style="margin-left:12px;border:1px solid #34425F;background:#141D31;color:#fff;border-radius:9px;padding:7px 12px">▶ Play</button>
      <button id="s_{safe_key}" style="border:1px solid #2C3852;background:#0C1424;color:#AAB7CD;border-radius:9px;padding:7px 12px">■ Stop</button>
      <span id="m_{safe_key}" style="color:#7F8DA6;font-size:10px;margin-left:8px"></span>
    </div>
    <script>
    const t_{safe_key}={payload}, l_{safe_key}={lang_payload}, p_{safe_key}=document.getElementById('p_{safe_key}'), s_{safe_key}=document.getElementById('s_{safe_key}'), m_{safe_key}=document.getElementById('m_{safe_key}');
    function stop_{safe_key}(){{if('speechSynthesis' in window) speechSynthesis.cancel();m_{safe_key}.textContent='Stopped';}}
    function play_{safe_key}(){{if(!('speechSynthesis' in window)){{m_{safe_key}.textContent='Browser speech unavailable';return;}}stop_{safe_key}();let u=new SpeechSynthesisUtterance(t_{safe_key});u.lang=l_{safe_key};u.rate=.96;u.onstart=()=>m_{safe_key}.textContent='Speaking…';u.onend=()=>m_{safe_key}.textContent='Question finished';u.onerror=()=>m_{safe_key}.textContent='Playback failed';speechSynthesis.speak(u);}}
    p_{safe_key}.onclick=play_{safe_key};s_{safe_key}.onclick=stop_{safe_key};setTimeout(()=>{{if({str(autoplay).lower()})play_{safe_key}();}},{delay});
    </script>
    """, height=55, scrolling=False)


def render_timer(started_at: float, duration_minutes: int):
    remaining = max(0, int(duration_minutes * 60 - (time.time() - started_at)))
    components.html(f"""
    <div style="text-align:right;font-family:Arial,sans-serif">
      <span style="font-size:9px;color:#7D8AA2;font-weight:900;letter-spacing:.12em">SESSION TIME REMAINING</span>
      <div id="tm" style="font-size:22px;color:#EEF2FF;font-weight:900">--:--</div>
    </div>
    <script>
    let r={remaining},e=document.getElementById('tm');function t(){{let m=Math.floor(Math.max(0,r)/60),s=Math.max(0,r)%60;e.textContent=String(m).padStart(2,'0')+':'+String(s).padStart(2,'0');r--;}}t();setInterval(t,1000);
    </script>
    """, height=55, scrolling=False)


def duration_state(started_at: float, duration_minutes: int):
    elapsed = max(0.0, time.time() - started_at)
    remaining = max(0.0, duration_minutes * 60 - elapsed)
    return elapsed, remaining, remaining <= 0


def question_target(duration_minutes: int, elapsed_seconds: float, completed: int) -> int:
    base = TARGET_QUESTIONS[duration_minutes]
    if elapsed_seconds <= 0:
        return base
    avg_turn = elapsed_seconds / max(1, completed)
    projected = int((duration_minutes * 60) / max(avg_turn, 120))
    return max(3, min(base * 2, max(base, projected)))


def speech_metrics(text: str, estimated_seconds: float | None = None):
    words = re.findall(r"\b[\w']+\b", text or "")
    filler_list = ["um", "uh", "erm", "like", "you know", "basically", "actually", "sort of", "kind of"]
    lowered = (text or "").lower()
    fillers = sum(len(re.findall(r"\b" + re.escape(f) + r"\b", lowered)) for f in filler_list)
    seconds = estimated_seconds or max(10, len(words) / 2.3) if words else 0
    return {
        "words": len(words),
        "filler_words": fillers,
        "estimated_seconds": round(seconds, 1),
        "words_per_minute": round(len(words) / (seconds / 60), 1) if seconds else 0,
    }


FILLER_LIST = ["um", "uh", "erm", "like", "you know", "basically", "actually", "sort of", "kind of"]


def clarity_heuristic(filler_words: int, words: int, wpm: float) -> float:
    """A local, deterministic clarity heuristic for the pre-submit calibration view only —
    not the Coach Agent's official communication score, which is computed after submission."""
    score = 10.0
    if words:
        score -= min(4.0, (filler_words / max(words, 1)) * 20)
    if wpm and (wpm < 110 or wpm > 170):
        score -= 1.5
    return round(max(1.0, min(10.0, score)), 1)


def remove_fillers(text: str) -> str:
    cleaned = text or ""
    for f in FILLER_LIST:
        cleaned = re.sub(r"(?i)\b" + re.escape(f) + r"\b,?", "", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
    cleaned = re.sub(r"\s+([.,!?])", r"\1", cleaned)
    return cleaned


def highlight_fillers_html(text: str) -> str:
    out = escape(text or "")
    for f in FILLER_LIST:
        out = re.sub(r"(?i)\b(" + re.escape(f) + r")\b", r'<mark class="filler">\1</mark>', out)
    return out


def metric_card(label, value, sub="", sub_class=""):
    return f"""<div class="metric-card"><div class="metric-k">{escape(str(label))}</div><div class="metric-v">{escape(str(value))}</div><div class="metric-s {sub_class}">{escape(str(sub))}</div></div>"""


def reset_session():
    for key, val in {
        "session_id": str(uuid.uuid4()), "evidence": None, "research": None, "turns": [],
        "question": None, "started": False, "started_at": None, "session_duration": 30,
        "question_mode": "Text Questions", "answer_mode": "⌨️ Type Answers",
        "categories": CATEGORIES[:], "company": "", "company_track": "", "camera_enabled": False,
        "groq_model": "", "session_complete": False, "last_plan": None
    }.items():
        st.session_state[key] = val


init_db()
defaults = {
    "session_id": str(uuid.uuid4()), "evidence": None, "research": None, "turns": [],
    "question": None, "started": False, "started_at": None, "session_duration": 30,
    "question_mode": "Text Questions", "answer_mode": "⌨️ Type Answers",
    "categories": CATEGORIES[:], "company": "", "company_track": "", "camera_enabled": False,
    "groq_model": "", "session_complete": False, "last_plan": None
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ---------------------------- Sidebar ----------------------------
with st.sidebar:
    st.markdown("### 🎯 Intervia")
    st.caption("STUDIO COCKPIT • AI INTERVIEW INTELLIGENCE")
    st.markdown('<div class="smallnote">Evidence-grounded • adaptive • professional session telemetry</div>', unsafe_allow_html=True)
    st.divider()

    st.markdown("**TARGET PROFILE**")
    target_role = st.text_input("Target job position", value="Senior Backend Software Engineer", disabled=st.session_state.started)
    company = st.text_input("Company / employer (optional)", value=st.session_state.company, disabled=st.session_state.started)

    st.markdown("**PERSONA MODEL**")
    persona = st.radio("Persona", ["FAANG-Style", "Friendly", "Strict Exec", "Startup CTO"], horizontal=True, disabled=st.session_state.started, label_visibility="collapsed")

    st.markdown("**EVALUATION VECTOR**")
    mode = st.selectbox("Primary vector", ["Mixed", "Technical", "Behavioral", "Case / Situational", "HR / Screening", "Leadership"], disabled=st.session_state.started)
    categories = st.multiselect("Interview categories", CATEGORIES, default=st.session_state.categories, disabled=st.session_state.started)

    st.markdown("**ADAPTIVE ESCALATION**")
    difficulty = st.select_slider("Difficulty baseline", ["Foundation", "Standard", "Hard", "Ultra Hard"], value="Standard", disabled=st.session_state.started)

    st.markdown("**CONTEXT INGESTION**")
    st.caption("CV + JD remain the candidate-grounding source. External research is a separate evidence class.")

    st.markdown("**SESSION DESIGN**")
    duration_label = st.selectbox("Practice session duration", list(DURATIONS.keys()), index=list(DURATIONS.values()).index(st.session_state.session_duration), disabled=st.session_state.started)
    question_mode = st.radio("Question format", ["Text Questions", "Audio Questions"], index=0 if st.session_state.question_mode == "Text Questions" else 1, horizontal=True, disabled=st.session_state.started)
    answer_mode = st.radio("Answer format", ["⌨️ Type Answers", "🎙️ Speak Answers"], index=0 if st.session_state.answer_mode.startswith("⌨") else 1, horizontal=True, disabled=st.session_state.started)
    use_research = st.checkbox("Current role/company research", value=False, disabled=st.session_state.started)
    camera_enabled = st.checkbox("Presentation snapshot", value=st.session_state.camera_enabled, disabled=st.session_state.started)
    speech_language = st.selectbox("Question voice", ["English (US)", "English (UK)"], disabled=st.session_state.started)
    speech_locale = "en-US" if speech_language == "English (US)" else "en-GB"
    answer_length = st.selectbox("Practice-answer length", ["Short", "Standard", "Detailed"], disabled=st.session_state.started)

    st.divider()
    api_key = st.text_input("Groq API key", type="password", value=configured_secret("GROQ_API_KEY"), help="For Streamlit Cloud, use st.secrets instead of committing keys.")
    if not st.session_state.started:
        st.session_state.session_duration = DURATIONS[duration_label]
        st.session_state.question_mode = question_mode
        st.session_state.answer_mode = answer_mode
        st.session_state.categories = categories or CATEGORIES[:]
        st.session_state.company = company
        st.session_state.camera_enabled = camera_enabled

# ---------------------------- Top shell ----------------------------
model_label = st.session_state.get("groq_model") or "AUTO MODEL"
st.markdown(f"""
<div class="topbar">
  <div><span class="brand">InterviewAI <span>STUDIO COCKPIT</span></span><span class="crumb">&nbsp; / &nbsp;Workspace / Session Telemetry <span style="color:#5FE0AF">#sess-{escape(st.session_state.session_id[:4])}</span></span></div>
  <div>
    <span class="chip lav">{escape(model_label)}</span>
    <span class="chip green">Evidence Grounded</span>
    <span class="chip">{escape(persona)}</span>
    <span class="chip">{escape(difficulty)} Track</span>
  </div>
</div>
<div class="navrow">
  <div class="navpill active">1. Live Adaptive Interview</div>
  <div class="navpill">2. 6-D Evaluation</div>
  <div class="navpill">3. JD → Curriculum</div>
  <div class="navpill">4. Resume & ATS Gap</div>
  <div class="navpill">5. Live Coding IDE</div>
  <div class="navpill">6. Executive Performance</div>
</div>
""", unsafe_allow_html=True)

st.markdown(f"""
<div class="hero2">
  <div class="eyebrow">AI INTERVIEW • SMARTER YOU</div>
  <h1>Premium adaptive interview cockpit.</h1>
  <div class="subhero">Realistic hiring-manager questions grounded in your CV and Job Description, with adaptive escalation, voice/text practice, ATS readiness, and a complete professional report after every session.</div>
</div>
""", unsafe_allow_html=True)

# KPI strip
ev = st.session_state.evidence or {}
ats = ev.get("ats_readiness", {})
k1, k2, k3, k4, k5 = st.columns(5)
k1.markdown(metric_card("TARGET ROLE", target_role, "Profile locked at start"), unsafe_allow_html=True)
k2.markdown(metric_card("ATS READINESS", f"{ats.get('score', '--')}/100", ats.get("band", "Build evidence first")), unsafe_allow_html=True)
k3.markdown(metric_card("INTERVIEW PROGRESS", f"{len(st.session_state.turns)}", f"of ~{TARGET_QUESTIONS[st.session_state.session_duration]} core questions"), unsafe_allow_html=True)
latest_score = st.session_state.turns[-1]["feedback"].get("overall", 0) if st.session_state.turns else 0
k4.markdown(metric_card("LATEST SCORE", f"{latest_score}/100", "Coach evaluation" if st.session_state.turns else "No answer scored yet"), unsafe_allow_html=True)
k5.markdown(metric_card("AGENT STATUS", "5 / 5", "Logical agent system ready"), unsafe_allow_html=True)

# ---------------------------- Evidence ingestion ----------------------------
left, right = st.columns([1.42, 1], gap="medium")
with left:
    st.markdown('<div class="panel"><div class="panel-title">Candidate Evidence Intelligence</div><div class="panel-sub">Upload the candidate CV/Resume and Job Description. The ATS check is a deterministic readiness heuristic; it does not certify any vendor ATS.</div></div>', unsafe_allow_html=True)
    cv_file = st.file_uploader("CV / Resume", type=["pdf", "docx", "txt"], key="cv")
    jd_file = st.file_uploader("Job Description", type=["pdf", "docx", "txt"], key="jd")
    jd_text = st.text_area("Or paste the Job Description", height=120, placeholder="Paste the job description if you do not have a file.")
    company_track = st.text_area("Optional public company/role context", height=75, placeholder="Add factual, public context if desired. This is never converted into candidate evidence.", disabled=st.session_state.started)

    b1, b2 = st.columns([1.2, 1])
    with b1:
        build_evidence = st.button("⚡ Build Evidence + ATS Intelligence", type="primary", use_container_width=True, disabled=st.session_state.started)
    with b2:
        if st.button("↺ New Session", use_container_width=True):
            reset_session()
            st.rerun()

    if build_evidence:
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
            st.session_state.session_complete = False
            st.session_state.started_at = None
            if use_research:
                try:
                    gateway = GroqGateway(api_key)
                    st.session_state.research = ResearchAgent(gateway).run(
                        target_role, "Not specified — grounded in CV/JD and role context",
                        safe_clamp(final_jd, 6000), company=company, company_track=company_track
                    )
                except Exception:
                    st.warning("Optional current role/company research is unavailable. The interview will continue with CV/JD evidence.")
            st.success("Evidence pack created. Candidate evidence, JD requirements, ATS signals and optional research remain separated.")

with right:
    st.markdown('<div class="panel"><div class="panel-title">5-Agent Mission Control</div>', unsafe_allow_html=True)
    statuses = [
        ("Evidence Intelligence", "READY" if st.session_state.evidence else "WAIT"),
        ("Research Intelligence", "READY" if st.session_state.research else ("OPTIONAL" if not use_research else "WAIT")),
        ("Adaptive Strategy", "ACTIVE" if st.session_state.started else "READY"),
        ("AI Interviewer", "ACTIVE" if st.session_state.question else "READY"),
        ("Performance Coach", "READY" if st.session_state.started or st.session_state.turns else "STANDBY"),
    ]
    for name, status in statuses:
        cls = "active" if status == "ACTIVE" else "wait" if status == "WAIT" else "off" if status in ("OPTIONAL","STANDBY") else ""
        st.markdown(f'<div class="status-row"><span class="status-name">{escape(name)}</span><span class="status-badge {cls}">{status}</span></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

if st.session_state.evidence:
    ev = st.session_state.evidence
    ats = ev.get("ats_readiness", {})
    st.markdown('<div class="panel"><div class="panel-title">Evidence Control Center</div>', unsafe_allow_html=True)
    ec1, ec2, ec3, ec4, ec5 = st.columns(5)
    ec1.markdown(f'<div class="evidence-kpi"><div class="k">Candidate facts</div><div class="v">{len(ev.get("candidate_facts", []))}</div></div>', unsafe_allow_html=True)
    ec2.markdown(f'<div class="evidence-kpi"><div class="k">JD requirements</div><div class="v">{len(ev.get("jd_requirements", []))}</div></div>', unsafe_allow_html=True)
    ec3.markdown(f'<div class="evidence-kpi"><div class="k">JD matches</div><div class="v">{len(ev.get("matches", []))}</div></div>', unsafe_allow_html=True)
    ec4.markdown(f'<div class="evidence-kpi"><div class="k">Skill gaps</div><div class="v">{len(ev.get("gaps", []))}</div></div>', unsafe_allow_html=True)
    ec5.markdown(f'<div class="evidence-kpi"><div class="k">ATS score</div><div class="v">{ats.get("score", 0)}/100</div></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    with st.expander("ATS readiness details — parser/keyword/formatting heuristic"):
        st.write(f"**Band:** {ats.get('band', 'Not calculated')}")
        for check in ats.get("checks", []):
            st.write(f"**{check['name']} — {check['score']}/100 — {check['status']}**")
            st.caption(check["detail"])
        if ats.get("keyword_gaps"):
            st.write("**JD terms to review:**", ", ".join(ats["keyword_gaps"]))
        if ats.get("recommendations"):
            st.write("**Recommendations:**")
            for item in ats["recommendations"]:
                st.write("• " + item)

    with st.expander("Evidence ledger — candidate facts vs JD requirements"):
        st.write("**Candidate evidence (CV only)**")
        st.write(ev.get("candidate_facts", []))
        st.write("**JD requirements (not candidate facts)**")
        st.write(ev.get("jd_requirements", []))
        st.write("**Grounding matches**")
        st.write(ev.get("matches", []))
        st.write("**Unknowns / gaps**")
        st.write(ev.get("gaps", []))

    if not st.session_state.started and not st.session_state.session_complete:
        if st.button("🚀 START ULTRA ADAPTIVE INTERVIEW", type="primary", use_container_width=True):
            if not categories:
                st.error("Select at least one interview category.")
            elif not api_key:
                st.error("Groq API key is required.")
            else:
                try:
                    gateway = GroqGateway(api_key)
                    st.session_state.groq_model = gateway.selected_model()
                    strategy = StrategyAgent()
                    interviewer = InterviewerAgent(gateway)
                    now = time.time()
                    st.session_state.started_at = now
                    elapsed, remaining, _ = duration_state(now, st.session_state.session_duration)
                    target_count = question_target(st.session_state.session_duration, elapsed, 0)
                    plan = strategy.plan([], mode, duration_label, ev, categories=categories, remaining_minutes=round(remaining/60, 1), target_questions=target_count)
                    st.session_state.last_plan = plan
                    q = interviewer.ask_question(ev, st.session_state.research, plan, target_role, "Not specified", mode, company=company)
                    st.session_state.question = q
                    st.session_state.started = True
                    st.session_state.session_complete = False
                    st.rerun()
                except Exception:
                    st.error("The adaptive interview could not start. Check the Groq key, model access and network, then retry.")

# ---------------------------- Live interview studio ----------------------------
if st.session_state.started and st.session_state.question:
    st.markdown('<div class="panel"><div class="panel-title">Live Adaptive Interview • Session Telemetry</div>', unsafe_allow_html=True)
    elapsed, remaining, expired = duration_state(st.session_state.started_at, st.session_state.session_duration)
    turn_no = len(st.session_state.turns) + 1
    target_count = question_target(st.session_state.session_duration, elapsed, len(st.session_state.turns))
    progress = min(1.0, len(st.session_state.turns) / max(1, target_count))
    p1, p2, p3 = st.columns([1.7, .7, .8])
    with p1:
        st.progress(progress, text=f"Question {turn_no} of adaptive target • {escape(difficulty)} escalation track")
    with p2:
        st.metric("Elapsed", f"{int(elapsed//60):02d}:{int(elapsed%60):02d}")
    with p3:
        render_timer(st.session_state.started_at, st.session_state.session_duration)
    st.markdown('</div>', unsafe_allow_html=True)

    if expired:
        st.warning("⏱️ Session time reached zero. Your complete session report is ready below.")
        st.session_state.question = None
        st.session_state.session_complete = True
    else:
        q_obj = st.session_state.question if isinstance(st.session_state.question, dict) else {"category": "Adaptive", "question": str(st.session_state.question)}
        question_text = q_obj.get("question", "").strip()
        category = q_obj.get("category", "Adaptive")
        plan = st.session_state.last_plan or {}
        focus = plan.get("focus", "High-signal role-specific baseline")
        weakest = plan.get("weakest_dimension", "relevance")
        is_voice = answer_mode == "🎙️ Speak Answers"
        tags = [t for t in [category, str(focus).title(), f"Watch: {str(weakest).title()}", difficulty] if t]

        qleft, qright = st.columns([1.3, 1], gap="medium")
        with qleft:
            st.markdown(
                '<div class="aria-card"><div class="aria-head">'
                '<div class="aria-avatar">🤖</div>'
                f'<div><div class="aria-name">Aria-6X <span style="color:#5FE0AF">✓ verified</span></div>'
                f'<div class="aria-sub">{escape(persona)} • Interview Agent</div></div>'
                '<div class="probe-badge">ACTIVE PROBE</div></div>'
                '<div class="prompt-label">Live Interview Prompt</div>'
                f'<div class="prompt-quote">“{escape(question_text)}”</div>'
                f'<div class="focus-row">{"".join(f"<span class=\'focus-tag\'>{escape(t)}</span>" for t in tags)}</div>'
                '<div class="you-row"><span class="name">You</span>'
                f'<span class="meta">{"🎙️ Voice mode" if is_voice else "⌨️ Text mode"}</span></div>'
                f'<div class="tip-card">💡 <b>Strategy note:</b> this question targets <b>{escape(str(focus))}</b> — '
                f'your current weakest-scoring dimension is <b>{escape(str(weakest))}</b>. Answer with a concrete '
                'example, your decision, and the measurable outcome.</div></div>',
                unsafe_allow_html=True,
            )
            render_speech_controls(question_text, f"q_{turn_no}", "Generated hiring-manager question", speech_locale, autoplay=question_mode=="Audio Questions")
            if question_mode == "Audio Questions":
                st.caption("Audio mode uses browser speech synthesis. Browser autoplay policies may require one manual Play click.")
            camera = st.camera_input("Optional presentation snapshot", key=f"cam_{turn_no}") if camera_enabled else None

        answer, voice_transcript, audio = "", "", None
        with qright:
            st.markdown(
                '<div class="voice-toggle-row">'
                f'<span class="toggle-pill {"on" if is_voice else "off"}">🎙️ Voice Stream</span>'
                f'<span class="toggle-pill {"on" if not is_voice else "off"}">⌨️ Text Mode</span>'
                f'<span class="online-chip">{"WHISPER-V3 ONLINE ●" if is_voice else "TEXT CAPTURE ●"}</span></div>',
                unsafe_allow_html=True,
            )
            if not is_voice:
                answer = st.text_area("Your answer", key=f"answer_{turn_no}", height=250, placeholder="Answer naturally. Use concrete examples, decisions, trade-offs and outcomes.")
            else:
                nonce_key, draft_key, cache_key = f"audio_nonce_{turn_no}", f"draft_transcript_{turn_no}", f"draft_src_{turn_no}"
                st.session_state.setdefault(nonce_key, 0)
                st.markdown(
                    '<div class="neural-card"><div class="neural-label">LIVE NEURAL AUDIO BUFFER</div>'
                    '<div class="wave">' + "".join('<div class="wave-bar"></div>' for _ in range(7)) + '</div></div>',
                    unsafe_allow_html=True,
                )
                audio = st.audio_input("🎙️ Record your answer", sample_rate=16000, key=f"audio_{turn_no}_{st.session_state[nonce_key]}")
                st.caption("Record your full answer, then review the calibration panel below before submitting.")

                if audio is not None and api_key and st.session_state.get(cache_key) != id(audio):
                    try:
                        gateway = GroqGateway(api_key)
                        st.session_state[draft_key] = gateway.transcribe(audio.getvalue(), getattr(audio, "name", "answer.wav")).strip()
                        st.session_state[cache_key] = id(audio)
                    except Exception:
                        st.error("Voice transcription failed. Please re-record or switch to text.")

                if st.session_state.get(draft_key):
                    mp = speech_metrics(st.session_state[draft_key])
                    clarity = clarity_heuristic(mp["filler_words"], mp["words"], mp["words_per_minute"])
                    dur = mp["estimated_seconds"] or 0
                    st.markdown(
                        '<div class="live-stat-grid">'
                        f'<div class="live-stat"><div class="k">Speaking Pace</div><div class="v">{mp["words_per_minute"]}</div><div class="s">WPM</div></div>'
                        f'<div class="live-stat"><div class="k">Filler Words</div><div class="v">{mp["filler_words"]}</div><div class="s">detected</div></div>'
                        f'<div class="live-stat"><div class="k">Duration</div><div class="v">{int(dur//60)}:{int(dur%60):02d}</div><div class="s">est.</div></div>'
                        f'<div class="live-stat"><div class="k">Clarity</div><div class="v">{clarity}/10</div><div class="s">heuristic</div></div></div>',
                        unsafe_allow_html=True,
                    )
                    st.caption("Clarity is a local calibration heuristic — the Coach Agent's official communication score is produced after submission.")
                    st.markdown('<div class="prompt-label" style="margin-top:10px">Live Transcription — edit before calibrating</div>', unsafe_allow_html=True)
                    edited = st.text_area("Transcript", value=st.session_state[draft_key], key=f"edit_{draft_key}_{st.session_state[nonce_key]}", height=130, label_visibility="collapsed")
                    st.session_state[draft_key] = edited

                    rc1, rc2 = st.columns(2)
                    with rc1:
                        if st.button("↺ Re-record & Reset", key=f"rerecord_{turn_no}", use_container_width=True):
                            st.session_state[nonce_key] += 1
                            st.session_state[draft_key] = ""
                            st.session_state.pop(cache_key, None)
                            st.rerun()
                    with rc2:
                        if st.button("🧹 Auto-Remove Fillers", key=f"declutter_{turn_no}", use_container_width=True):
                            st.session_state[draft_key] = remove_fillers(st.session_state[draft_key])
                            st.rerun()
                    voice_transcript = st.session_state[draft_key]
                    answer = voice_transcript
                else:
                    st.caption("Once your recording is captured, the transcript and calibration stats appear here for review.")

        submit = st.button("✨ Submit Answer & Calibrate Next Question", type="primary", use_container_width=True)
        if submit:
            elapsed_now, remaining_now, expired_now = duration_state(st.session_state.started_at, st.session_state.session_duration)
            if expired_now:
                st.session_state.question = None
                st.session_state.session_complete = True
                st.rerun()
            elif not api_key:
                st.error("Groq API key is required.")
            else:
                gateway = GroqGateway(api_key)
                # Voice answers are transcribed as soon as they're recorded (calibration panel
                # above), and the candidate may have edited the transcript there — so submission
                # uses that already-calibrated text rather than re-transcribing the raw audio.
                answer = (answer or "").strip()

                if not answer:
                    st.error("Provide an answer before submitting.")
                else:
                    try:
                        coach = CoachAgent(gateway)
                        result = coach.evaluate(question_text, answer, st.session_state.evidence, target_role, mode, answer_length)
                        metrics = speech_metrics(answer) if voice_transcript else {
                            "words": len(answer.split()), "filler_words": None, "estimated_seconds": None, "words_per_minute": None
                        }
                        camera_feedback = None
                        if camera is not None:
                            try:
                                camera_feedback = gateway.analyze_camera(camera.getvalue(), getattr(camera, "type", "image/jpeg"))
                            except Exception:
                                camera_feedback = {"available": False, "message": "Presentation snapshot analysis unavailable."}
                        result["speech_metrics"] = metrics
                        result["presentation_cues"] = camera_feedback
                        turn = {
                            "question": question_text,
                            "category": category,
                            "answer": answer,
                            "answer_mode": "voice" if voice_transcript else "text",
                            "voice_transcript": voice_transcript,
                            "feedback": result,
                            "timestamp": datetime.now().isoformat(timespec="seconds"),
                            "elapsed_seconds": round(elapsed_now, 1),
                            "strategy": st.session_state.last_plan or {},
                        }
                        st.session_state.turns.append(turn)
                        save_session(st.session_state.session_id, target_role, "Not specified", st.session_state.turns)

                        elapsed_after, remaining_after, expired_after = duration_state(st.session_state.started_at, st.session_state.session_duration)
                        if expired_after:
                            st.session_state.question = None
                            st.session_state.session_complete = True
                        else:
                            strategy = StrategyAgent()
                            target_count = question_target(st.session_state.session_duration, elapsed_after, len(st.session_state.turns))
                            plan = strategy.plan(
                                st.session_state.turns, mode, duration_label, st.session_state.evidence,
                                categories=st.session_state.categories, remaining_minutes=round(remaining_after/60,1),
                                target_questions=target_count
                            )
                            st.session_state.last_plan = plan
                            interviewer = InterviewerAgent(gateway)
                            try:
                                st.session_state.question = interviewer.ask_question(
                                    st.session_state.evidence, st.session_state.research, plan,
                                    target_role, "Not specified", mode, company=company
                                )
                            except Exception:
                                st.session_state.question = None
                                st.session_state.session_complete = True
                                st.warning("The answer was saved, but the next adaptive question could not be generated. The session report is still available.")
                        st.rerun()
                    except Exception:
                        st.error("Coaching failed for this turn. The app kept your evidence state; retry the answer or end the session.")

# ---------------------------- Latest feedback + report ----------------------------
if st.session_state.turns:
    latest = st.session_state.turns[-1]["feedback"]
    st.markdown('<div class="panel"><div class="panel-title">AI Feedback • 6-D Evaluation</div>', unsafe_allow_html=True)
    cols = st.columns(7)
    keys = ["technical", "relevance", "evidence", "communication", "structure", "confidence"]
    labels = ["Technical", "Relevance", "Evidence", "Communication", "Structure", "Confidence"]
    for col, key, label in zip(cols[:6], keys, labels):
        col.metric(label, latest.get("scores", {}).get(key, 0))
    cols[6].metric("Overall", latest.get("overall", 0))
    st.markdown('<div class="panel" style="margin-top:8px">', unsafe_allow_html=True)
    f1, f2 = st.columns(2)
    with f1:
        st.markdown("**Strengths**")
        for x in latest.get("strengths", [])[:5]:
            st.markdown(f'<div class="feedback-item">✓ {escape(x)}</div>', unsafe_allow_html=True)
        st.markdown("**Missing / improve**")
        for x in latest.get("missing_points", [])[:5]:
            st.markdown(f'<div class="feedback-item">△ {escape(x)}</div>', unsafe_allow_html=True)
    with f2:
        st.markdown("**Verification notes**")
        for x in latest.get("verification_notes", [])[:5]:
            st.markdown(f'<div class="feedback-item">⌁ {escape(x)}</div>', unsafe_allow_html=True)
        st.markdown("**Suggested better practice answer**")
        st.markdown(f'<div class="feedback-item">{escape(latest.get("practice_answer",""))}</div>', unsafe_allow_html=True)
        st.markdown("**Next improvement**")
        st.markdown(f'<div class="feedback-item">{escape(latest.get("next_improvement",""))}</div>', unsafe_allow_html=True)
    st.markdown('</div></div>', unsafe_allow_html=True)

    if st.session_state.started and st.button("⏹ END SESSION & FINALIZE PROFESSIONAL REPORT", use_container_width=True):
        st.session_state.question = None
        st.session_state.started = False
        st.session_state.session_complete = True
        st.rerun()

    st.markdown('<div class="panel"><div class="panel-title">Final Session Intelligence</div>', unsafe_allow_html=True)
    category_scores = defaultdict(list)
    for t in st.session_state.turns:
        category_scores[t.get("category", "General")].append(t.get("feedback", {}).get("overall", 0))
    if category_scores:
        readiness = st.columns(min(4, len(category_scores)))
        for i, (cat, vals) in enumerate(category_scores.items()):
            readiness[i % len(readiness)].metric(cat.split(" ")[0], round(sum(vals)/len(vals)))
    st.markdown("**Report coverage**")
    st.caption("Every configured session input and every generated output is captured, including Speech analytics when voice is used: profile, mode, duration, categories, evidence/ATS, research, question, answer, score dimensions, strengths, missing points, verification notes, better answer, next improvement, speech metrics and presentation cues.")
    st.markdown('</div>', unsafe_allow_html=True)

    md = build_markdown_report(
        target_role=target_role,
        industry="Not specified — grounded in CV/JD and role context",
        mode=mode,
        turns=st.session_state.turns,
        evidence=st.session_state.evidence,
        duration_minutes=st.session_state.session_duration,
        question_mode=st.session_state.question_mode,
        answer_mode=st.session_state.answer_mode,
        categories=st.session_state.categories,
        company=company,
        research=st.session_state.research,
        model=st.session_state.groq_model or "Automatic model discovery",
        session_id=st.session_state.session_id,
        started_at=st.session_state.started_at,
    )
    pdf = build_pdf_report(
        target_role=target_role,
        industry="Not specified — grounded in CV/JD and role context",
        mode=mode,
        turns=st.session_state.turns,
        evidence=st.session_state.evidence,
        duration_minutes=st.session_state.session_duration,
        question_mode=st.session_state.question_mode,
        answer_mode=st.session_state.answer_mode,
        categories=st.session_state.categories,
        company=company,
        research=st.session_state.research,
        model=st.session_state.groq_model or "Automatic model discovery",
        session_id=st.session_state.session_id,
        started_at=st.session_state.started_at,
    )
    r1, r2 = st.columns(2)
    r1.download_button("⬇ Download complete Markdown report", md, file_name="intervia_premium_session_report.md", mime="text/markdown", use_container_width=True)
    r2.download_button("⬇ Download complete PDF report", pdf, file_name="intervia_premium_session_report.pdf", mime="application/pdf", use_container_width=True)

st.markdown('<div class="footer">INTERVIA • Evidence-grounded interview practice • ATS readiness heuristic • 5 logical agents • Voice + text • Professional session reporting</div>', unsafe_allow_html=True)
