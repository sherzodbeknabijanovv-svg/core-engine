"""
Roadmap'ni PDF holida (ingliz tilida, AQSH universitet standartlariga
mos, aniq va professional formatda) yaratadi.
"""
from __future__ import annotations

import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

from app.models.schemas import RoadmapOut


def build_roadmap_pdf(roadmap: RoadmapOut) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=LETTER,
        topMargin=0.75 * inch, bottomMargin=0.75 * inch,
        leftMargin=0.75 * inch, rightMargin=0.75 * inch,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("TitleCustom", parent=styles["Title"], textColor=colors.HexColor("#1e293b"))
    h2 = ParagraphStyle("H2Custom", parent=styles["Heading2"], textColor=colors.HexColor("#4338ca"), spaceBefore=14)
    body = styles["BodyText"]

    elements = [
        Paragraph("EduStimul — Personalized Learning Roadmap", title_style),
        Spacer(1, 4),
        Paragraph(f"Generated: {roadmap.generated_at.strftime('%B %d, %Y %H:%M UTC')}", body),
        Spacer(1, 12),
        Paragraph(f"Overall Level: <b>{roadmap.overall_level.value}</b> &nbsp;&nbsp; Overall Score: <b>{roadmap.overall_score_percent}%</b>", body),
        Spacer(1, 6),
        Paragraph(roadmap.summary, body),
    ]

    elements.append(Paragraph("Section Scores", h2))
    score_rows = [["Section", "Score"]]
    for section, score in roadmap.section_scores.items():
        score_rows.append([section, f"{score}%"])
    if roadmap.essay_score is not None:
        score_rows.append(["Essay Writing", f"{roadmap.essay_score}%"])
    score_table = Table(score_rows, colWidths=[3.5 * inch, 1.5 * inch])
    score_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef2ff")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#3730a3")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(score_table)

    if roadmap.weak_areas:
        elements.append(Paragraph("Areas Needing Attention", h2))
        items = [ListItem(Paragraph(f"<b>{w.section}</b> ({w.score_percent}%) — {w.note}", body)) for w in roadmap.weak_areas]
        elements.append(ListFlowable(items, bulletType="bullet"))

    elements.append(Paragraph(f"Weekly Study Plan ({roadmap.daily_study_minutes} minutes / day)", h2))
    for day in roadmap.weekly_plan:
        elements.append(Paragraph(f"<b>{day.day_label} — {day.focus}</b> ({day.duration_minutes} min)", body))
        task_items = [ListItem(Paragraph(t, body)) for t in day.tasks]
        elements.append(ListFlowable(task_items, bulletType="bullet", leftIndent=16))
        elements.append(Spacer(1, 6))

    doc.build(elements)
    return buffer.getvalue()
