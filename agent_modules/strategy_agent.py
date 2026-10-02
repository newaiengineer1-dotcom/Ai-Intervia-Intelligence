from typing import Any

from utils import average_scores


class StrategyAgent:
    """Deterministic adaptive policy; no extra LLM call required."""

    def plan(self, turns: list[dict], mode: str, duration: str, evidence: dict, categories: list[str] | None = None, remaining_minutes: float | None = None, target_questions: int | None = None) -> dict[str, Any]:
        scores = [t["feedback"].get("scores", {}) for t in turns if t.get("feedback")]
        avg = average_scores(scores)
        weakest = min(avg, key=avg.get) if avg else "relevance"
        if not turns:
            focus = "high-signal role-specific baseline"
        elif avg.get("technical", 100) < 60:
            focus = "technical depth and reasoning"
        elif avg.get("evidence", 100) < 60:
            focus = "resume-grounded evidence and ownership"
        elif avg.get("communication", 100) < 60:
            focus = "concise communication and structure"
        elif avg.get("relevance", 100) < 60:
            focus = "directly answering the question"
        else:
            focus = "progressively harder follow-up"
        return {
            "mode": mode,
            "duration": duration,
            "focus": focus,
            "weakest_dimension": weakest,
            "turns_completed": len(turns),
            "categories": categories or ["Technical & Role-Specific 💻"],
            "remaining_minutes": remaining_minutes,
            "target_questions": target_questions,
        }
