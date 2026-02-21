"""Pydantic models for IEEE Paper Formatter"""
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from enum import Enum


class SectionType(str, Enum):
    TITLE = "Title"
    AUTHORS = "Authors"
    AFFILIATION = "Affiliation"
    ABSTRACT = "Abstract"
    KEYWORDS = "Keywords"
    INTRODUCTION = "Introduction"
    RELATED_WORK = "Related Work"
    LITERATURE_REVIEW = "Literature Review"
    METHODOLOGY = "Methodology"
    RESULTS = "Results"
    DISCUSSION = "Discussion"
    CONCLUSION = "Conclusion"
    FUTURE_WORK = "Future Work"
    ACKNOWLEDGMENTS = "Acknowledgments"
    REFERENCES = "References"
    APPENDIX = "Appendix"
    UNKNOWN = "Unknown"


class FontRule(BaseModel):
    font_family: str  # "Times New Roman"
    font_size: int    # 10, 24, etc.
    bold: bool
    italic: bool
    alignment: str    # "left", "center", "justify"


class Section(BaseModel):
    id: str
    type: SectionType
    content: str
    original_heading: Optional[str] = None
    formatted_heading: Optional[str] = None
    word_count: int = 0
    font_rule: Optional[FontRule] = None
    heading_font_rule: Optional[FontRule] = None  # Font rule specifically for the heading
    subsections: Optional[List['Section']] = None  # Support for nested subsections
    is_subsection: bool = False  # Flag to indicate if this is a subsection


class ParsedDocument(BaseModel):
    sections: List[Section]
    metadata: Dict[str, Any]


class FormattedDocument(BaseModel):
    sections: List[Section]
    metadata: Dict[str, Any]
    compliance_score: float


class IssueSeverity(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Issue(BaseModel):
    type: str
    section: Optional[str] = None
    severity: IssueSeverity
    message: str
    current: Optional[Any] = None
    expected: Optional[Any] = None


class Fix(BaseModel):
    section_id: str
    type: str
    original: Optional[str] = None
    formatted: Optional[str] = None
    reason: str


class ComplianceScore(BaseModel):
    score: float  # 0-100
    breakdown: Dict[str, float]
    weights: Dict[str, float]


class ProcessingResult(BaseModel):
    status: str
    document_before: ParsedDocument
    document_after: FormattedDocument
    issues: List[Issue]
    fixes: List[Fix]
    compliance: ComplianceScore
    metadata: Dict[str, Any]


class UserEdits(BaseModel):
    """User-provided corrections and additions"""
    author_name: Optional[str] = None
    author_email: Optional[str] = None
    affiliation: Optional[str] = None
    keywords: Optional[List[str]] = None
    section_corrections: Optional[Dict[str, SectionType]] = None


class UploadResponse(BaseModel):
    """Response after document upload and initial processing"""
    processing_result: ProcessingResult


class ApplyEditsRequest(BaseModel):
    """User corrections to apply before final formatting"""
    document_id: str
    edits: UserEdits


class ExportRequest(BaseModel):
    """Request to export formatted document"""
    document_id: str
    format: str  # "docx" or "pdf"


class AskAIRequest(BaseModel):
    """Request for AI assistance on specific section"""
    section_id: str
    selected_text: str
    question: str


class AskAIResponse(BaseModel):
    answer: str
    suggestion: Optional[str] = None
    explanation: str
    confidence: float
