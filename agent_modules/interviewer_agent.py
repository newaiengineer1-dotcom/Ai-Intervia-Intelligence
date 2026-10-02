import json

from utils import safe_clamp
from agent_modules.groq_gateway import GroqGateway


class InterviewerAgent:
    def __init__(self, gateway: GroqGateway):
        self.gateway = gateway

    def ask(self, evidence: dict, research: dict | None, plan: dict, target_role: str, industry: str, mode: str, company: str = "") -> str:
        system = (
            "You are a realistic human interviewer. Ask exactly ONE concise question. "
            "Ground it in the target role, JD requirements and candidate evidence. "
            "Never state an unsupported candidate fact. Prefer practical questions with clear evaluation signals."
        )
        user = f"""
Target role: {target_role}
Mode: {mode}
Company: {company or 'Not specified'}
Role context: {industry}
Allowed categories: {safe_clamp(json.dumps(plan.get('categories', []), ensure_ascii=False), 1800)}
Strategy focus: {plan['focus']}
Remaining time: {plan.get('remaining_minutes', 'unknown')} minutes
Target question count: {plan.get('target_questions', 'adaptive')}
Candidate evidence: {safe_clamp(json.dumps(evidence.get('candidate_facts', []), ensure_ascii=False), 4500)}
JD requirements: {safe_clamp(json.dumps(evidence.get('jd_requirements', []), ensure_ascii=False), 3500)}
External role context: {safe_clamp(json.dumps(research or {}, ensure_ascii=False), 1800)}

Choose one useful category and ask exactly one realistic interview question. Return only the question text.
"""
        return self.gateway.chat_text(system, user, max_tokens=180)

    def ask_question(self, evidence: dict, research: dict | None, plan: dict, target_role: str, industry: str, mode: str, company: str = "") -> str:
        return self.ask(evidence, research, plan, target_role, industry, mode, company=company)
