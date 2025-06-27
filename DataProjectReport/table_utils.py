# table_utils.py

from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

# ─── Paragraph Styling Helper ────────────────────────────────
def style_paragraph(p, font_size=11, justify=True):
    """
    Apply font, spacing, and alignment styles to a paragraph.
    """
    p.paragraph_format.line_spacing = 1.3
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(4)
    if justify:
        p.alignment = WD_PARAGRAPH_ALIGNMENT.JUSTIFY
    for run in p.runs:
        run.font.name = "Calibri"
        run.font.size = Pt(font_size)

# ─── Cell Background Color ───────────────────────────────────
def _set_cell_background(cell, color_hex):
    """
    Apply background shading to a table cell.
    """
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), color_hex)
    tcPr.append(shd)

# ─── Column Width Calculation ────────────────────────────────
def _compute_column_widths(text_matrix, max_total_width_inches=10.0, min_width_inches=0.5):
    """
    Dynamically compute column widths based on content length and type.
    """
    if not text_matrix:
        return []

    cols = list(zip(*text_matrix))
    scores = []
    total = 0.0

    for col in cols:
        cell_lengths = [len(str(cell or "")) for cell in col]
        max_len = max(cell_lengths)
        has_sentence = any(len(str(cell).split()) > 5 for cell in col)
        is_numeric = all(str(cell).replace(".", "", 1).isdigit() for cell in col if cell)

        weight = 1.8 if has_sentence else 0.5 if is_numeric else 1.0
        score = max_len * weight
        scores.append(score)
        total += score

    total = total or 1.0
    raw_widths = [(s / total) * max_total_width_inches for s in scores]
    capped = [max(min_width_inches, w) for w in raw_widths]

    total_used = sum(capped)
    if total_used > max_total_width_inches:
        factor = max_total_width_inches / total_used
        capped = [w * factor for w in capped]

    return [Inches(w) for w in capped]

# ─── Mini-Table Insertion ────────────────────────────────────
def add_mini_table_to_cell(cell, headers, rows):
    """
    Add a nested table inside a DOCX table cell with styled header.
    """
    header_len = len(headers or [])
    row_lens = [len(r) for r in rows]
    col_count = max([header_len] + row_lens) if row_lens or headers else 0

    matrix = []
    if headers:
        matrix.append([headers[i] if i < header_len else "" for i in range(col_count)])
    for row in rows:
        matrix.append([row[i] if i < len(row) else "" for i in range(col_count)])

    cell_width = getattr(cell, "width", Inches(6)).inches
    col_widths = _compute_column_widths(matrix, max_total_width_inches=cell_width)

    mini = cell.add_table(rows=1 if headers else 0, cols=col_count)
    mini.style = "Light Grid Accent 1"
    mini.autofit = False

    if headers:
        hdr_cells = mini.rows[0].cells
        for i, text in enumerate(matrix[0]):
            c = hdr_cells[i]
            c.width = col_widths[i]
            p = c.paragraphs[0]
            run = p.add_run(str(text))
            run.bold = True
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = 1.2
            p.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
            _set_cell_background(c, "D9D9D9")

    for row in matrix[1 if headers else 0:]:
        rc = mini.add_row().cells
        for i, text in enumerate(row):
            rc[i].width = col_widths[i]
            p = rc[i].paragraphs[0]
            p.text = str(text)
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = 1.15
            p.alignment = WD_PARAGRAPH_ALIGNMENT.LEFT

# ─── Add Justified Text to Cell ──────────────────────────────
def add_justified_text(cell, text):
    """
    Add a styled, justified paragraph of text inside a cell.
    """
    p = cell.add_paragraph(text)
    style_paragraph(p, font_size=11, justify=True)

# ─── Global Page Numbers in Footer ───────────────────────────
def add_global_page_numbers(doc):
    """
    Add auto-updating page numbers to all footers in the document.
    """
    for sec in doc.sections:
        footer = sec.footer
        footer.is_linked_to_previous = False
        p = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
        p.alignment = WD_PARAGRAPH_ALIGNMENT.RIGHT
        run = p.add_run()

        fldBegin = OxmlElement("w:fldChar")
        fldBegin.set(qn("w:fldCharType"), "begin")
        instrText = OxmlElement("w:instrText")
        instrText.text = " PAGE "
        fldSeparate = OxmlElement("w:fldChar")
        fldSeparate.set(qn("w:fldCharType"), "separate")
        fldEnd = OxmlElement("w:fldChar")
        fldEnd.set(qn("w:fldCharType"), "end")

        run._r.append(fldBegin)
        run._r.append(instrText)
        run._r.append(fldSeparate)
        run._r.append(fldEnd)

        run.font.size = Pt(9)
        run.font.color.rgb = RGBColor(128, 128, 128)
