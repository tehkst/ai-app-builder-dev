"""The Audit report for the client (Markdown and PDF): plain-English summary and first steps up
front, then the prioritised fix plan (each fix with evidence, what it would affect and a suggested
price), the map of the app, the Health Check scores and a technical appendix."""
from __future__ import annotations

from html import escape
from typing import Any, Dict, List

from app.platform.clients.audit import counts

SEVERITY = {"critical": "Critical", "high": "High", "medium": "Medium", "low": "Low"}
LEVEL = {"contained": "Contained", "moderate": "Moderate", "wide": "Wide"}
METHOD = ("Prepared by AI Software Factory: an automated, read-only Health Check and dependency map, and a "
          "review of the code by our team with AI assistance. Nothing from your code was run outside an "
          "isolated test environment. Findings marked \"not verified\" could not be confirmed in the files "
          "and should be checked before acting on them. Prices are suggested fixed prices per fix.")


def _evidence(f: Dict[str, Any]) -> str:
    return ", ".join(f"{e['file']}{':' + str(e['line']) if e.get('line') else ''}" for e in f["evidence"]) or "(none given)"


def _reach(f: Dict[str, Any]) -> str:
    c = f["change_impact"]
    if not c.get("found"):
        return "Not mapped (check by hand)."
    pages = ", ".join(c.get("entry_points") or []) or "none found"
    tests = "covered by tests" if not c.get("untested") else "no automated test covers it"
    return (f"{LEVEL.get(c['level'], c['level'])}: {c['affected_count']} other files depend on {c['name']}; "
            f"pages/entry points: {pages}; {tests}.")


def render_markdown(audit: Dict[str, Any], project: str) -> str:
    h, n = audit["health"], counts(audit)
    lines = [f"# Codebase Audit: {project}", "",
             f"Health Check grade **{h['overall']['grade']}** ({h['overall']['score']}/100) · "
             f"{h['size']['lines']:,} lines in {h['size']['files']} files · "
             + ", ".join(f"{n[s]} {SEVERITY[s].lower()}" for s in n if n[s]), "",
             "## In short", "", audit["summary"], "", "## Do these first", ""]
    lines += [f"{i}. {step}" for i, step in enumerate(audit["first_steps"], 1)]
    lines += ["", "## Fix plan", "", "| # | Fix | Severity | Size | Suggested price | Affects |", "|---|---|---|---|---|---|"]
    for i, f in enumerate(audit["findings"], 1):
        reach = f["change_impact"]
        lines.append(f"| {i} | {f['title']}{'' if f['verified'] else ' (not verified)'} | {SEVERITY.get(f['severity'], f['severity'])} | "
                     f"{f['size']} ({f['hours']}) | {f['price']} | "
                     f"{LEVEL.get(reach.get('level'), 'not mapped') if reach.get('found') else 'not mapped'} |")
    for i, f in enumerate(audit["findings"], 1):
        lines += ["", f"### {i}. {f['title']}", "", f"**Why it matters:** {f['impact']}", "",
                  f"**Fix:** {f['fix']}", "", f"**Evidence:** {_evidence(f)}" + ("" if f["verified"] else " _(not verified)_"),
                  "", f"**What the fix would touch:** {_reach(f)}"]
    if audit["map"]:
        lines += ["", "## How the app is put together", ""]
        lines += [f"- **{m['part']}**: {m['purpose']}" + (f" ({', '.join(m['files'][:4])})" if m["files"] else "") for m in audit["map"]]
    lines += ["", "## Health Check scores", "", "| Area | Score | Grade |", "|---|---|---|"]
    lines += [f"| {a['title']} | {a['score']} | {a['grade']} |" for a in h["areas"]]
    if audit["appendix"]:
        lines += ["", "## Technical notes for your developer", "", audit["appendix"]]
    lines += ["", "---", "", METHOD]
    return "\n".join(lines) + "\n"


def render_pdf(audit: Dict[str, Any], project: str, out_path: str) -> str:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    base = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=base["Heading1"], fontSize=20, textColor=colors.HexColor("#1D4ED8"), spaceAfter=4)
    h2 = ParagraphStyle("h2", parent=base["Heading2"], fontSize=13, spaceBefore=10, spaceAfter=5)
    h3 = ParagraphStyle("h3", parent=base["Heading3"], fontSize=11, spaceBefore=8, spaceAfter=3)
    body = ParagraphStyle("body", parent=base["BodyText"], fontSize=10, leading=14)
    small = ParagraphStyle("small", parent=body, fontSize=8.5, leading=11, textColor=colors.HexColor("#4B5563"))
    cell = ParagraphStyle("cell", parent=small, fontSize=8, leading=10, textColor=colors.black)
    tone = {"critical": "#B91C1C", "high": "#DC2626", "medium": "#CA8A04", "low": "#4B5563"}
    h, n = audit["health"], counts(audit)
    story: List[Any] = [
        Paragraph(f"Codebase Audit: {escape(project)}", h1),
        Paragraph(f"Health Check grade {h['overall']['grade']} ({h['overall']['score']}/100) · {h['size']['lines']:,} lines in "
                  f"{h['size']['files']} files · " + escape(", ".join(f"{n[s]} {s}" for s in n if n[s])), small),
        Paragraph("In short", h2), Paragraph(escape(audit["summary"]), body),
        Paragraph("Do these first", h2),
    ]
    story += [Paragraph(f"{i}. {escape(step)}", body) for i, step in enumerate(audit["first_steps"], 1)]
    rows = [["#", "Fix", "Severity", "Size", "Price", "Affects"]]
    for i, f in enumerate(audit["findings"], 1):
        reach = f["change_impact"]
        rows.append([str(i), Paragraph(escape(f["title"]) + ("" if f["verified"] else " <i>(not verified)</i>"), cell),
                     Paragraph(f"<font color='{tone.get(f['severity'], '#000')}'>{SEVERITY.get(f['severity'], f['severity'])}</font>", cell),
                     f["size"], f["price"], LEVEL.get(reach.get("level"), "not mapped") if reach.get("found") else "not mapped"])
    table = Table(rows, colWidths=[8 * mm, 82 * mm, 20 * mm, 12 * mm, 16 * mm, 22 * mm], repeatRows=1)
    table.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D1D5DB")),
                               ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E5E7EB")), ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                               ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story += [Paragraph("Fix plan", h2), table]
    for i, f in enumerate(audit["findings"], 1):
        story.append(KeepTogether([
            Paragraph(f"{i}. {escape(f['title'])}", h3),
            Paragraph(f"<b>Why it matters:</b> {escape(f['impact'])}", body),
            Paragraph(f"<b>Fix:</b> {escape(f['fix'])} <i>({f['size']}, {escape(f['hours'])}, {escape(f['price'])})</i>", body),
            Paragraph(f"<b>Evidence:</b> {escape(_evidence(f))}" + ("" if f["verified"] else " <i>(not verified)</i>"), small),
            Paragraph(f"<b>What the fix would touch:</b> {escape(_reach(f))}", small),
        ]))
    if audit["map"]:
        story.append(Paragraph("How the app is put together", h2))
        story += [Paragraph(f"<b>{escape(m['part'])}</b>: {escape(m['purpose'])}", body) for m in audit["map"]]
    story.append(Paragraph("Health Check scores", h2))
    scores = Table([["Area", "Score", "Grade"]] + [[a["title"], str(a["score"]), a["grade"]] for a in h["areas"]],
                   colWidths=[95 * mm, 30 * mm, 30 * mm])
    scores.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D1D5DB")),
                                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E5E7EB")), ("FONTSIZE", (0, 0), (-1, -1), 9)]))
    story.append(scores)
    if audit["appendix"]:
        story += [Paragraph("Technical notes for your developer", h2)]
        story += [Paragraph(escape(part), small) for part in audit["appendix"].split("\n") if part.strip()]
    story += [Spacer(1, 12), Paragraph(escape(METHOD), small)]
    doc = SimpleDocTemplate(out_path, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=18 * mm,
                            bottomMargin=18 * mm, title=f"Codebase Audit: {project}")
    doc.build(story)
    return out_path
