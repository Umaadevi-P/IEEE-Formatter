"""
Layer A: Document Parsing Layer
Extracts structured content from .docx files.
Tables are preserved as pipe-delimited plain text grids.
No AI processing happens here.
"""
import re
import uuid
import logging
from typing import List, Optional

from docx import Document
from docx.text.paragraph import Paragraph
from docx.table import Table as DocxTable

from app.models import ParsedDocument, Section, SectionType

logger = logging.getLogger(__name__)

# Word XML namespace
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
P_TAG   = f"{{{W_NS}}}p"
TBL_TAG = f"{{{W_NS}}}tbl"

# Module-level table counter — reset at the start of each _parse_docx call
_global_table_counter = 0


class DocumentParser:
    """Extracts structured content from uploaded .docx files."""

    def parse(self, file_path: str) -> ParsedDocument:
        if file_path.lower().endswith(".pdf"):
            return self._parse_pdf(file_path)
        return self._parse_docx(file_path)

    # ------------------------------------------------------------------ #
    #  DOCX                                                                #
    # ------------------------------------------------------------------ #

    def _parse_docx(self, file_path: str) -> ParsedDocument:
        global _global_table_counter
        _global_table_counter = 0  # reset counter for each new document

        doc = Document(file_path)
        sections: List[Section] = []

        # --- Title (very first non-empty paragraph) ---
        title: Optional[str] = None
        for para in doc.paragraphs:
            if para.text.strip():
                title = para.text.strip()
                break

        if title:
            sections.append(Section(
                id=str(uuid.uuid4()),
                type=SectionType.TITLE,
                content=title,
                word_count=len(title.split()),
            ))

        # --- Authors / affiliation: paragraphs between title and first heading ---
        pre_heading: List[str] = []
        for para in doc.paragraphs:
            t = para.text.strip()
            if title and t == title:
                continue
            if self._is_heading(para):
                break
            if t and title:
                pre_heading.append(t)

        if pre_heading:
            sections.append(Section(
                id=str(uuid.uuid4()),
                type=SectionType.AUTHORS,
                content=pre_heading[0],
                word_count=len(pre_heading[0].split()),
            ))
            if len(pre_heading) >= 2:
                aff = "\n".join(pre_heading[1:])
                sections.append(Section(
                    id=str(uuid.uuid4()),
                    type=SectionType.AFFILIATION,
                    content=aff,
                    word_count=len(aff.split()),
                ))

        # --- Main parse: walk body XML to get paragraphs AND tables ---
        current_heading: Optional[str] = None
        current_content: List[str] = []
        current_subsections: List[Section] = []

        def flush():
            nonlocal current_heading, current_content, current_subsections
            if current_heading is not None:
                sections.append(self._make_section(
                    current_heading, current_content, current_subsections
                ))
            current_heading = None
            current_content = []
            current_subsections = []

        def add_text(text: str) -> None:
            """Append text to the right bucket."""
            if current_subsections:
                last = current_subsections[-1]
                last.content = (last.content + "\n" + text).strip()
                last.word_count = len(last.content.split())
            elif current_heading is not None:
                current_content.append(text)
            elif sections:
                # No open heading — glue to the last completed section
                sections[-1].content = (sections[-1].content + "\n" + text).strip()
                sections[-1].word_count = len(sections[-1].content.split())

        body = doc.element.body
        for child in body:
            tag = child.tag  # full qualified tag e.g. {…ns…}p

            # ---- paragraph ----
            if tag == P_TAG:
                para = Paragraph(child, doc)
                text = para.text.strip()

                if not text:
                    continue
                if title and text == title:
                    continue
                if text in pre_heading:
                    continue

                if self._is_heading(para):
                    flush()
                    current_heading = text
                elif self._is_subheading(para):
                    sub = Section(
                        id=str(uuid.uuid4()),
                        type=SectionType.UNKNOWN,
                        content="",
                        original_heading=text,
                        word_count=0,
                        is_subsection=True,
                    )
                    current_subsections.append(sub)
                else:
                    add_text(text)

            # ---- table ----
            elif tag == TBL_TAG:
                table_text = self._table_element_to_text(child, doc)
                if table_text:
                    add_text(table_text)

        flush()  # save last open section

        metadata = {
            "original_file": file_path,
            "file_type": "docx",
            "total_sections": len(sections),
            "total_words": sum(s.word_count for s in sections),
        }
        return ParsedDocument(sections=sections, metadata=metadata)

    # ------------------------------------------------------------------ #
    #  Table → plain text                                                  #
    # ------------------------------------------------------------------ #

    def _table_element_to_text(self, tbl_element, doc) -> str:
        """
        Convert a <w:tbl> element to a structured table marker.
        Handles merged cells correctly using the raw XML row/cell structure.
        """
        global _global_table_counter
        try:
            table = DocxTable(tbl_element, doc)
            if not table.rows:
                return ""

            num_cols = len(table.columns)
            lines = []

            for row in table.rows:
                # python-docx repeats the same _tc for merged cells in a row.
                # We deduplicate per-row using tc identity, keeping first occurrence.
                seen_in_row = {}
                ordered_cells = []
                for cell in row.cells:
                    tc_id = id(cell._tc)
                    if tc_id not in seen_in_row:
                        seen_in_row[tc_id] = cell.text.strip().replace("\n", " ")
                    ordered_cells.append(tc_id)

                # Build unique cell list in order
                unique_tcs = list(dict.fromkeys(ordered_cells))  # preserve order, deduplicate
                row_values = [seen_in_row[tc_id] for tc_id in unique_tcs]

                # Pad to num_cols if needed
                while len(row_values) < num_cols:
                    row_values.append("")

                lines.append("| " + " | ".join(row_values) + " |")

            if not lines:
                return ""

            _global_table_counter += 1
            return f"[[TABLE_START:{_global_table_counter}]]\n" + "\n".join(lines) + "\n[[TABLE_END]]"

        except Exception as exc:
            logger.warning(f"Table extraction failed: {exc}")
            return ""

    # ------------------------------------------------------------------ #
    #  Section builder                                                     #
    # ------------------------------------------------------------------ #

    def _make_section(
        self,
        heading: str,
        content_lines: List[str],
        subsections: List[Section],
    ) -> Section:
        content_text = "\n".join(content_lines).strip()
        section_type = self.detect_section_type(heading, content_text)
        return Section(
            id=str(uuid.uuid4()),
            type=section_type,
            content=content_text,
            original_heading=heading,
            word_count=len(content_text.split()) if content_text else 0,
            subsections=subsections if subsections else None,
        )

    # ------------------------------------------------------------------ #
    #  Paragraph style helpers                                             #
    # ------------------------------------------------------------------ #

    def _is_heading(self, para: Paragraph) -> bool:
        if para.style.name.startswith("Heading 1"):
            return True
        if para.runs:
            run = para.runs[0]
            if (run.bold
                    and len(para.text.strip()) < 100
                    and not para.style.name.startswith("Heading 2")):
                return True
        return False

    def _is_subheading(self, para: Paragraph) -> bool:
        return para.style.name.startswith("Heading 2")

    # ------------------------------------------------------------------ #
    #  Section-type detection                                              #
    # ------------------------------------------------------------------ #

    def detect_section_type(self, heading: str, content: str = "") -> SectionType:
        h = heading.lower().strip()
        h = re.sub(r"^[ivxlcdm]+\.\s+", "", h)
        h = re.sub(r"^\d+\.\s+", "", h)
        h = re.sub(r"^section\s+\d+:?\s*", "", h)
        h = h.strip()

        if any(k in h for k in ["abstract", "summary"]):           return SectionType.ABSTRACT
        if any(k in h for k in ["keyword", "index term"]):         return SectionType.KEYWORDS
        if "intro" in h:                                            return SectionType.INTRODUCTION
        if any(k in h for k in ["methodology", "methods", "approach", "method"]): return SectionType.METHODOLOGY
        if any(k in h for k in ["result", "finding", "experiment"]): return SectionType.RESULTS
        if any(k in h for k in ["conclusion", "concluding"]):      return SectionType.CONCLUSION
        if any(k in h for k in ["reference", "bibliography"]):     return SectionType.REFERENCES
        if any(k in h for k in ["related work", "background"]):    return SectionType.RELATED_WORK
        if "literature" in h:                                       return SectionType.LITERATURE_REVIEW
        if any(k in h for k in ["discussion", "analysis"]):        return SectionType.DISCUSSION
        if "future" in h:                                           return SectionType.FUTURE_WORK
        if "acknowledgment" in h or "acknowledgement" in h:        return SectionType.ACKNOWLEDGMENTS
        if "appendix" in h:                                         return SectionType.APPENDIX
        if "author" in h:                                           return SectionType.AUTHORS
        if "affiliation" in h:                                      return SectionType.AFFILIATION
        return SectionType.UNKNOWN

    # ------------------------------------------------------------------ #
    #  PDF (fallback)                                                      #
    # ------------------------------------------------------------------ #

    def _parse_pdf(self, file_path: str) -> ParsedDocument:
        try:
            import fitz
        except ImportError:
            logger.error("PyMuPDF not installed.")
            return ParsedDocument(sections=[], metadata={"error": "PyMuPDF not installed"})

        doc_pdf = fitz.open(file_path)
        raw_text = "".join(page.get_text() for page in doc_pdf)
        doc_pdf.close()

        lines = [l.strip() for l in raw_text.splitlines() if l.strip()]
        sections: List[Section] = []
        current_heading: Optional[str] = None
        current_content: List[str] = []
        title_done = False

        for line in lines:
            is_heading = (
                re.match(r'^[IVX]+\.\s+[A-Z]', line)
                or re.match(r'^\d+\.\s+[A-Z]', line)
                or (line.isupper() and 3 < len(line) < 60)
                or re.match(r'^(abstract|introduction|methodology|results|conclusion|references|discussion|acknowledgment)', line, re.I)
            )
            if is_heading:
                if not title_done and current_content:
                    sections.append(Section(id=str(uuid.uuid4()), type=SectionType.TITLE,
                                            content=current_content[0], word_count=len(current_content[0].split())))
                    if len(current_content) > 1:
                        auth = " ".join(current_content[1:])
                        sections.append(Section(id=str(uuid.uuid4()), type=SectionType.AUTHORS,
                                                content=auth, word_count=len(auth.split())))
                    title_done = True
                    current_content = []
                if current_heading:
                    body = "\n".join(current_content).strip()
                    sections.append(Section(id=str(uuid.uuid4()),
                                            type=self.detect_section_type(current_heading, body),
                                            content=body, original_heading=current_heading,
                                            word_count=len(body.split()) if body else 0))
                current_heading = line
                current_content = []
            else:
                current_content.append(line)

        if current_heading:
            body = "\n".join(current_content).strip()
            sections.append(Section(id=str(uuid.uuid4()),
                                    type=self.detect_section_type(current_heading, body),
                                    content=body, original_heading=current_heading,
                                    word_count=len(body.split()) if body else 0))

        return ParsedDocument(sections=sections,
                              metadata={"original_file": file_path, "file_type": "pdf",
                                        "total_sections": len(sections),
                                        "total_words": sum(s.word_count for s in sections)})
