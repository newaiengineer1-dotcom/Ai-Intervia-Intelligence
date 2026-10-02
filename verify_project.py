from pathlib import Path
import ast
import py_compile

ROOT = Path(__file__).parent
FILES = [
    "app.py",
    "agents.py",
    "db.py",
    "rag.py",
    "report.py",
    "utils.py",
    "crew_adapter.py",
    "agent_modules/__init__.py",
    "agent_modules/groq_gateway.py",
    "agent_modules/evidence_agent.py",
    "agent_modules/research_agent.py",
    "agent_modules/strategy_agent.py",
    "agent_modules/interviewer_agent.py",
    "agent_modules/coach_agent.py",
]

for name in FILES:
    path = ROOT / name
    if not path.exists():
        raise SystemExit(f"Missing required file: {name}")
    py_compile.compile(str(path), doraise=True)
    ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

app = (ROOT / "app.py").read_text(encoding="utf-8")
agent_facade = (ROOT / "agents.py").read_text(encoding="utf-8")

checks = {
    "combined_setup_tab": 'Interview categories and Interview mode' in app,
    "new_interview_tab": 'New Interview Session' in app and 'Reset & Start New Interview' in app,
    "seven_categories": "Behavioral & Situational 🎭" in app and "Reverse Interviewing" in app,
    "no_industry_input": 'st.text_input("Industry"' not in app,
    "no_raw_exception_code": "st.code(str(exc)" not in app,
    "no_raw_exception_fstrings": "{exc}" not in app,
    "text_answer_mode": "⌨️ Type Answers" in app,
    "voice_answer_mode": "🎙️ Speak Answers" in app,
    "audio_questions": "Audio Questions" in app,
    "whisper_transcription": "gateway.transcribe" in app,
    "adaptive_target": "question_target" in app,
    "interviewer_facade": "InterviewerAgent" in agent_facade,
    "modular_agents": all((ROOT / "agent_modules" / f).exists() for f in [
        "groq_gateway.py", "evidence_agent.py", "research_agent.py",
        "strategy_agent.py", "interviewer_agent.py", "coach_agent.py"
    ]),
    "automatic_model_discovery": "models.list()" in (ROOT / "agent_modules" / "groq_gateway.py").read_text(encoding="utf-8"),
    "dashboard_reset": "reset_interview_session" in app and 'reset_dashboard_button' in app,
    "reset_preserves_api_key": 'api_key_input' not in app[app.find('def reset_interview_session'):app.find('def configured_secret')],
}
failed = [key for key, ok in checks.items() if not ok]
if failed:
    raise SystemExit("Failed checks: " + ", ".join(failed))

print("PASS: Intervia syntax, modular structure, UI requirements, and model-discovery checks")
