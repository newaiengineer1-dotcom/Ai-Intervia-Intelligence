# Intervia — Interview Intelligence

Ultra-premium, evidence-grounded Streamlit interview practice platform with a modular multi-agent architecture and automatic Groq model discovery.

## What changed in this release

- **One professional Interview Design tab:** `Interview categories and Interview mode`.
- **Industry UI removed:** there is no Industry input/tab in the dashboard. Role/JD context is used internally without asking the user for a separate industry field.
- **Automatic Groq model discovery:** the app calls the Groq model-list endpoint for the supplied API key and selects an accessible chat model before interview generation.
- **New Interview Session:** a dedicated reset tab and dashboard reset action clear the active interview, evidence, uploads, answers, timer and adaptive question while preserving the Groq API key and deployment.
- **Modular agents:** each major agent has its own file under `agent_modules/`.
- **Backward compatibility:** `agents.py` remains as a small facade, so existing `from agents import ...` imports continue to work.
- **Premium dark dashboard:** high-contrast typography, glass panels, stronger controls, visible agent statuses, and clearer session design.
- **Clean user-facing errors:** raw Python/Groq exceptions are not printed into the dashboard.
- **Voice + text interview:** browser question playback plus Groq Whisper transcription.
- **Adaptive pacing:** target question count changes according to session duration and answer pace.

## Project structure

```text
Intervia_Interview_Intelligence/
├── app.py
├── agents.py                         # compatibility facade
├── agent_modules/
│   ├── __init__.py
│   ├── groq_gateway.py              # Groq client + model discovery
│   ├── evidence_agent.py            # CV/JD grounding
│   ├── research_agent.py            # optional role/company context
│   ├── strategy_agent.py            # deterministic adaptive strategy
│   ├── interviewer_agent.py         # question generation
│   └── coach_agent.py               # answer evaluation
├── db.py
├── rag.py
├── report.py
├── utils.py
├── crew_adapter.py
├── requirements.txt
├── requirements-dev.txt
├── runtime.txt
├── verify_project.py
├── tests/
├── sample_data/
├── docs/
├── .streamlit/
└── MASTER_PROMPT.md
```

## Core interview controls

### Interview categories and Interview mode

The single setup tab contains:

- Mixed
- Technical
- Behavioral
- Case / Situational
- HR / Screening
- Leadership

Categories:

- Behavioral & Situational 🎭
- Technical & Role-Specific 💻
- HR & Screening Basics 🤝
- Leadership & Management 👔
- Case & Analytical Interviews 📊
- Competency & Skill-Based 🧠
- Reverse Interviewing — Questions for the Employer 🔍

## Groq model behavior

Intervia does not permanently assume `openai/gpt-oss-120b` is available.

The gateway first asks Groq for the models visible to the supplied API key. It then selects an accessible chat model from the configured preference order. If model discovery is temporarily unavailable, the gateway still attempts the configured fallback sequence and converts API failures into friendly UI messages.

The selected model is shown in the Agent Cockpit after the interview session is initialized.

## Secrets

Streamlit Cloud → **Manage app → Settings → Secrets**:

```toml
GROQ_API_KEY = "gsk_your_key_here"
GROQ_LLM_MODEL = ""
GROQ_WHISPER_MODEL = "whisper-large-v3-turbo"
```

Leave `GROQ_LLM_MODEL` empty for automatic selection.

Never commit a real API key to GitHub.

## Local setup

Python runtime target:

```text
Python 3.12
```

Install:

```bash
pip install -r requirements.txt
streamlit run app.py
```

Windows PowerShell:

```powershell
$env:GROQ_API_KEY="gsk_your_key_here"
streamlit run app.py
```

## Validation

Run:

```bash
python verify_project.py
```

The verifier checks:

- Python compilation of all application modules
- modular agent files
- combined Interview categories + Interview mode tab
- all seven categories
- absence of an Industry input in `app.py`
- absence of raw `st.code(str(exc))` dashboard error rendering
- text and voice answer modes
- audio question mode
- Whisper transcription integration
- adaptive pacing
- automatic Groq model discovery

## Important runtime note

Static validation cannot prove that a particular Groq key will receive access to a particular model. Groq project permissions, quotas, network access, and API availability are runtime conditions. The application therefore discovers available models and presents a friendly error instead of exposing raw API traces.
