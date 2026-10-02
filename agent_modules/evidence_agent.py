import re
from typing import Any


class EvidenceAgent:
    """Builds deterministic, source-separated CV/JD evidence."""

    STOP = {
        "and", "the", "with", "for", "from", "this", "that", "have", "will", "your", "you",
        "are", "our", "their", "into", "using", "years", "role", "work", "team", "job", "about",
    }

    def _sentences(self, text: str) -> list[str]:
        return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text or "") if len(s.strip()) > 20]

    def _terms(self, text: str) -> set[str]:
        return {
            x.lower()
            for x in re.findall(r"[A-Za-z][A-Za-z0-9+#.-]{2,}", text or "")
            if x.lower() not in self.STOP
        }

    def build(self, cv_text: str, jd_text: str, target_role: str, industry: str = "Not specified") -> dict[str, Any]:
        cv_sentences = self._sentences(cv_text)
        jd_sentences = self._sentences(jd_text)
        cv_terms = self._terms(cv_text)
        jd_terms = self._terms(jd_text)
        return {
            "target_role": target_role,
            "industry": industry,
            "candidate_facts": cv_sentences[:80],
            "jd_requirements": jd_sentences[:80],
            "candidate_terms": sorted(cv_terms)[:250],
            "jd_terms": sorted(jd_terms)[:250],
            "matches": sorted(cv_terms & jd_terms)[:80],
            "gaps": sorted(jd_terms - cv_terms)[:80],
            "grounding_rule": "Candidate facts come only from the CV. JD requirements and research are never candidate facts.",
        }
