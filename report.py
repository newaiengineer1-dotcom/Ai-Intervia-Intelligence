import html
import io
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from utils import average_scores


def build_markdown_report(target_role, industry, mode, turns, evidence):
    scores = average_scores([t.get("feedback", {}).get("scores", {}) for t in turns])
    overall = round(sum(scores.values()) / len(scores)) if scores else 0
    lines = [
        "# Intervia Interview Report",
        f"Generated: {datetime.utcnow().isoformat(timespec='seconds')} UTC",
        f"Role: {target_role}",
        f"Mode: {mode}",
        f"Overall average: {overall}/100",
        "",
        "## Average scores",
    ]
    for k, v in scores.items():
        lines.append(f"- {k.title()}: {v}/100")
    lines += ["", "## Grounding"]
    lines.append("Candidate evidence was kept separate from JD requirements and external research.")
    for i, turn in enumerate(turns, 1):
        fb = turn.get("feedback", {})
        lines += ["", f"## Question {i}", turn.get("question", ""), "", "### Candidate answer", turn.get("answer", ""), "", "### Coaching"]
        lines.append(f"Overall: {fb.get('overall', 0)}/100")
        lines.append(f"Strengths: {', '.join(fb.get('strengths', []))}")
        lines.append(f"Missing points: {', '.join(fb.get('missing_points', []))}")
        lines.append(f"Practice answer: {fb.get('practice_answer', '')}")
        lines.append(f"Next improvement: {fb.get('next_improvement', '')}")
    return "\n".join(lines)


def build_pdf_report(target_role, industry, mode, turns, evidence):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    story = [Paragraph("Intervia Interview Report", styles["Title"]), Spacer(1, 8)]
    story.append(Paragraph(html.escape(f"Role: {target_role} | Mode: {mode}"), styles["BodyText"]))
    story.append(Spacer(1, 10))
    scores = average_scores([t.get("feedback", {}).get("scores", {}) for t in turns])
    story.append(Paragraph("Average scores", styles["Heading2"]))
    story.append(Paragraph(html.escape(" | ".join(f"{k.title()}: {v}/100" for k, v in scores.items())), styles["BodyText"]))
    story.append(Spacer(1, 10))
    for i, turn in enumerate(turns, 1):
        fb = turn.get("feedback", {})
        story.append(Paragraph(f"Question {i}", styles["Heading2"]))
        for label, value in [
            ("Question", turn.get("question", "")),
            ("Candidate answer", turn.get("answer", "")),
            ("Coaching", fb.get("practice_answer", "")),
            ("Next improvement", fb.get("next_improvement", "")),
        ]:
            story.append(Paragraph(html.escape(f"{label}: {value}"), styles["BodyText"]))
            story.append(Spacer(1, 6))
    doc.build(story)
    return buf.getvalue()
