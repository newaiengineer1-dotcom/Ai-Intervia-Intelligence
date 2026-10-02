# Intervia Verification Report — 2026-10-02

## Static validation completed

The following checks were executed successfully in the available build environment:

- `python -m py_compile` for `app.py`, `agents.py`, all `agent_modules/*.py`, `db.py`, `rag.py`, `report.py`, `utils.py`, and `crew_adapter.py`.
- AST parsing of all application Python modules through `verify_project.py`.
- Core deterministic regression checks for `EvidenceAgent`, `StrategyAgent`, `average_scores`, and `safe_clamp`.
- Verification of the `Interview categories and Interview mode` setup tab plus the dedicated `New Interview Session` reset tab.
- Verification that all seven interview categories remain present.
- Verification that there is no `st.text_input("Industry"` UI control.
- Verification that raw `st.code(str(exc))` dashboard rendering is absent.
- Verification of text/audio question and typed/spoken answer controls.
- Verification of Whisper transcription integration.
- Verification of adaptive question targeting.
- Verification that the modular Groq gateway contains `models.list()` automatic model discovery.
- Verification that the legacy `from agents import ...` facade remains available.
- Verification that the dashboard reset action preserves the API-key state while clearing active interview state.
- `PYTHONPATH=. pytest -q` completed successfully: 4 tests passed.

## Runtime limitation

The build sandbox did not have outbound package-network access, so a fresh installation of the pinned third-party requirements could not be completed here. Existing installed packages were therefore not used to claim a complete Streamlit/Groq runtime execution test.

Groq API behavior also depends on the actual API key, Groq project permissions, quota, and deployment network. Those cannot be truthfully marked as validated without executing the deployed application with a real key.

Therefore this report claims **static/code-level validation plus deterministic regression validation**, not a guarantee that every external API key or Streamlit Cloud environment will succeed.

## Expected first deployment check

After Streamlit Cloud deployment:

1. Add `GROQ_API_KEY` in Streamlit Secrets.
2. Leave `GROQ_LLM_MODEL` empty for automatic selection.
3. Enter/select the interview setup.
4. Build the evidence pack.
5. Start an interview.
6. Confirm the Agent Cockpit displays the selected Groq model.
7. Confirm Question 1 is generated.
8. Test one typed answer and one voice answer.
9. Confirm no raw 401/403/429 traceback appears in the UI.
