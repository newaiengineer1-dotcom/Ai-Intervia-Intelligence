import os
import re
from typing import Any

from utils import safe_clamp

PRIMARY_MODELS = (
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
)
WHISPER_MODEL = "whisper-large-v3-turbo"


def parse_json(text: str) -> dict:
    import json

    cleaned = (text or "").strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.I)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, flags=re.S)
        if not match:
            raise
        return json.loads(match.group(0))


class GroqGateway:
    """Single Groq client shared by every Intervia agent."""

    def __init__(self, api_key: str):
        try:
            from groq import Groq
        except ImportError as exc:
            raise RuntimeError("Groq library is missing. Install requirements.txt.") from exc

        key = (api_key or "").strip()
        if not key:
            raise RuntimeError("Enter a Groq API key before starting Intervia.")

        self.client = Groq(api_key=key)
        self._available_models: list[str] | None = None
        self._selected_model: str | None = None

    def available_models(self) -> list[str]:
        if self._available_models is not None:
            return self._available_models
        try:
            response = self.client.models.list()
            models = []
            for item in getattr(response, "data", []) or []:
                model_id = getattr(item, "id", None)
                if model_id:
                    models.append(str(model_id))
            self._available_models = models
        except Exception:
            # Discovery failure is handled by chat fallback logic.
            self._available_models = []
        return self._available_models

    def selected_model(self) -> str:
        if self._selected_model:
            return self._selected_model

        configured = os.getenv("GROQ_LLM_MODEL", "").strip()
        visible = set(self.available_models())
        candidates = [configured] if configured else []
        candidates.extend(PRIMARY_MODELS)

        seen = set()
        ordered = []
        for model in candidates:
            if model and model not in seen:
                seen.add(model)
                if not visible or model in visible:
                    ordered.append(model)

        if visible:
            # Prefer a known chat-capable model, then any non-audio model.
            for model in ordered:
                self._selected_model = model
                return model
            for model in sorted(visible):
                low = model.lower()
                if not any(x in low for x in ("whisper", "tts", "guard", "safeguard", "embed")):
                    self._selected_model = model
                    return model

        self._selected_model = ordered[0] if ordered else (configured or PRIMARY_MODELS[0])
        return self._selected_model

    def model_status(self) -> dict[str, Any]:
        models = self.available_models()
        selected = self.selected_model()
        return {
            "selected": selected,
            "discovered": bool(models),
            "count": len(models),
            "models": models,
        }

    @staticmethod
    def friendly_error(exc: Exception) -> str:
        raw = str(exc).lower()
        if "403" in raw or "access denied" in raw or "forbidden" in raw or "permission" in raw:
            return "Groq denied access. Check the API key's project permissions and available models."
        if "401" in raw or "unauthorized" in raw or "invalid api key" in raw:
            return "Groq authentication failed. Check the API key in Intervia or Streamlit Secrets."
        if "429" in raw or "rate limit" in raw or "too many requests" in raw:
            return "Groq rate limit reached. Wait for the quota window or use a shorter answer/session."
        if "network" in raw or "connection" in raw or "timeout" in raw or "dns" in raw:
            return "Groq could not be reached from this environment. Check Streamlit Cloud network access and Groq availability."
        return "Groq could not complete the request. Check the API key and model availability."

    def _chat(self, messages: list[dict[str, str]], max_tokens: int, temperature: float) -> str:
        attempted: list[str] = []
        errors: list[Exception] = []
        visible = set(self.available_models())
        configured = os.getenv("GROQ_LLM_MODEL", "").strip()
        candidates = [configured] if configured else []
        candidates.extend(PRIMARY_MODELS)

        if visible:
            candidates = [m for m in candidates if m in visible]
            if not candidates:
                candidates = [m for m in sorted(visible) if "whisper" not in m.lower()]
        else:
            # If model discovery itself was blocked, still make one normal API attempt.
            candidates = [m for m in candidates if m]

        deduped = []
        for model in candidates:
            if model not in deduped:
                deduped.append(model)

        for model in deduped:
            attempted.append(model)
            try:
                response = self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                self._selected_model = model
                return (response.choices[0].message.content or "").strip()
            except Exception as exc:
                errors.append(exc)

        if errors:
            raise RuntimeError(self.friendly_error(errors[-1])) from errors[-1]
        raise RuntimeError("No accessible Groq chat model was found for this API key.")

    def chat_text(self, system: str, user: str, max_tokens: int = 300) -> str:
        return self._chat(
            [
                {"role": "system", "content": safe_clamp(system, 5000)},
                {"role": "user", "content": safe_clamp(user, 9000)},
            ],
            max_tokens=max_tokens,
            temperature=0.25,
        )

    def chat_json(self, system: str, user: str, max_tokens: int = 900) -> dict:
        text = self._chat(
            [
                {"role": "system", "content": safe_clamp(system, 5000)},
                {"role": "user", "content": safe_clamp(user, 12000)},
            ],
            max_tokens=max_tokens,
            temperature=0.2,
        )
        return parse_json(text)

    def transcribe(self, data: bytes, filename: str = "answer.wav") -> str:
        try:
            result = self.client.audio.transcriptions.create(
                file=(filename or "answer.wav", data),
                model=os.getenv("GROQ_WHISPER_MODEL", WHISPER_MODEL),
                response_format="text",
            )
            return result if isinstance(result, str) else str(getattr(result, "text", result)).strip()
        except Exception as exc:
            raise RuntimeError(self.friendly_error(exc)) from exc

    def analyze_camera(self, data: bytes, mime_type: str = "image/jpeg") -> dict[str, Any]:
        return {
            "available": False,
            "captured": bool(data),
            "mime_type": mime_type,
            "message": "Camera snapshot captured. Automated personality or emotion inference is disabled.",
        }
