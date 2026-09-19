"""
Layer D: Document Reconstruction / Export
DOCX: two-column body, single-column header block.
PDF: BaseDocTemplate with non-overlapping frames.
     Header is measured, then column frames are placed BELOW it.
"""
import re
import logging

from app.models import FormattedDocument, SectionType
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from reportlab.lib.pagesizes import letter as LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate,
    Paragraph, Spacer, PageBreak, FrameBreak, NextPageTemplate,
)
from reportlab.platypus import Table as RLTable, TableStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT
from reportlab.lib import colors as RC

logger = logging.getLogger(__name__)

PW, PH = LETTER
ML = MR = 0.75 * inch
MT = MB = 1.0 * inch
GAP = 0.25 * inch
BW = PW - ML - MR
CW = (BW - GAP) / 2
BH = PH - MT - MB


def _S(name, **kw):
    SS = getSampleStyleSheet()
    return ParagraphStyle(name, parent=SS["Normal"], **kw)


HEADER_TYPES = {
    SectionType.TITLE, SectionType.AUTHORS,
    SectionType.AFFILIATION, SectionType.ABSTRACT, SectionType.KEYWORDS,
}


class DocumentExporter:

    # ── DOCX ─────────────────────────────────────────────────────────

    def export_docx(self, document: FormattedDocument, output_path: str) -> str:
        doc = Document()
        for sec in doc.sections:
            sec.left_margin = Inches(0.75); sec.right_margin = Inches(0.75)
            sec.top_margin  = Inches(1.0);  sec.bottom_margin = Inches(1.0)

        hs = [s for s in document.sections if s.type in HEADER_TYPES]
        bs = [s for s in document.sections if s.type not in HEADER_TYPES]

        for s in hs:
            self._write_section(doc, s)

        if bs:
            p = doc.add_paragraph()
            pPr = p._p.get_or_add_pPr()
            sB = OxmlElement('w:sectPr')
            self._set_cols(sB, 1, continuous=True)
            pPr.append(sB)
            for s in bs:
                self._write_section(doc, s)
            self._set_cols(doc.sections[-1]._sectPr, 2)

        doc.save(output_path)
        return output_path

    def _set_cols(self, sectPr, num, continuous=False):
        for el in sectPr.findall(qn('w:cols')):
            sectPr.remove(el)
        c = OxmlElement('w:cols')
        c.set(qn('w:num'), str(num))
        if num > 1:
            c.set(qn('w:space'), '720')
            c.set(qn('w:equalWidth'), '1')
        sectPr.append(c)
        if continuous:
            for el in sectPr.findall(qn('w:type')):
                sectPr.remove(el)
            t = OxmlElement('w:type')
            t.set(qn('w:val'), 'continuous')
            sectPr.append(t)

    def _write_section(self, doc, section):
        if section.formatted_heading:
            p = doc.add_paragraph()
            r = p.add_run(section.formatted_heading)
            fr = section.heading_font_rule
            if fr:
                r.font.name = fr.font_family; r.font.size = Pt(fr.font_size)
                r.font.bold = fr.bold; r.font.italic = fr.italic
                p.alignment = self._dalign(fr.alignment)
            else:
                r.font.name = "Times New Roman"; r.font.size = Pt(10)
                r.font.bold = True; p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            self._dsp(p)

        if section.content:
            for blk in self._blocks(section.content):
                if blk['type'] == 'table':
                    self._docx_table(doc, blk['rows'], blk['table_num'])
                else:
                    for line in blk['text'].split('\n'):
                        line = line.strip()
                        if not line:
                            continue
                        p = doc.add_paragraph()
                        r = p.add_run(line)
                        fr = section.font_rule
                        if fr:
                            r.font.name = fr.font_family; r.font.size = Pt(fr.font_size)
                            r.font.bold = fr.bold; r.font.italic = fr.italic
                            p.alignment = self._dalign(fr.alignment)
                        else:
                            r.font.name = "Times New Roman"; r.font.size = Pt(10)
                            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                        self._dsp(p)

        if section.subsections:
            for sub in section.subsections:
                self._write_section(doc, sub)

    def _docx_table(self, doc, rows, tnum):
        if not rows:
            return
        cap = doc.add_paragraph()
        cr = cap.add_run(f"TABLE {self._roman(tnum)}")
        cr.font.name = "Times New Roman"; cr.font.size = Pt(9); cr.font.bold = True
        cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        cap.paragraph_format.space_before = Pt(4)
        cap.paragraph_format.space_after  = Pt(2)
        nc = max(len(r) for r in rows)
        t = doc.add_table(rows=len(rows), cols=nc)
        t.style = 'Table Grid'
        for ri, rd in enumerate(rows):
            for ci in range(min(len(rd), nc)):
                cell = t.rows[ri].cells[ci]
                cell.text = rd[ci]
                par = cell.paragraphs[0]
                par.alignment = WD_ALIGN_PARAGRAPH.CENTER
                par.paragraph_format.space_before = Pt(1)
                par.paragraph_format.space_after  = Pt(1)
                if par.runs:
                    par.runs[0].font.name = "Times New Roman"
                    par.runs[0].font.size = Pt(9)
                    if ri == 0:
                        par.runs[0].font.bold = True
        a = doc.add_paragraph()
        a.paragraph_format.space_after = Pt(4)

    def _dalign(self, a):
        return {"center": WD_ALIGN_PARAGRAPH.CENTER, "justify": WD_ALIGN_PARAGRAPH.JUSTIFY,
                "right": WD_ALIGN_PARAGRAPH.RIGHT}.get(a, WD_ALIGN_PARAGRAPH.LEFT)

    def _dsp(self, p):
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after  = Pt(2)
        p.paragraph_format.line_spacing  = Pt(12)

    # ── PDF ──────────────────────────────────────────────────────────

    def export_pdf(self, document: FormattedDocument, output_path: str) -> str:
        """
        IEEE PDF using SimpleDocTemplate.
        - Title, authors, affiliation, abstract, keywords: full-width paragraphs.
        - Body (Introduction onwards): two-column via a flowing RLTable
          where each paragraph is its own row, so ReportLab can split freely.
        No frame calculations. No header height measuring. No custom templates.
        """
        from reportlab.platypus import SimpleDocTemplate

        # Apply all 5 fixes from the analysis:
        # Fix 1: tight heading spacing
        s_title  = _S("pT",   fontName="Times-Bold",   fontSize=16, leading=20, alignment=TA_CENTER, spaceAfter=3)
        s_author = _S("pAu",  fontName="Times-Roman",  fontSize=10, leading=12, alignment=TA_CENTER, spaceAfter=1)
        s_affil  = _S("pAf",  fontName="Times-Italic", fontSize=10, leading=12, alignment=TA_CENTER, spaceAfter=2)
        s_abl    = _S("pAbl", fontName="Times-Bold",   fontSize=9,  leading=10, alignment=TA_CENTER, spaceBefore=3, spaceAfter=1)
        s_abs    = _S("pAb",  fontName="Times-Roman",  fontSize=9,  leading=11, alignment=TA_JUSTIFY, spaceAfter=2)
        s_kw     = _S("pKw",  fontName="Times-Italic", fontSize=9,  leading=10, alignment=TA_JUSTIFY, spaceAfter=3)
        # Fix 1: reduced spaceBefore/spaceAfter on headings
        s_head   = _S("pH",   fontName="Times-Bold",   fontSize=10, leading=11, alignment=TA_LEFT,    spaceBefore=2, spaceAfter=1)
        s_sub    = _S("pSH",  fontName="Times-Italic", fontSize=9,  leading=10, alignment=TA_LEFT,    spaceBefore=1, spaceAfter=1)
        # Fix 2: denser body text
        s_body   = _S("pB",   fontName="Times-Roman",  fontSize=9,  leading=10, alignment=TA_JUSTIFY, spaceAfter=0, firstLineIndent=10)

        HEADER = {SectionType.TITLE, SectionType.AUTHORS,
                  SectionType.AFFILIATION, SectionType.ABSTRACT, SectionType.KEYWORDS}
        hs = [s for s in document.sections if s.type in HEADER]
        bs = [s for s in document.sections if s.type not in HEADER]

        # ── Full-width header paragraphs ─────────────────────────────
        story = []
        for s in hs:
            if s.type == SectionType.TITLE:
                txt = (s.formatted_heading or s.content or "").strip()
                if txt:
                    story.append(Paragraph(self._esc(txt), s_title))
            elif s.type == SectionType.AUTHORS and s.content:
                story.append(Paragraph(self._esc(s.content.replace("\n", ", ")), s_author))
            elif s.type == SectionType.AFFILIATION and s.content:
                story.append(Paragraph(self._esc(s.content.replace("\n", " | ")), s_affil))
            elif s.type == SectionType.ABSTRACT:
                story.append(Paragraph("Abstract", s_abl))
                if s.content:
                    story.append(Paragraph(self._esc(s.content), s_abs))
            elif s.type == SectionType.KEYWORDS and s.content:
                story.append(Paragraph(f"<i>Index Terms</i>\u2014{self._esc(s.content)}", s_kw))

        # ── Two-column body as a flowing RLTable ─────────────────────
        # Each body paragraph is a separate row in a 2-column table.
        # Left cell = paragraph, right cell = empty.
        # This lets ReportLab split the table row-by-row across pages
        # and fill both columns naturally.
        #
        # We use a single-row-per-paragraph table so every paragraph
        # can be individually placed in the left or right column flow.
        # Fix 4: slightly narrower cell width
        col_w = (CW - 6)

        def body_row(flowable):
            """Wrap a single flowable in a 2-col table row."""
            return RLTable([[flowable, Spacer(1, 1)]], colWidths=[col_w, col_w],
                           splitByRow=1)

        def make_body_table(items):
            """
            Pack all body items into a single 2-column table.
            Split items roughly in half: first half goes in left cell,
            second half goes in right cell. splitByRow=1 allows page breaks.
            """
            if not items:
                return []
            mid = len(items) // 2
            left_items  = items[:mid] if items else [Spacer(1, 1)]
            right_items = items[mid:] if len(items) > 1 else [Spacer(1, 1)]
            if not left_items:
                left_items = [Spacer(1, 1)]
            if not right_items:
                right_items = [Spacer(1, 1)]

            # Split into chunks of ~50 items per row to allow page splitting
            chunk_size = 20
            left_chunks  = [left_items[i:i+chunk_size]  for i in range(0, len(left_items),  chunk_size)]
            right_chunks = [right_items[i:i+chunk_size] for i in range(0, len(right_items), chunk_size)]

            # Pad to same number of chunks
            while len(left_chunks) < len(right_chunks):
                left_chunks.append([Spacer(1, 1)])
            while len(right_chunks) < len(left_chunks):
                right_chunks.append([Spacer(1, 1)])

            data = [[l, r] for l, r in zip(left_chunks, right_chunks)]
            tbl = RLTable(data, colWidths=[col_w, col_w], splitByRow=1)
            tbl.setStyle(TableStyle([
                ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING',    (0, 0), (-1, -1), 0),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
                ('LEFTPADDING',   (0, 0), (-1, -1), 0),
                ('RIGHTPADDING',  (0, 0), (0, -1),  GAP / 2),
                ('RIGHTPADDING',  (1, 0), (1, -1),  0),
            ]))
            return [tbl]

        # Collect all body flowables
        body_items = []
        for s in bs:
            if s.formatted_heading:
                body_items.append(Paragraph(self._esc(s.formatted_heading), s_head))
            if s.content:
                for blk in self._blocks(s.content):
                    if blk['type'] == 'table':
                        # Fix 4: table inside column uses adjusted width
                        body_items.extend(self._pdf_table_col(blk['rows'], blk['table_num'], col_w))
                    else:
                        for line in blk['text'].split('\n'):
                            line = line.strip()
                            if line:
                                body_items.append(Paragraph(self._esc(line), s_body))
            if s.subsections:
                for sub in s.subsections:
                    if sub.formatted_heading:
                        body_items.append(Paragraph(self._esc(sub.formatted_heading), s_sub))
                    if sub.content:
                        for blk in self._blocks(sub.content):
                            if blk['type'] == 'table':
                                body_items.extend(self._pdf_table_col(blk['rows'], blk['table_num'], col_w))
                            else:
                                for line in blk['text'].split('\n'):
                                    line = line.strip()
                                    if line:
                                        body_items.append(Paragraph(self._esc(line), s_body))

        if body_items:
            story.append(Spacer(1, 4))
            story.extend(make_body_table(body_items))

        pdf = SimpleDocTemplate(
            output_path, pagesize=LETTER,
            leftMargin=ML, rightMargin=MR,
            topMargin=MT,  bottomMargin=MB,
        )

        try:
            pdf.build(story)
        except Exception as e:
            logger.error(f"PDF build error: {e}")
            raise
        return output_path

    def _pdf_table_col(self, rows, tnum: int, col_width: float):
        """IEEE table sized to fit within a single column."""
        if not rows:
            return []
        roman = self._roman(tnum)
        # Fix 4: fontSize=7 and use col_width - 12
        cap_s = _S(f"TC2{tnum}", fontName="Times-Bold",  fontSize=8, leading=10, alignment=TA_CENTER, spaceBefore=3, spaceAfter=1)
        c_s   = _S(f"Tc2{tnum}", fontName="Times-Roman", fontSize=7, leading=9,  alignment=TA_CENTER)
        h_s   = _S(f"Th2{tnum}", fontName="Times-Bold",  fontSize=7, leading=9,  alignment=TA_CENTER)
        data = [[Paragraph(self._esc(c), h_s if ri == 0 else c_s) for c in row]
                for ri, row in enumerate(rows)]
        nc = max(len(r) for r in rows)
        cw = (col_width - 12) / nc   # Fix 4
        tbl = RLTable(data, colWidths=[cw] * nc, splitByRow=1)
        tbl.setStyle(TableStyle([
            ('GRID',           (0, 0), (-1, -1), 0.4, RC.black),
            ('BACKGROUND',     (0, 0), (-1,  0), RC.Color(0.85, 0.85, 0.85)),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [RC.white, RC.Color(0.96, 0.96, 0.96)]),
            ('VALIGN',         (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING',     (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING',  (0, 0), (-1, -1), 2),
            ('LEFTPADDING',    (0, 0), (-1, -1), 3),
            ('RIGHTPADDING',   (0, 0), (-1, -1), 3),
        ]))
        return [Paragraph(f"TABLE {roman}", cap_s), tbl, Spacer(1, 3)]

    # ── Shared helpers ────────────────────────────────────────────────

    def _blocks(self, content: str):
        blocks = []
        pattern = r'\[\[TABLE_START:?(\d*)\]\](.*?)\[\[TABLE_END\]\]'
        last = 0
        for m in re.finditer(pattern, content, re.DOTALL):
            before = content[last:m.start()].strip()
            if before:
                blocks.append({'type': 'text', 'text': before})
            tnum = int(m.group(1)) if m.group(1) else 1
            rows = []
            for line in m.group(2).strip().split('\n'):
                line = line.strip()
                if line.startswith('|') and line.endswith('|'):
                    rows.append([c.strip() for c in line[1:-1].split('|')])
            if rows:
                blocks.append({'type': 'table', 'rows': rows, 'table_num': tnum})
            last = m.end()
        after = content[last:].strip()
        if after:
            blocks.append({'type': 'text', 'text': after})
        if not blocks:
            blocks.append({'type': 'text', 'text': content})
        return blocks

    def _pdf_table(self, rows, tnum: int):
        if not rows:
            return []
        SS = getSampleStyleSheet()
        roman = self._roman(tnum)
        cap_s = _S(f"TC{tnum}", fontName="Times-Bold",   fontSize=9, leading=11, alignment=TA_CENTER, spaceBefore=4, spaceAfter=2)
        c_s   = _S(f"Tc{tnum}", fontName="Times-Roman",  fontSize=8, leading=10, alignment=TA_CENTER)
        h_s   = _S(f"Th{tnum}", fontName="Times-Bold",   fontSize=8, leading=10, alignment=TA_CENTER)
        data = [[Paragraph(self._esc(c), h_s if ri == 0 else c_s) for c in row]
                for ri, row in enumerate(rows)]
        nc = max(len(r) for r in rows)
        cw = CW / nc
        tbl = RLTable(data, colWidths=[cw] * nc, splitByRow=1)
        tbl.setStyle(TableStyle([
            ('GRID',           (0, 0), (-1, -1), 0.5, RC.black),
            ('BACKGROUND',     (0, 0), (-1,  0), RC.Color(0.85, 0.85, 0.85)),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [RC.white, RC.Color(0.96, 0.96, 0.96)]),
            ('VALIGN',         (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING',     (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING',  (0, 0), (-1, -1), 3),
            ('LEFTPADDING',    (0, 0), (-1, -1), 4),
            ('RIGHTPADDING',   (0, 0), (-1, -1), 4),
        ]))
        return [Paragraph(f"TABLE {roman}", cap_s), tbl, Spacer(1, 4)]

    @staticmethod
    def _roman(n: int) -> str:
        r = ['I','II','III','IV','V','VI','VII','VIII','IX','X']
        return r[n - 1] if 1 <= n <= len(r) else str(n)

    @staticmethod
    def _esc(text: str) -> str:
        return (text.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
                .replace("\u2019","'").replace("\u2018","'")
                .replace("\u201c",'"').replace("\u201d",'"')
                .replace("\u2014","&#8212;").replace("\u2013","&#8211;"))
