from agents import EvidenceAgent, StrategyAgent
from utils import average_scores, safe_clamp


def test_evidence_separation():
    e = EvidenceAgent().build("I designed solar PV layouts.", "Experience with BESS is preferred.", "Engineer", "Energy")
    assert any("solar" in x.lower() for x in e["candidate_facts"])
    assert any("bess" in x.lower() for x in e["jd_requirements"])


def test_score_average():
    a = average_scores([{"technical": 80, "relevance": 60, "evidence": 70, "communication": 90, "structure": 80, "confidence": 70}])
    assert a["technical"] == 80


def test_clamp():
    assert len(safe_clamp("x" * 100, 10)) <= 50


def test_strategy_with_categories_and_time():
    plan = StrategyAgent().plan([], "Mixed", "30 Minutes", {}, categories=["Behavioral & Situational 🎭"], remaining_minutes=29.5, target_questions=8)
    assert plan["focus"]
    assert plan["categories"] == ["Behavioral & Situational 🎭"]
    assert plan["target_questions"] == 8
