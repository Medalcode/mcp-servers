import os
import json

import fitz

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image as RLImage,
)
from reportlab.lib import colors


class PDFGenerator:
    def report(self, title: str, content: str, output: str) -> dict:
        os.makedirs(os.path.dirname(output) or ".", exist_ok=True)
        doc = SimpleDocTemplate(output, pagesize=A4,
                                rightMargin=20*mm, leftMargin=20*mm,
                                topMargin=20*mm, bottomMargin=20*mm)
        styles = getSampleStyleSheet()
        story = []

        story.append(Paragraph(title, styles["Title"]))
        story.append(Spacer(1, 12))

        data = json.loads(content) if isinstance(content, str) else content

        if isinstance(data, list):
            for item in data:
                self._add_item(item, story, styles)
        elif isinstance(data, dict):
            for key, value in data.items():
                story.append(Paragraph(f"<b>{key}</b>", styles["Heading2"]))
                story.append(Spacer(1, 6))
                if isinstance(value, list) and value and isinstance(value[0], dict):
                    self._add_table(value, story, styles)
                elif isinstance(value, list):
                    for v in value:
                        story.append(Paragraph(f"• {v}", styles["Normal"]))
                else:
                    story.append(Paragraph(str(value), styles["Normal"]))
                story.append(Spacer(1, 12))

        doc.build(story)
        return {
            "output": output,
            "title": title,
            "pages": self._count_pages(output),
        }

    def table_report(self, title: str, headers: list[str], rows: list[list[str]], output: str) -> dict:
        os.makedirs(os.path.dirname(output) or ".", exist_ok=True)
        doc = SimpleDocTemplate(output, pagesize=A4,
                                rightMargin=20*mm, leftMargin=20*mm,
                                topMargin=20*mm, bottomMargin=20*mm)
        styles = getSampleStyleSheet()
        story = [
            Paragraph(title, styles["Title"]),
            Spacer(1, 12),
        ]
        table_data = [headers] + rows
        table = Table(table_data, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), HexColor("#2563eb")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 10),
            ("FONTSIZE", (0, 1), (-1, -1), 9),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#cbd5e1")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, HexColor("#f8fafc")]),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(table)
        doc.build(story)
        return {
            "output": output,
            "title": title,
            "rows": len(rows),
            "cols": len(headers),
            "pages": self._count_pages(output),
        }

    def text_to_pdf(self, text: str, output: str, title: str = "") -> dict:
        os.makedirs(os.path.dirname(output) or ".", exist_ok=True)
        doc = SimpleDocTemplate(output, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []
        if title:
            story.append(Paragraph(title, styles["Title"]))
            story.append(Spacer(1, 12))
        for line in text.split("\n"):
            if line.strip() == "":
                story.append(Spacer(1, 6))
            elif line.startswith("# "):
                story.append(Paragraph(line[2:], styles["Heading1"]))
            elif line.startswith("## "):
                story.append(Paragraph(line[3:], styles["Heading2"]))
            elif line.startswith("### "):
                story.append(Paragraph(line[4:], styles["Heading3"]))
            else:
                story.append(Paragraph(line, styles["Normal"]))
        doc.build(story)
        return {
            "output": output,
            "title": title or "Document",
            "pages": self._count_pages(output),
        }

    def _add_item(self, item, story, styles):
        if isinstance(item, dict):
            for k, v in item.items():
                story.append(Paragraph(f"<b>{k}:</b> {v}", styles["Normal"]))
            story.append(Spacer(1, 8))
        else:
            story.append(Paragraph(f"• {item}", styles["Normal"]))

    def _add_table(self, data, story, styles):
        if not data:
            return
        headers = list(data[0].keys())
        rows = [[str(row.get(h, "")) for h in headers] for row in data]
        table_data = [headers] + rows
        table = Table(table_data, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), HexColor("#2563eb")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#cbd5e1")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(table)
        story.append(Spacer(1, 12))

    def _count_pages(self, path: str) -> int:
        try:
            doc = fitz.open(path)
            n = len(doc)
            doc.close()
            return n
        except Exception:
            return 0
