"""Optional CrewAI adapter. The core product does not require CrewAI."""


def crewai_available() -> bool:
    try:
        import crewai  # noqa: F401
        return True
    except ImportError:
        return False


def architecture_note() -> str:
    return (
        "CrewAI is intentionally optional. Use the native lightweight orchestrator for the MVP; "
        "add CrewAI only when task delegation, traces, or larger multi-agent workflows justify it."
    )
