"""
Layer E: Confidence Score Engine
Generates a "Submission Readiness Score" (0-100) based on:
  - IEEE formatting compliance (deterministic rules)
  - Grammar / writing quality (AI-assisted)
  - Completeness (required sections, abstract length, references)
  - Reference quality (count, format)
  - Structural correctness (section order, headings)

This score means: "How ready is this document for IEEE submission?"
NOT: "probability IEEE will accept the paper"
"""
import logging
from typing import List, Dict, Any

from app.models import (
    FormattedDocument, Issue, IssueSeverity, SectionType, ComplianceScore
)

logger = logging.getLogger(__name__)

# Component weights (must sum to 1.0)
WEIGHTS = {
    "completeness":    0.30,   # Required sections present
    "structure":       0.20,   # Section order + headings
    "abstract":        0.15,   # Abstract length compliance
    "references":      0.15,   # References present + count
    "grammar":         0.20,   # AI writing quality (falls back to heuristic)
}

# Human-readable descriptions for the UI
EXPLANATIONS_TEMPLATE = {
    "completeness":  "Measures whether all required IEEE sections (Abstract, Introduction, Conclusion, References) are present.",
    "structure":     "Checks that sections follow the IEEE standard order and have proper headings.",
    "abstract":      "Verifies the abstract falls within the IEEE word count range (150–250 words).",
    "references":    "Checks that a References section exists and contains numbered entries.",
    "grammar":       "AI-assessed grammar quality, clarity, and academic writing tone.",
}


def calculate_readiness_score(
    document: FormattedDocument,
    issues: List[Issue],
    ai_quality: Dict[str, Any] = None,
) -> ComplianceScore:
    """
    Calculate the submission readiness score.

    Parameters
    ----------
    document   : the formatted document
    issues     : list of issues detected by the rules engine
    ai_quality : dict from ollama_service.assess_writing_quality()
                 expected keys: grammar_score, clarity_score, academic_tone_score
    """
    breakdown: Dict[str, float] = {}

    # 1. Completeness score
    breakdown["completeness"] = _score_completeness(document)

    # 2. Structure score
    breakdown["structure"] = _score_structure(document, issues)

    # 3. Abstract compliance
    breakdown["abstract"] = _score_abstract(document)

    # 4. References quality
    breakdown["references"] = _score_references(document)

    # 5. Grammar / writing quality
    breakdown["grammar"] = _score_grammar(document, ai_quality)

    # Weighted total
    total = sum(breakdown[k] * WEIGHTS[k] for k in WEIGHTS) * 100
    total = round(max(0.0, min(100.0, total)), 1)

    # Build human-readable explanations for the score panel
    explanations: Dict[str, str] = {}
    for key, base_text in EXPLANATIONS_TEMPLATE.items():
        pct = round(breakdown[key] * 100)
        status = "✓ Good" if pct >= 80 else ("⚠ Fair" if pct >= 50 else "✗ Needs work")
        explanations[key] = f"{status} ({pct}%) — {base_text}"

    return ComplianceScore(
        score=total,
        breakdown={k: round(v * 100, 1) for k, v in breakdown.items()},
        weights=WEIGHTS,
        explanations=explanations,
    )


# ---------------------------------------------------------------------------
# Sub-scorers
# ---------------------------------------------------------------------------

REQUIRED_SECTIONS = {
    SectionType.ABSTRACT,
    SectionType.INTRODUCTION,
    SectionType.CONCLUSION,
    SectionType.REFERENCES,
}

EXTRA_SECTIONS = {
    SectionType.KEYWORDS,
    SectionType.METHODOLOGY,
    SectionType.RESULTS,
}


def _score_completeness(doc: FormattedDocument) -> float:
    present = {s.type for s in doc.sections}
    # Required sections: 80% weight
    req_present = len(REQUIRED_SECTIONS & present)
    req_score = req_present / len(REQUIRED_SECTIONS)

    # Extra recommended sections: 20% weight
    extra_present = len(EXTRA_SECTIONS & present)
    extra_score = extra_present / len(EXTRA_SECTIONS)

    return 0.8 * req_score + 0.2 * extra_score


def _score_structure(doc: FormattedDocument, issues: List[Issue]) -> float:
    order_issues = sum(1 for i in issues if i.type == "section_out_of_order")
    heading_issues = sum(1 for i in issues if i.type == "missing_section_heading")

    order_score = max(0.0, 1.0 - 0.15 * order_issues)
    heading_score = max(0.0, 1.0 - 0.1 * heading_issues)
    return 0.6 * order_score + 0.4 * heading_score


def _score_abstract(doc: FormattedDocument) -> float:
    abstracts = [s for s in doc.sections if s.type == SectionType.ABSTRACT]
    if not abstracts:
        return 0.0
    wc = abstracts[0].word_count
    if 150 <= wc <= 250:
        return 1.0
    if wc < 150:
        return max(0.3, wc / 150)
    # Over 250
    return max(0.5, 1.0 - (wc - 250) / 500)


def _score_references(doc: FormattedDocument) -> float:
    ref_sections = [s for s in doc.sections if s.type == SectionType.REFERENCES]
    if not ref_sections:
        return 0.0
    content = ref_sections[0].content or ""
    # Count numbered references [1], [2], ...
    import re
    count = len(re.findall(r'\[\d+\]', content))
    if count == 0:
        # Try counting line-by-line entries
        lines = [l.strip() for l in content.splitlines() if l.strip()]
        count = len(lines)

    if count >= 10:
        return 1.0
    if count >= 5:
        return 0.8
    if count >= 1:
        return 0.5
    return 0.2


def _score_grammar(doc: FormattedDocument, ai_quality: Dict[str, Any]) -> float:
    if ai_quality:
        g = ai_quality.get("grammar_score", 70) / 100
        c = ai_quality.get("clarity_score", 70) / 100
        a = ai_quality.get("academic_tone_score", 70) / 100
        return (g + c + a) / 3

    # Heuristic fallback: check average word count per section (fuller = better)
    body_types = {
        SectionType.INTRODUCTION, SectionType.METHODOLOGY,
        SectionType.RESULTS, SectionType.CONCLUSION
    }
    body_sections = [s for s in doc.sections if s.type in body_types]
    if not body_sections:
        return 0.6  # default mid-score

    avg_words = sum(s.word_count for s in body_sections) / len(body_sections)
    if avg_words >= 200:
        return 0.75
    if avg_words >= 100:
        return 0.65
    return 0.5
