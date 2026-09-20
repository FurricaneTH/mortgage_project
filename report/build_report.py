#!/usr/bin/env python3
"""Build report.pdf from the lightweight Markdown in report.md."""

from __future__ import annotations

import re
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "report.md"
OUTPUT = ROOT / "report.pdf"
NAVY = colors.HexColor("#18364A")
TEAL = colors.HexColor("#167D8D")
INK = colors.HexColor("#253746")
MUTED = colors.HexColor("#627482")
PALE = colors.HexColor("#EEF4F6")


def inline_markup(text: str) -> str:
    text = escape(text)
    text = re.sub(r"`([^`]+)`", r'<font name="Courier" size="7.5">\1</font>', text)
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)


def table_cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def create_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="ReportTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=22, leading=27, textColor=NAVY, spaceAfter=8, alignment=0))
    styles.add(ParagraphStyle(name="ReportH1", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=15, leading=19, textColor=NAVY, spaceBefore=12, spaceAfter=6, keepWithNext=True))
    styles.add(ParagraphStyle(name="ReportH2", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=11, leading=14, textColor=TEAL, spaceBefore=8, spaceAfter=4, keepWithNext=True))
    styles.add(ParagraphStyle(name="ReportBody", parent=styles["BodyText"], fontName="Helvetica", fontSize=9, leading=12.5, textColor=INK, spaceAfter=6))
    styles.add(ParagraphStyle(name="ReportSmall", parent=styles["BodyText"], fontName="Helvetica", fontSize=7.6, leading=10, textColor=INK))
    styles.add(ParagraphStyle(name="ReportTableHead", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=7.7, leading=9.5, textColor=colors.white))
    styles.add(ParagraphStyle(name="ReportSubtitle", parent=styles["BodyText"], fontName="Helvetica", fontSize=10, leading=14, textColor=MUTED, spaceAfter=12))
    return styles


def build_story(markdown: str, styles) -> list:
    story = []
    lines = markdown.splitlines()
    paragraph: list[str] = []
    index = 0

    def flush_paragraph():
        if paragraph:
            text = " ".join(line.strip() for line in paragraph)
            story.append(Paragraph(inline_markup(text), styles["ReportBody"]))
            paragraph.clear()

    while index < len(lines):
        line = lines[index].rstrip()
        if not line.strip():
            flush_paragraph()
            index += 1
            continue
        if line.startswith("|"):
            flush_paragraph()
            raw_rows = []
            while index < len(lines) and lines[index].lstrip().startswith("|"):
                raw_rows.append(table_cells(lines[index]))
                index += 1
            rows = [
                row for row in raw_rows
                if not all(re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) for cell in row)
            ]
            is_page_table = len(rows[0]) == 3 and rows[0][0] == "PDF pages"
            data = []
            for row_index, row in enumerate(rows):
                style = styles["ReportTableHead"] if row_index == 0 else styles["ReportSmall"]
                data.append([Paragraph(inline_markup(cell), style) for cell in row])
            widths = [55, 185, 272] if is_page_table else [105, 245, 162]
            table = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE]),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CBD7DD")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]))
            story.extend([table, Spacer(1, 8)])
            continue
        if line.startswith("# "):
            flush_paragraph()
            story.append(Paragraph(inline_markup(line[2:]), styles["ReportTitle"]))
        elif line.startswith("## "):
            flush_paragraph()
            story.append(Paragraph(inline_markup(line[3:]), styles["ReportH1"]))
        elif line.startswith("### "):
            flush_paragraph()
            story.append(Paragraph(inline_markup(line[4:]), styles["ReportH2"]))
        elif line.startswith("- "):
            flush_paragraph()
            story.append(Paragraph(inline_markup(line[2:]), styles["ReportBody"], bulletText="-"))
        else:
            paragraph.append(line)
        index += 1
    flush_paragraph()
    return story


def draw_page(canvas, document):
    canvas.saveState()
    width, height = letter
    canvas.setStrokeColor(colors.HexColor("#D7E1E6"))
    canvas.setLineWidth(0.5)
    canvas.line(document.leftMargin, height - 0.42 * inch, width - document.rightMargin, height - 0.42 * inch)
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(MUTED)
    canvas.drawString(document.leftMargin, 0.35 * inch, "AREAL.AI | NLP / LLM Internship Assignment")
    canvas.drawRightString(width - document.rightMargin, 0.35 * inch, f"Page {document.page}")
    canvas.restoreState()


def main() -> None:
    styles = create_styles()
    document = SimpleDocTemplate(
        str(OUTPUT), pagesize=letter, rightMargin=0.55 * inch, leftMargin=0.55 * inch,
        topMargin=0.62 * inch, bottomMargin=0.58 * inch,
        title="Mortgage Document Understanding - Design and Results",
        author="AREAL.AI Internship Assignment",
    )
    story = build_story(SOURCE.read_text(encoding="utf-8"), styles)
    document.build(story, onFirstPage=draw_page, onLaterPages=draw_page)
    print(f"Created {OUTPUT}")


if __name__ == "__main__":
    main()
