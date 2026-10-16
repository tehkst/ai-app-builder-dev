"""Health Check reports: Markdown (Mission Control, email) and a client-ready PDF.

Plain English for a business owner first, details after. The PDF needs `reportlab` (BSD licence).
Secrets never appear: results only carry their file, line and kind.
"""
from __future__ import annotations

from typing import Any, Dict, List

SEVERITY_LABEL = {"high": "High", "medium": "Medium", "low": "Low"}


def _stack_line(result: Dict[str, Any]) -> str:
    stack = result["stack"]
    parts = stack.get("frameworks") or stack.get("languages") or ["Unknown"]
    extras = stack.get("databases", []) + stack.get("containers", [])
    return ", ".join(parts + extras)


def render_markdown(result: Dict[str, Any]) -> str:
    o = result["overall"]
    lines = [
        f"# Codebase Health Check: {result['project']}",
        "",
        f"**Overall: {o['grade']} ({o['score']}/100)** · {_stack_line(result)} · "
        f"{result['size']['lines']:,} lines in {result['size']['files']} files · checked {result['checked_at'][:10]}",
        "",
        "## Scores",
        "",
        "| Area | Score | Grade |",
        "|---|---|---|",
    ]
    lines += [f"| {a['title']} | {a['score']} | {a['grade']} |" for a in result["areas"]]
    lines += ["", "## Top risks", ""]
    if result["top_risks"]:
        lines += [f"{i}. **{r['title']}** ({SEVERITY_LABEL[r['severity']]}, {r['area']}): {r['detail']}"
                  for i, r in enumerate(result["top_risks"], 1)]
    else:
        lines.append("No significant risks found by the automated checks.")
    if result["next_steps"]:
        lines += ["", "## What we'd do next", ""] + [f"- {step}" for step in result["next_steps"]]
    security = next(a for a in result["areas"] if a["key"] == "security")
    if security["data"]["count"]:
        lines += ["", "## Where the possible secrets are (values not shown)", ""]
        lines += [f"- `{h['file']}`{':' + str(h['line']) if h['line'] else ''}: {h['kind']}" for h in security["data"]["locations"]]
    lines += ["", "---", "", result["method"] + " This automated Health Check is the first step of a full Audit, "
              "which reviews the code by hand and produces a prioritised fix plan."]
    return "\n".join(lines) + "\n"


def render_pdf(result: Dict[str, Any], out_path: str) -> str:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    from html import escape

    base = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=base["Heading1"], fontSize=20, textColor=colors.HexColor("#1D4ED8"), spaceAfter=4)
    h2 = ParagraphStyle("h2", parent=base["Heading2"], fontSize=13, spaceBefore=10, spaceAfter=5)
    body = ParagraphStyle("body", parent=base["BodyText"], fontSize=10, leading=14)
    small = ParagraphStyle("small", parent=body, fontSize=8.5, leading=11, textColor=colors.HexColor("#4B5563"))
    tone = {"A": "#16A34A", "B": "#65A30D", "C": "#CA8A04", "D": "#EA580C", "F": "#DC2626"}
    o = result["overall"]
    story: List[Any] = [
        Paragraph(f"Codebase Health Check: {escape(result['project'])}", h1),
        Paragraph(f"{escape(_stack_line(result))} · {result['size']['lines']:,} lines in {result['size']['files']} files · "
                  f"checked {result['checked_at'][:10]}", small),
        Spacer(1, 10),
        Paragraph(f"<font size=28 color='{tone[o['grade']]}'><b>{o['grade']}</b></font>&nbsp;&nbsp;"
                  f"<font size=12>Overall score {o['score']}/100</font>", ParagraphStyle("grade", parent=body, leading=34)),
        Spacer(1, 12),
    ]
    rows = [["Area", "Score", "Grade"]] + [[a["title"], str(a["score"]), a["grade"]] for a in result["areas"]]
    table = Table(rows, colWidths=[95 * mm, 30 * mm, 30 * mm])
    style = [("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D1D5DB")), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E5E7EB")),
             ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 10)]
    for i, a in enumerate(result["areas"], 1):
        style.append(("TEXTCOLOR", (2, i), (2, i), colors.HexColor(tone[a["grade"]])))
    table.setStyle(TableStyle(style))
    story += [table, Paragraph("Top risks", h2)]
    if result["top_risks"]:
        for i, r in enumerate(result["top_risks"], 1):
            story.append(Paragraph(f"<b>{i}. {escape(r['title'])}</b> ({SEVERITY_LABEL[r['severity']]}, {escape(r['area'])})<br/>"
                                   f"{escape(r['detail'])}", body))
            story.append(Spacer(1, 4))
    else:
        story.append(Paragraph("No significant risks found by the automated checks.", body))
    if result["next_steps"]:
        story.append(Paragraph("What we'd do next", h2))
        story += [Paragraph(f"• {escape(step)}", body) for step in result["next_steps"]]
    security = next(a for a in result["areas"] if a["key"] == "security")
    if security["data"]["count"]:
        story.append(Paragraph("Where the possible secrets are (values not shown)", h2))
        story += [Paragraph(f"• {escape(h['file'])}{':' + str(h['line']) if h['line'] else ''}: {escape(h['kind'])}", small)
                  for h in security["data"]["locations"][:20]]
    story += [Spacer(1, 14), Paragraph(escape(result["method"]) + " This automated Health Check is the first step of a full "
                                       "Audit, which reviews the code by hand and produces a prioritised fix plan.", small)]
    doc = SimpleDocTemplate(out_path, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=18 * mm,
                            bottomMargin=18 * mm, title=f"Codebase Health Check: {result['project']}")
    doc.build(story)
    return out_path
