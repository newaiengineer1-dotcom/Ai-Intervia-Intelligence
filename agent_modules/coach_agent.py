import json
from typing import Any

from utils import safe_clamp
from agent_modules.groq_gateway import GroqGateway


class CoachAgent:
    def __init__(self, gateway: GroqGateway):
        self.gateway = gateway

    def evaluate(self, question: str, answer: str, evidence: dict, target_role: str, mode: str, answer_length: str) -> dict[str, Any]:
        length_map = {"Short": "60-90", "Standard": "100-150", "Detailed": "140-180"}
        system = (
            "You are a strict but constructive interview coach. Evaluate only what is supported by the answer and candidate evidence. "
            "Do not invent employers, projects, technologies, dates, metrics, titles, certifications or responsibilities. Return valid JSON."
        )
        user = f"""
Role: {target_role}
Mode: {mode}
Question: {safe_clamp(question, 2500)}
Candidate answer: {safe_clamp(answer, 5000)}
Candidate evidence only: {safe_clamp(json.dumps(evidence.get('candidate_facts', []), ensure_ascii=False), 5000)}
JD requirements: {safe_clamp(json.dumps(evidence.get('jd_requirements', []), ensure_ascii=False), 3500)}

Return JSON with scores 0-100:
{{
  "scores": {{"technical":0,"relevance":0,"evidence":0,"communication":0,"structure":0,"confidence":0}},
  "overall": 0,
  "strengths": [],
  "missing_points": [],
  "verification_notes": [],
  "practice_answer": "{length_map.get(answer_length, '100-150')} words; improve structure without adding unsupported facts",
  "next_improvement": ""
}}
"""
        result = self.gateway.chat_json(system, user, max_tokens=900)
        scores = result.get("scores", {})
        keys = ["technical", "relevance", "evidence", "communication", "structure", "confidence"]
        for key in keys:
            try:
                scores[key] = max(0, min(100, int(scores.get(key, 0))))
            except (TypeError, ValueError):
                scores[key] = 0
        result["scores"] = scores
        try:
            overall = int(result.get("overall", round(sum(scores.values()) / len(scores))))
        except (TypeError, ValueError):
            overall = round(sum(scores.values()) / len(scores))
        result["overall"] = max(0, min(100, overall))
        return result
