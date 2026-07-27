# -*- coding: utf-8 -*-
"""Generate editable and fixed-layout reports from the native report view."""

from __future__ import annotations

import html
import os
import re
from pathlib import Path
from typing import Any

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


DOCX_BODY_FONT = "Arial Unicode MS"
PDF_CJK_FONT = "AdarianCJK"
INK = "17324D"
HEADING = "2E74B5"
HEADING_DARK = "1F4D78"
MUTED = "607586"


def write_report_docx(view: dict[str, Any], path: Path) -> Path:
    """Write a formal editable report without workbench diagnostics."""

    path.parent.mkdir(parents=True, exist_ok=True)
    document = Document()
    _configure_docx(document)
    document.core_properties.title = str(view.get("title") or "舆情风险研判报告")

    title = document.add_paragraph()
    title.paragraph_format.space_after = Pt(6)
    title_run = title.add_run(_display_text(view.get("title") or "舆情风险研判报告"))
    _format_docx_run(title_run, size=22, bold=True, color=INK)

    for section in view.get("sections") or []:
        _add_docx_section(document, section)
    _add_docx_appendix(document, view.get("appendix") or {})

    document.save(path)
    return path


def write_report_pdf(view: dict[str, Any], path: Path) -> Path:
    """Write a formal fixed-layout report without workbench diagnostics."""

    path.parent.mkdir(parents=True, exist_ok=True)
    _register_pdf_font()

    styles = _pdf_styles()
    story: list[Any] = [
        Paragraph(_pdf_text(view.get("title") or "舆情风险研判报告"), styles["Title"]),
        Spacer(1, 10),
    ]
    for section in view.get("sections") or []:
        _add_pdf_section(story, section, styles)
    _add_pdf_appendix(story, view.get("appendix") or {}, styles)

    report = SimpleDocTemplate(
        str(path),
        pagesize=letter,
        leftMargin=inch,
        rightMargin=inch,
        topMargin=0.78 * inch,
        bottomMargin=0.72 * inch,
        title=str(view.get("title") or "舆情风险研判报告"),
        author="Adarian",
    )
    report.build(story, onFirstPage=_draw_pdf_footer, onLaterPages=_draw_pdf_footer)
    return path


def _configure_docx(document: Document) -> None:
    section = document.sections[0]
    section.page_width = Inches(8.5)
    section.page_height = Inches(11)
    section.top_margin = Inches(1)
    section.right_margin = Inches(1)
    section.bottom_margin = Inches(1)
    section.left_margin = Inches(1)
    section.header_distance = Inches(0.492)
    section.footer_distance = Inches(0.492)
    section.start_type = WD_SECTION.NEW_PAGE

    normal = document.styles["Normal"]
    _configure_docx_style(normal, 11, INK, 0, 6, 1.1)
    _configure_docx_style(document.styles["Heading 1"], 16, HEADING, 16, 8, 1.0, bold=True)
    _configure_docx_style(document.styles["Heading 2"], 13, HEADING, 12, 6, 1.0, bold=True)
    _configure_docx_style(document.styles["Heading 3"], 12, HEADING_DARK, 8, 4, 1.0, bold=True)

    list_style = document.styles["List Bullet"]
    _configure_docx_style(list_style, 11, INK, 0, 8, 1.167)
    list_style.paragraph_format.left_indent = Inches(0.5)
    list_style.paragraph_format.first_line_indent = Inches(-0.25)

    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    footer_run = footer.add_run("Adarian  |  ")
    _format_docx_run(footer_run, size=9, color=MUTED)
    _add_page_field(footer)


def _configure_docx_style(style: Any, size: float, color: str, before: float, after: float, line_spacing: float, *, bold: bool = False) -> None:
    style.font.name = DOCX_BODY_FONT
    style.font.size = Pt(size)
    style.font.bold = bold
    style.font.color.rgb = RGBColor.from_string(color)
    style.element.rPr.rFonts.set(qn("w:eastAsia"), DOCX_BODY_FONT)
    style.paragraph_format.space_before = Pt(before)
    style.paragraph_format.space_after = Pt(after)
    style.paragraph_format.line_spacing = line_spacing


def _format_docx_run(run: Any, *, size: float = 11, bold: bool = False, color: str = INK) -> None:
    run.font.name = DOCX_BODY_FONT
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = RGBColor.from_string(color)
    run._element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:eastAsia"), DOCX_BODY_FONT)


def _add_docx_section(document: Document, section: dict[str, Any]) -> None:
    document.add_heading(_display_text(section.get("heading") or ""), level=1)
    for block in section.get("blocks") or []:
        kind = block.get("type")
        if kind == "subheading":
            document.add_heading(_display_text(block.get("text") or ""), level=2)
        elif kind == "list":
            for item in block.get("items") or []:
                paragraph = document.add_paragraph(style="List Bullet")
                paragraph.add_run(_display_text(item))
        elif kind == "preformatted":
            paragraph = document.add_paragraph()
            _set_paragraph_shading(paragraph, "F3F7FA")
            run = paragraph.add_run(str(block.get("text") or ""))
            _format_docx_run(run, size=9.5, color=INK)
            run.font.name = "Courier New"
            fonts = run._element.get_or_add_rPr().get_or_add_rFonts()
            fonts.set(qn("w:ascii"), "Courier New")
            fonts.set(qn("w:hAnsi"), "Courier New")
        elif kind == "table":
            _add_docx_table(document, block)
        elif kind == "callout":
            paragraph = document.add_paragraph()
            _set_paragraph_shading(paragraph, "EEF8FC")
            title = paragraph.add_run(f"{_display_text(block.get('title') or '')}\n")
            _format_docx_run(title, bold=True, color=HEADING_DARK)
            paragraph.add_run(_display_text(block.get("text") or ""))
        else:
            text = block.get("text") or ""
            if _is_markdown_subheading(text):
                document.add_heading(_display_text(text), level=2)
            else:
                document.add_paragraph(_display_text(text))


def _add_docx_appendix(document: Document, appendix: dict[str, Any]) -> None:
    if appendix.get("mode") == "hidden":
        return
    document.add_heading(_display_text(appendix.get("title") or "附录"), level=1)
    for section in appendix.get("sections") or []:
        _add_docx_section(document, section)


def _add_docx_table(document: Document, block: dict[str, Any]) -> None:
    headers = [str(value) for value in block.get("headers") or []]
    rows = [[str(value) for value in row] for row in block.get("rows") or []]
    column_count = len(headers) or max((len(row) for row in rows), default=0)
    if not column_count:
        return

    widths = [6.5 / column_count] * column_count
    if column_count == 2:
        widths = [2.05, 4.45]
    table = document.add_table(rows=1, cols=column_count)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False

    for index, cell in enumerate(table.rows[0].cells):
        cell.width = Inches(widths[index])
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        _set_cell_shading(cell, "EAF2F7")
        run = cell.paragraphs[0].add_run(_display_text(headers[index] if index < len(headers) else ""))
        _format_docx_run(run, size=9.5, bold=True, color=HEADING_DARK)

    for row in rows:
        cells = table.add_row().cells
        for index, cell in enumerate(cells):
            cell.width = Inches(widths[index])
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            run = cell.paragraphs[0].add_run(_display_text(row[index] if index < len(row) else ""))
            _format_docx_run(run, size=9.5, color=INK)
    document.add_paragraph().paragraph_format.space_after = Pt(2)


def _set_paragraph_shading(paragraph: Any, fill: str) -> None:
    properties = paragraph._p.get_or_add_pPr()
    shading = OxmlElement("w:shd")
    shading.set(qn("w:fill"), fill)
    properties.append(shading)


def _set_cell_shading(cell: Any, fill: str) -> None:
    properties = cell._tc.get_or_add_tcPr()
    shading = OxmlElement("w:shd")
    shading.set(qn("w:fill"), fill)
    properties.append(shading)


def _add_page_field(paragraph: Any) -> None:
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instruction = OxmlElement("w:instrText")
    instruction.set(qn("xml:space"), "preserve")
    instruction.text = " PAGE "
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.extend([begin, instruction, end])
    _format_docx_run(run, size=9, color=MUTED)


def _pdf_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "Title": ParagraphStyle(
            "AdarianTitle",
            parent=base["Title"],
            fontName=PDF_CJK_FONT,
            fontSize=22,
            leading=28,
            textColor=colors.HexColor(f"#{INK}"),
            alignment=TA_LEFT,
            spaceAfter=8,
            wordWrap="CJK",
        ),
        "Subtitle": ParagraphStyle(
            "AdarianSubtitle",
            parent=base["Normal"],
            fontName=PDF_CJK_FONT,
            fontSize=10.5,
            leading=16,
            textColor=colors.HexColor(f"#{MUTED}"),
            spaceAfter=6,
            wordWrap="CJK",
        ),
        "Meta": ParagraphStyle(
            "AdarianMeta",
            parent=base["Normal"],
            fontName=PDF_CJK_FONT,
            fontSize=8.5,
            leading=12,
            textColor=colors.HexColor(f"#{MUTED}"),
            wordWrap="CJK",
        ),
        "H1": ParagraphStyle(
            "AdarianH1",
            parent=base["Heading1"],
            fontName=PDF_CJK_FONT,
            fontSize=16,
            leading=22,
            textColor=colors.HexColor(f"#{HEADING}"),
            spaceBefore=16,
            spaceAfter=8,
            wordWrap="CJK",
        ),
        "H2": ParagraphStyle(
            "AdarianH2",
            parent=base["Heading2"],
            fontName=PDF_CJK_FONT,
            fontSize=12,
            leading=18,
            textColor=colors.HexColor(f"#{HEADING_DARK}"),
            spaceBefore=10,
            spaceAfter=5,
            wordWrap="CJK",
        ),
        "Body": ParagraphStyle(
            "AdarianBody",
            parent=base["BodyText"],
            fontName=PDF_CJK_FONT,
            fontSize=10.5,
            leading=17,
            textColor=colors.HexColor(f"#{INK}"),
            spaceAfter=7,
            wordWrap="CJK",
        ),
        "List": ParagraphStyle(
            "AdarianList",
            parent=base["BodyText"],
            fontName=PDF_CJK_FONT,
            fontSize=10.5,
            leading=17,
            textColor=colors.HexColor(f"#{INK}"),
            leftIndent=4,
            spaceAfter=4,
            wordWrap="CJK",
        ),
        "Code": ParagraphStyle(
            "AdarianCode",
            parent=base["Code"],
            fontName=PDF_CJK_FONT,
            fontSize=8.8,
            leading=13.5,
            textColor=colors.HexColor(f"#{INK}"),
            backColor=colors.HexColor("#F3F7FA"),
            borderColor=colors.HexColor("#DCE8EF"),
            borderWidth=0.7,
            borderPadding=9,
            spaceBefore=2,
            spaceAfter=9,
            wordWrap="CJK",
        ),
    }


def _add_pdf_section(story: list[Any], section: dict[str, Any], styles: dict[str, ParagraphStyle]) -> None:
    story.append(Paragraph(_pdf_text(section.get("heading") or ""), styles["H1"]))
    for block in section.get("blocks") or []:
        kind = block.get("type")
        if kind == "subheading":
            story.append(Paragraph(_pdf_text(block.get("text") or ""), styles["H2"]))
        elif kind == "list":
            items = [
                ListItem(Paragraph(_pdf_text(item), styles["List"]), leftIndent=12)
                for item in block.get("items") or []
            ]
            story.append(ListFlowable(items, bulletType="bullet", bulletFontName=PDF_CJK_FONT, leftIndent=20, bulletOffsetY=1))
            story.append(Spacer(1, 4))
        elif kind == "preformatted":
            story.append(Paragraph(_pdf_text(block.get("text") or ""), styles["Code"]))
        elif kind == "table":
            table = _build_pdf_table(block, styles)
            if table is not None:
                story.extend([table, Spacer(1, 8)])
        elif kind == "callout":
            title = _pdf_text(block.get("title") or "")
            text = _pdf_text(block.get("text") or "")
            callout = Table(
                [[Paragraph(f"<b>{title}</b><br/>{text}", styles["Body"])]],
                colWidths=[6.35 * inch],
            )
            callout.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EEF8FC")),
                ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#A8D5EA")),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]))
            story.extend([callout, Spacer(1, 7)])
        else:
            text = block.get("text") or ""
            style = styles["H2"] if _is_markdown_subheading(text) else styles["Body"]
            story.append(Paragraph(_pdf_text(text), style))


def _build_pdf_table(block: dict[str, Any], styles: dict[str, ParagraphStyle]) -> Table | None:
    headers = [str(value) for value in block.get("headers") or []]
    rows = [[str(value) for value in row] for row in block.get("rows") or []]
    column_count = len(headers) or max((len(row) for row in rows), default=0)
    if not column_count:
        return None

    header_style = ParagraphStyle(
        "AdarianTableHeader",
        parent=styles["Body"],
        fontSize=9,
        leading=13,
        textColor=colors.HexColor(f"#{HEADING_DARK}"),
    )
    cell_style = ParagraphStyle(
        "AdarianTableCell",
        parent=styles["Body"],
        fontSize=8.6,
        leading=12.5,
        spaceAfter=0,
    )
    normalized_headers = headers + [""] * (column_count - len(headers))
    normalized_rows = [row + [""] * (column_count - len(row)) for row in rows]
    data = [
        [Paragraph(f"<b>{_pdf_text(value)}</b>", header_style) for value in normalized_headers],
        *[[Paragraph(_pdf_text(value), cell_style) for value in row] for row in normalized_rows],
    ]
    widths = [6.35 * inch / column_count] * column_count
    if column_count == 2:
        widths = [2.0 * inch, 4.35 * inch]
    table = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EAF2F7")),
        ("GRID", (0, 0), (-1, -1), 0.55, colors.HexColor("#C8D8E3")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return table


def _add_pdf_appendix(story: list[Any], appendix: dict[str, Any], styles: dict[str, ParagraphStyle]) -> None:
    if appendix.get("mode") == "hidden":
        return
    story.append(Paragraph(_pdf_text(appendix.get("title") or "附录"), styles["H1"]))
    for section in appendix.get("sections") or []:
        _add_pdf_section(story, section, styles)


def _draw_pdf_footer(canvas: Any, document: Any) -> None:
    canvas.saveState()
    canvas.setFont(PDF_CJK_FONT, 8)
    canvas.setFillColor(colors.HexColor(f"#{MUTED}"))
    canvas.drawRightString(letter[0] - inch, 0.42 * inch, f"Adarian  |  {document.page}")
    canvas.restoreState()


def _pdf_text(value: Any) -> str:
    return html.escape(_display_text(value)).replace("\n", "<br/>")


def _display_text(value: Any) -> str:
    text = str(value or "").strip()
    text = re.sub(r"^#{1,6}\s+", "", text)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"__(.+?)__", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    return text


def _is_markdown_subheading(value: Any) -> bool:
    return bool(re.match(r"^\s*#{2,6}\s+", str(value or "")))


def _register_pdf_font() -> None:
    if PDF_CJK_FONT in pdfmetrics.getRegisteredFontNames():
        return
    candidates = [
        os.getenv("ADARIAN_REPORT_FONT_PATH", ""),
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/Library/Fonts/Arial Unicode.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    ]
    font_path = next((Path(item) for item in candidates if item and Path(item).is_file()), None)
    if font_path is None:
        raise RuntimeError(
            "REPORT_PDF_FONT_NOT_FOUND: configure ADARIAN_REPORT_FONT_PATH with a Chinese TrueType font"
        )
    pdfmetrics.registerFont(TTFont(PDF_CJK_FONT, str(font_path), subfontIndex=0))
