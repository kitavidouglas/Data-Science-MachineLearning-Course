# report_builder.py

from datetime import datetime
from collections import defaultdict

from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.section import WD_ORIENT, WD_SECTION
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

from table_utils import (
    _compute_column_widths,
    _set_cell_background,
    add_mini_table_to_cell,
    style_paragraph,
    add_justified_text,
    add_global_page_numbers
)
from html_parser import parse_html_content


def create_word_report(table_data, region_filter):
    doc = Document()

    # ── Page Setup ────────────────────────────────────────────
    sect0 = doc.sections[0]
    sect0.orientation = WD_ORIENT.LANDSCAPE
    sect0.page_width, sect0.page_height = Inches(11), Inches(8.5)
    for sect in doc.sections:
        sect.top_margin = sect.bottom_margin = sect.left_margin = sect.right_margin = Inches(0.5)

    # ── Styles ─────────────────────────────────────────────────
    normal = doc.styles["Normal"]
    normal.font.name, normal.font.size = "Calibri", Pt(11)
    h1 = doc.styles["Heading 1"]
    h1.font.name, h1.font.size, h1.font.color.rgb = "Calibri", Pt(16), RGBColor.from_string("107AB8")
    h2 = doc.styles["Heading 2"]
    h2.font.name, h2.font.size, h2.font.color.rgb = "Calibri", Pt(13), RGBColor.from_string("EF6149")

    # ── Cover Page ────────────────────────────────────────────
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("Regional Issues Report\n")
    r.font.size, r.font.color.rgb = Pt(24), RGBColor.from_string("107AB8")
    doc.add_paragraph("Mini Group / Eleven Degrees Consulting").alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph(f"Date: {datetime.today():%Y-%m-%d}").alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_page_break()

    # ── Footer (region + page numbers) ────────────────────────
    add_global_page_numbers(doc)
    for sec in doc.sections:
        ftr = sec.footer
        # insert region line above page numbers
        p_reg = ftr.add_paragraph(f"Regional Issues Report for “{(region_filter or 'ALL').upper()}”")
        p_reg.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_reg.runs[0].font.name, p_reg.runs[0].font.size = "Calibri", Pt(9)

    # ── Group by Project ───────────────────────────────────────
    grouped = defaultdict(list)
    for row in table_data:
        grouped[row[0]].append(row)

    first = True
    for pid, rows in grouped.items():
        proj = rows[0]
        name, branch, region, start, status = proj[1], proj[2], proj[3], proj[4], proj[5]
        bm, om, sup = proj[14], proj[15], proj[16]

        # New section per project
        if not first:
            section = doc.add_section(WD_SECTION.NEW_PAGE)
        else:
            section = doc.sections[0]
            first = False

        # ─ Header (logos + metadata) ────────────────────────────
        header = section.header
        header.is_linked_to_previous = False
        for p in list(header.paragraphs):
            header._element.remove(p._element)

        logo_tbl = header.add_table(rows=1, cols=2, width=Inches(11))
        logo_tbl.autofit = False
        logo_tbl.columns[0].width = logo_tbl.columns[1].width = Inches(5.5)

        # left logo
        c0 = logo_tbl.cell(0, 0)
        c0.vertical_alignment = WD_ALIGN_PARAGRAPH.CENTER
        p0 = c0.paragraphs[0]; p0.alignment = WD_ALIGN_PARAGRAPH.LEFT
        try: p0.add_run().add_picture("minigroup_logo.png", width=Inches(1.2))
        except: pass

        # right logo
        c1 = logo_tbl.cell(0, 1)
        c1.vertical_alignment = WD_ALIGN_PARAGRAPH.CENTER
        p1 = c1.paragraphs[0]; p1.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        try: p1.add_run().add_picture("minigroup.png", width=Inches(1.2))
        except: pass

        # metadata line
        meta = (f"Branch: {branch} | Region: {region} | Start: {start} | "
                f"Status: {status} | BM: {bm} | OM: {om} | Sup: {sup}")
        mp = header.add_paragraph(meta)
        mp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        mp.runs[0].font.name, mp.runs[0].runs[0].font.size = "Calibri", Pt(9)

        # ── Body: Project Info ───────────────────────────────────
        doc.add_heading(f"Project: {name}", level=1)
        for label, val in [
            ("Branch", branch), ("Region", region), ("Start Date", start),
            ("Status", status), ("Branch Manager", bm),
            ("Operations Manager", om), ("Supervisor", sup)
        ]:
            p = doc.add_paragraph()
            run = p.add_run(f"{label}: "); run.bold = True
            p.add_run(str(val))
        doc.add_paragraph()

        # ── Issues ──────────────────────────────────────────────
        for issue in rows:
            title, sev = issue[6], issue[7]
            doc.add_heading(f"Issue: {title}", level=2)

            # 1) Short metadata grid
            meta_fields = [("Severity", sev), ("Cost Impact", f"${issue[10]:,.2f}")]
            tbl_meta = doc.add_table(rows=len(meta_fields), cols=2)
            tbl_meta.autofit = False
            widths = _compute_column_widths(meta_fields, max_total_width_inches=Inches(6).inches)
            for i, w in enumerate(widths):
                for cell in tbl_meta.columns[i].cells:
                    cell.width = w
            for i, (lbl, val) in enumerate(meta_fields):
                c0, c1 = tbl_meta.rows[i].cells
                c0.text = lbl; c0.paragraphs[0].runs[0].bold = True
                c1.text = str(val)
            doc.add_paragraph()

            # 2) Long text sections with HTML parsing
            for lbl, html in [
                ("Description", issue[8]),
                ("Implication", issue[9]),
                ("Recommendation", issue[13])
            ]:
                doc.add_heading(lbl, level=3)
                cont = doc.add_table(rows=1, cols=1).cell(0,0)
                cont.width = Inches(10)
                for block in parse_html_content(html):
                    if block["type"] == "paragraph":
                        p = cont.add_paragraph()
                        style_paragraph(p)
                        for run in block["runs"]:
                            r = p.add_run(run["text"])
                            r.bold = run["bold"]
                            r.italic = run["italic"]
                            if run.get("href"):
                                # optional hyperlink logic here
                                pass
                    else:  # nested table block
                        add_mini_table_to_cell(cont, [h for h in block["rows"][0]], block["rows"][1:])
                doc.add_paragraph()

    return doc
