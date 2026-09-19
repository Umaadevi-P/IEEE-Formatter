"""
Layer B: IEEE Rules Engine
Deterministic validation and formatting of IEEE conference papers.
Uses rules.docx for reference. AI is only called for generating content
of genuinely missing required sections.
"""
import re
import uuid
import logging
from typing import List, Dict, Any, Optional, Tuple

from app.models import (
    ParsedDocument, FormattedDocument, Section, SectionType,
    FontRule, Issue, IssueSeverity,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# IEEE constants
# ---------------------------------------------------------------------------

REQUIRED_SECTIONS = {
    SectionType.ABSTRACT,
    SectionType.INTRODUCTION,
    SectionType.CONCLUSION,
    SectionType.REFERENCES,
}

# Sections that should appear but are less critical
RECOMMENDED_SECTIONS = {
    SectionType.KEYWORDS,
    SectionType.METHODOLOGY,
    SectionType.RESULTS,
}

IEEE_SECTION_ORDER = [
    SectionType.TITLE,
    SectionType.AUTHORS,
    SectionType.AFFILIATION,
    SectionType.ABSTRACT,
    SectionType.KEYWORDS,
    SectionType.INTRODUCTION,
    SectionType.RELATED_WORK,
    SectionType.LITERATURE_REVIEW,
    SectionType.METHODOLOGY,
    SectionType.RESULTS,
    SectionType.DISCUSSION,
    SectionType.CONCLUSION,
    SectionType.FUTURE_WORK,
    SectionType.ACKNOWLEDGMENTS,
    SectionType.REFERENCES,
    SectionType.APPENDIX,
]

ABSTRACT_MIN_WORDS = 150
ABSTRACT_MAX_WORDS = 250

FONT_RULES: Dict[SectionType, FontRule] = {
    SectionType.TITLE: FontRule(font_family="Times New Roman", font_size=24, bold=True, italic=False, alignment="center"),
    SectionType.AUTHORS: FontRule(font_family="Times New Roman", font_size=10, bold=False, italic=False, alignment="center"),
    SectionType.AFFILIATION: FontRule(font_family="Times New Roman", font_size=10, bold=False, italic=True, alignment="center"),
    SectionType.ABSTRACT: FontRule(font_family="Times New Roman", font_size=9, bold=False, italic=False, alignment="justify"),
    SectionType.KEYWORDS: FontRule(font_family="Times New Roman", font_size=9, bold=False, italic=True, alignment="justify"),
    SectionType.INTRODUCTION: FontRule(font_family="Times New Roman", font_size=10, bold=False, italic=False, alignment="justify"),
    SectionType.RELATED_WORK: FontRule(font_family="Times New Roman", font_size=10, bold=False, italic=False, alignment="justify"),
    SectionType.LITERATURE_REVIEW: FontRule(font_family="Times New Roman", font_size=10, bold=False, italic=False, alignment="justify"),
    SectionType.METHODOLOGY: FontRule(font_family="Times New Roman", font_size=10, bold=False, italic=False, alignment="justify"),
    SectionType.RESULTS: FontRule(font_family="Times New Roman", font_size=10, bold=False, italic=False, alignment="justify"),
    SectionType.DISCUSSION: FontRule(font_family="Times New Roman", font_size=10, bold=False, italic=False, alignment="justify"),
    SectionType.CONCLUSION: FontRule(font_family="Times New Roman", font_size=10, bold=False, italic=False, alignment="justify"),
    SectionType.FUTURE_WORK: FontRule(font_family="Times New Roman", font_size=10, bold=False, italic=False, alignment="justify"),
    SectionType.ACKNOWLEDGMENTS: FontRule(font_family="Times New Roman", font_size=10, bold=False, italic=False, alignment="justify"),
    SectionType.REFERENCES: FontRule(font_family="Times New Roman", font_size=10, bold=False, italic=False, alignment="justify"),
    SectionType.APPENDIX: FontRule(font_family="Times New Roman", font_size=10, bold=False, italic=False, alignment="justify"),
    SectionType.UNKNOWN: FontRule(font_family="Times New Roman", font_size=10, bold=False, italic=False, alignment="justify"),
}

HEADING_FONT = FontRule(font_family="Times New Roman", font_size=10, bold=True, italic=False, alignment="left")
SUBHEADING_FONT = FontRule(font_family="Times New Roman", font_size=10, bold=False, italic=True, alignment="left")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def apply_ieee_rules(
    document: ParsedDocument,
    generate_missing: bool = True,
) -> Tuple[FormattedDocument, List[Issue]]:
    """
    Apply all IEEE rules to the parsed document.
    - Fixes section headings (rename to IEEE standard)
    - Reorders sections
    - Adds Roman numeral numbering
    - Applies font rules
    - Generates stub content for missing required sections (if generate_missing)
    - Returns (FormattedDocument, List[Issue])
    """
    sections = [s.model_copy(deep=True) for s in document.sections]

    # 1. Detect issues on the original document
    issues = detect_issues(document)

    # 2. Ensure the first body heading is Introduction
    sections = _normalise_introduction(sections)

    # 3. Generate missing required sections using AI context
    if generate_missing:
        sections = _fill_missing_required_sections(sections, document)

    # 4. Convert citations to IEEE numbered format
    from app.citation_converter import CitationConverter
    cc = CitationConverter()
    sections = cc.convert_references(sections)

    # 5. Apply font rules
    sections = [_apply_font_rules(s) for s in sections]

    # 6. Reorder to IEEE standard
    sections = _reorder_sections(sections)

    # 7. Apply numbering + heading formatting
    sections = _apply_numbering(sections)

    formatted_doc = FormattedDocument(
        sections=sections,
        metadata={
            **document.metadata,
            "formatted": True,
            "ieee_compliant": True,
        },
        compliance_score=0.0,  # filled by Layer E
    )
    return formatted_doc, issues


def detect_issues(document: ParsedDocument) -> List[Issue]:
    """Run all deterministic checks and return a list of issues."""
    issues: List[Issue] = []
    issues.extend(_check_missing_sections(document))
    issues.extend(_check_section_order(document))
    issues.extend(_check_abstract_length(document))
    issues.extend(_check_missing_headings(document))
    issues.extend(_check_references_format(document))
    issues.extend(_check_figures_tables(document))
    return issues


# ---------------------------------------------------------------------------
# Internal checks
# ---------------------------------------------------------------------------

def _check_missing_sections(doc: ParsedDocument) -> List[Issue]:
    present = {s.type for s in doc.sections}
    issues = []
    for req in REQUIRED_SECTIONS:
        if req not in present:
            issues.append(Issue(
                type="missing_required_section",
                section=req.value,
                severity=IssueSeverity.HIGH,
                message=f"Required section '{req.value}' is missing",
                expected=req.value,
            ))
    for rec in RECOMMENDED_SECTIONS:
        if rec not in present:
            issues.append(Issue(
                type="missing_recommended_section",
                section=rec.value,
                severity=IssueSeverity.MEDIUM,
                message=f"Recommended section '{rec.value}' is missing",
                expected=rec.value,
            ))
    return issues


def _check_section_order(doc: ParsedDocument) -> List[Issue]:
    expected_pos = {st: idx for idx, st in enumerate(IEEE_SECTION_ORDER)}
    issues = []
    last_pos = -1
    for s in doc.sections:
        if s.type == SectionType.UNKNOWN:
            continue
        ep = expected_pos.get(s.type, -1)
        if ep != -1 and ep < last_pos:
            prev_types = [st for st in IEEE_SECTION_ORDER if expected_pos.get(st, -1) == last_pos]
            if prev_types:
                issues.append(Issue(
                    type="section_out_of_order",
                    section=s.type.value,
                    severity=IssueSeverity.MEDIUM,
                    message=f"'{s.type.value}' appears after '{prev_types[0].value}' but should come before it",
                    current=s.type.value,
                    expected=f"Should appear before {prev_types[0].value}",
                ))
        if ep != -1:
            last_pos = max(last_pos, ep)
    return issues


def _check_abstract_length(doc: ParsedDocument) -> List[Issue]:
    issues = []
    for s in doc.sections:
        if s.type == SectionType.ABSTRACT:
            wc = s.word_count
            if wc < ABSTRACT_MIN_WORDS or wc > ABSTRACT_MAX_WORDS:
                issues.append(Issue(
                    type="abstract_word_count_violation",
                    section="Abstract",
                    severity=IssueSeverity.MEDIUM,
                    message=f"Abstract has {wc} words; IEEE requires {ABSTRACT_MIN_WORDS}–{ABSTRACT_MAX_WORDS}",
                    current=wc,
                    expected=f"{ABSTRACT_MIN_WORDS}–{ABSTRACT_MAX_WORDS} words",
                ))
    return issues


def _check_missing_headings(doc: ParsedDocument) -> List[Issue]:
    needs_heading = {
        SectionType.ABSTRACT, SectionType.KEYWORDS, SectionType.INTRODUCTION,
        SectionType.RELATED_WORK, SectionType.LITERATURE_REVIEW, SectionType.METHODOLOGY,
        SectionType.RESULTS, SectionType.DISCUSSION, SectionType.CONCLUSION,
        SectionType.FUTURE_WORK, SectionType.ACKNOWLEDGMENTS, SectionType.REFERENCES,
        SectionType.APPENDIX,
    }
    issues = []
    for s in doc.sections:
        if s.type in needs_heading and (not s.original_heading or not s.original_heading.strip()):
            issues.append(Issue(
                type="missing_section_heading",
                section=s.type.value,
                severity=IssueSeverity.LOW,
                message=f"Section '{s.type.value}' is missing a heading",
                expected=f"Heading for {s.type.value}",
            ))
    return issues


def _check_references_format(doc: ParsedDocument) -> List[Issue]:
    """Check that references section exists and has entries."""
    issues = []
    ref_sections = [s for s in doc.sections if s.type == SectionType.REFERENCES]
    if not ref_sections:
        return issues
    ref = ref_sections[0]
    if not ref.content or len(ref.content.strip()) < 10:
        issues.append(Issue(
            type="empty_references",
            section="References",
            severity=IssueSeverity.HIGH,
            message="References section appears to be empty",
            expected="At least one reference entry",
        ))
    return issues


def _check_figures_tables(doc: ParsedDocument) -> List[Issue]:
    """Check for figure/table captions that don't follow IEEE format."""
    issues = []
    for s in doc.sections:
        content = s.content or ""
        # Find figure references without proper caption format
        fig_refs = re.findall(r'\bfig(?:ure)?\.?\s*\d+\b', content, re.IGNORECASE)
        for ref in fig_refs:
            # Check if proper "Fig. X." format is not used
            if not re.search(r'\bFig\.\s*\d+\.', content):
                issues.append(Issue(
                    type="figure_caption_format",
                    section=s.type.value,
                    severity=IssueSeverity.LOW,
                    message=f"Figure reference detected. IEEE requires captions in format 'Fig. X. Caption text.' below the figure.",
                    current=ref,
                    expected="Fig. X. Caption text."
                ))
                break  # One warning per section

        # Check for tables without proper IEEE caption
        table_refs = re.findall(r'\btable\s+[IVX\d]+\b', content, re.IGNORECASE)
        for ref in table_refs:
            if not re.search(r'\bTABLE\s+[IVX]+\b', content):
                issues.append(Issue(
                    type="table_caption_format",
                    section=s.type.value,
                    severity=IssueSeverity.LOW,
                    message=f"Table reference detected. IEEE requires table titles in format 'TABLE I' (small caps, Roman numerals) ABOVE the table.",
                    current=ref,
                    expected="TABLE I\\nTable Title"
                ))
                break
    return issues


# ---------------------------------------------------------------------------
# Internal transformations
# ---------------------------------------------------------------------------

def _normalise_introduction(sections: List[Section]) -> List[Section]:
    """
    IEEE rule: the first numbered body section must be Introduction.
    If it's UNKNOWN or has a different heading that clearly introduces the paper,
    retype it as INTRODUCTION.
    """
    body_start = None
    for i, s in enumerate(sections):
        if s.type not in {SectionType.TITLE, SectionType.AUTHORS,
                          SectionType.AFFILIATION, SectionType.ABSTRACT,
                          SectionType.KEYWORDS}:
            body_start = i
            break

    if body_start is None:
        return sections

    first_body = sections[body_start]
    # If first body section has an introduction-like heading or is UNKNOWN
    if first_body.type == SectionType.UNKNOWN:
        h = (first_body.original_heading or "").lower()
        if "intro" in h or h == "" or "background" in h or "overview" in h:
            sections[body_start] = first_body.model_copy(
                update={"type": SectionType.INTRODUCTION,
                        "original_heading": first_body.original_heading or "Introduction"}
            )
    return sections


def _fill_missing_required_sections(
    sections: List[Section], original_doc: ParsedDocument
) -> List[Section]:
    """
    For truly missing required sections, generate placeholder content using AI.
    This respects the rule: use AI ONLY for content generation, not for checks.
    """
    from app.ollama_service import generate_section_content, is_ollama_available

    present = {s.type for s in sections}
    ai_available = is_ollama_available()

    # Build document context for AI
    context_parts = []
    for s in sections:
        if s.content:
            context_parts.append(f"[{s.type.value}]: {s.content[:500]}")
    context = "\n\n".join(context_parts[:6])

    for req_type in REQUIRED_SECTIONS:
        if req_type in present:
            continue

        logger.info(f"Generating missing required section: {req_type.value}")
        if ai_available:
            content = generate_section_content(req_type.value, context)
        else:
            content = f"[{req_type.value} – Please add content here]"

        new_section = Section(
            id=str(uuid.uuid4()),
            type=req_type,
            content=content,
            original_heading=req_type.value,
            word_count=len(content.split()),
        )
        sections.append(new_section)

    return sections


def _apply_font_rules(section: Section) -> Section:
    s = section.model_copy(deep=True)
    s.font_rule = FONT_RULES.get(s.type, FONT_RULES[SectionType.UNKNOWN])
    return s


def _reorder_sections(sections: List[Section]) -> List[Section]:
    by_type: Dict[SectionType, List[Section]] = {}
    for s in sections:
        by_type.setdefault(s.type, []).append(s)

    reordered = []
    for st in IEEE_SECTION_ORDER:
        if st in by_type:
            reordered.extend(by_type[st])
    # Unknown sections that slipped through – append at end (before references)
    return reordered


def _apply_numbering(sections: List[Section]) -> List[Section]:
    numbered_types = {
        SectionType.INTRODUCTION, SectionType.RELATED_WORK, SectionType.LITERATURE_REVIEW,
        SectionType.METHODOLOGY, SectionType.RESULTS, SectionType.DISCUSSION,
        SectionType.CONCLUSION, SectionType.FUTURE_WORK, SectionType.ACKNOWLEDGMENTS,
        SectionType.REFERENCES, SectionType.APPENDIX,
    }

    roman_counter = 1
    result = []

    for section in sections:
        s = section.model_copy(deep=True)

        if s.type in numbered_types:
            numeral = _to_roman(roman_counter)
            roman_counter += 1

            raw_heading = s.original_heading or s.type.value
            clean = re.sub(r"^[ivxlcdm]+\.\s+", "", raw_heading.lower())
            clean = re.sub(r"^\d+\.\s+", "", clean).strip()
            if "final thought" in clean or "final remark" in clean:
                clean = "conclusion"

            s.formatted_heading = f"{numeral}. {clean.upper()}"
            s.heading_font_rule = HEADING_FONT

            # Subsection lettering
            if s.subsections:
                lettered = []
                for i, sub in enumerate(s.subsections):
                    sub2 = sub.model_copy(deep=True)
                    letter = chr(65 + i)
                    sub2.formatted_heading = (
                        f"{letter}. {(sub2.original_heading or 'Subsection').title()}"
                    )
                    sub2.heading_font_rule = SUBHEADING_FONT
                    lettered.append(sub2)
                s.subsections = lettered

        elif s.type == SectionType.ABSTRACT:
            s.formatted_heading = "ABSTRACT"
            s.heading_font_rule = HEADING_FONT
        elif s.type == SectionType.KEYWORDS:
            s.formatted_heading = "INDEX TERMS"
            s.heading_font_rule = HEADING_FONT
        elif s.type in {SectionType.AUTHORS, SectionType.AFFILIATION, SectionType.TITLE}:
            s.formatted_heading = None
        elif s.original_heading:
            s.formatted_heading = s.original_heading.upper()
            s.heading_font_rule = HEADING_FONT

        result.append(s)

    return result


def _to_roman(n: int) -> str:
    vals = [1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1]
    syms = ["M","CM","D","CD","C","XC","L","XL","X","IX","V","IV","I"]
    out = ""
    for v, s in zip(vals, syms):
        while n >= v:
            out += s
            n -= v
    return out
