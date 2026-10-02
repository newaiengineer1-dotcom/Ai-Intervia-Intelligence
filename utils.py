import io
import re
from typing import Any


def safe_clamp(text: str, limit: int) -> str:
    text = text or ""
    if len(text) <= limit:
        return text
    return text[:limit] + "\n[context truncated for token safety]"


def extract_uploaded_text(uploaded) -> str:
    name = (uploaded.name or "").lower()
    data = uploaded.getvalue()
    if name.endswith(".pdf"):
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    if name.endswith(".docx"):
        from docx import Document
        doc = Document(io.BytesIO(data))
        return "\n".join(p.text for p in doc.paragraphs)
    return data.decode("utf-8", errors="ignore")


def average_scores(scores_list: list[dict[str, Any]]) -> dict[str, float]:
    keys = ["technical", "relevance", "evidence", "communication", "structure", "confidence"]
    if not scores_list:
        return {k: 0 for k in keys}
    return {k: round(sum(float(s.get(k, 0)) for s in scores_list) / len(scores_list), 1) for k in keys}
