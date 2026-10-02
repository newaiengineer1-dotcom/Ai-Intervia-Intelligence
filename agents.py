"""Backward-compatible facade for Intervia's modular agent package."""

from agent_modules import (
    CoachAgent,
    EvidenceAgent,
    GroqGateway,
    InterviewerAgent,
    ResearchAgent,
    StrategyAgent,
)

__all__ = [
    "GroqGateway",
    "EvidenceAgent",
    "ResearchAgent",
    "StrategyAgent",
    "InterviewerAgent",
    "CoachAgent",
]
