from typing import Any

from utils import safe_clamp
from agent_modules.groq_gateway import GroqGateway


class ResearchAgent:
    """Optional role/company context agent; it never creates candidate evidence."""

    def __init__(self, gateway: GroqGateway):
        self.gateway = gateway

    def run(self, target_role: str, industry: str, jd: str, company: str = "", company_track: str = "") -> dict[str, Any]:
        prompt = f"""
Target role: {target_role}
Company: {company or 'Not specified'}
Role context: {industry}
User-provided company context: {safe_clamp(company_track, 1800)}
Job description:
{safe_clamp(jd, 6000)}

Provide concise interview-preparation context:
- role themes
- likely interview focus areas
- useful technical/business topics
- company-specific preparation only when supported by the supplied company context

Do not invent current company facts. Do not make any candidate claims.
"""
        try:
            summary = self.gateway.chat_text(
                "You are a careful interview research assistant. Separate role/JD context from candidate evidence.",
                prompt,
                max_tokens=650,
            )
            return {"available": True, "summary": summary, "source_class": "role/JD context"}
        except Exception:
            return {"available": False, "summary": "Optional role research is unavailable.", "source_class": "role/JD context"}
