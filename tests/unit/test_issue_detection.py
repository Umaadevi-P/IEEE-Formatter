"""Unit tests for issue detection"""
import pytest
from app.issue_detector import IssueDetector
from app.models import ParsedDocument, Section, SectionType, IssueSeverity


def test_detect_missing_required_sections():
    """Test detection of missing required sections"""
    detector = IssueDetector()
    
    # Create document with only title and introduction
    doc = ParsedDocument(
        sections=[
            Section(
                id="1",
                type=SectionType.TITLE,
                content="Test Paper",
                word_count=2
            ),
            Section(
                id="2",
                type=SectionType.INTRODUCTION,
                content="This is the introduction.",
                original_heading="Introduction",
                word_count=4
            )
        ],
        metadata={}
    )
    
    issues = detector.detect_issues(doc)
    
    # Should detect missing: Abstract, Keywords, Methodology, Results, Conclusion, References
    missing_section_issues = [i for i in issues if i.type == "missing_required_section"]
    assert len(missing_section_issues) == 6
    
    # All should be high severity
    for issue in missing_section_issues:
        assert issue.severity == IssueSeverity.HIGH


def test_detect_abstract_word_count_violation_too_short():
    """Test detection of abstract that is too short"""
    detector = IssueDetector()
    
    # Create document with short abstract (< 150 words)
    doc = ParsedDocument(
        sections=[
            Section(
                id="1",
                type=SectionType.ABSTRACT,
                content="This is a very short abstract.",
                original_heading="Abstract",
                word_count=6
            )
        ],
        metadata={}
    )
    
    issues = detector.detect_issues(doc)
    
    # Should detect abstract word count violation
    abstract_issues = [i for i in issues if i.type == "abstract_word_count_violation"]
    assert len(abstract_issues) == 1
    assert abstract_issues[0].severity == IssueSeverity.MEDIUM
    assert abstract_issues[0].current == 6


def test_detect_abstract_word_count_violation_too_long():
    """Test detection of abstract that is too long"""
    detector = IssueDetector()
    
    # Create document with long abstract (> 250 words)
    long_content = " ".join(["word"] * 300)
    doc = ParsedDocument(
        sections=[
            Section(
                id="1",
                type=SectionType.ABSTRACT,
                content=long_content,
                original_heading="Abstract",
                word_count=300
            )
        ],
        metadata={}
    )
    
    issues = detector.detect_issues(doc)
    
    # Should detect abstract word count violation
    abstract_issues = [i for i in issues if i.type == "abstract_word_count_violation"]
    assert len(abstract_issues) == 1
    assert abstract_issues[0].severity == IssueSeverity.MEDIUM
    assert abstract_issues[0].current == 300


def test_detect_section_order_issues():
    """Test detection of out-of-order sections"""
    detector = IssueDetector()
    
    # Create document with sections out of order (Conclusion before Results)
    doc = ParsedDocument(
        sections=[
            Section(
                id="1",
                type=SectionType.INTRODUCTION,
                content="Introduction content",
                original_heading="Introduction",
                word_count=2
            ),
            Section(
                id="2",
                type=SectionType.CONCLUSION,
                content="Conclusion content",
                original_heading="Conclusion",
                word_count=2
            ),
            Section(
                id="3",
                type=SectionType.RESULTS,
                content="Results content",
                original_heading="Results",
                word_count=2
            )
        ],
        metadata={}
    )
    
    issues = detector.detect_issues(doc)
    
    # Should detect section order issue
    order_issues = [i for i in issues if i.type == "section_out_of_order"]
    assert len(order_issues) >= 1
    
    # Should be medium severity
    for issue in order_issues:
        assert issue.severity == IssueSeverity.MEDIUM


def test_detect_missing_headings():
    """Test detection of missing section headings"""
    detector = IssueDetector()
    
    # Create document with section missing heading
    doc = ParsedDocument(
        sections=[
            Section(
                id="1",
                type=SectionType.ABSTRACT,
                content="This is the abstract content.",
                original_heading=None,  # Missing heading
                word_count=5
            ),
            Section(
                id="2",
                type=SectionType.INTRODUCTION,
                content="This is the introduction.",
                original_heading="Introduction",  # Has heading
                word_count=4
            )
        ],
        metadata={}
    )
    
    issues = detector.detect_issues(doc)
    
    # Should detect missing heading for abstract
    heading_issues = [i for i in issues if i.type == "missing_section_heading"]
    assert len(heading_issues) == 1
    assert heading_issues[0].severity == IssueSeverity.LOW
    assert heading_issues[0].section == "Abstract"


def test_no_issues_for_compliant_document():
    """Test that a compliant document has no issues"""
    detector = IssueDetector()
    
    # Create a fully compliant document
    doc = ParsedDocument(
        sections=[
            Section(id="1", type=SectionType.TITLE, content="Title", word_count=1),
            Section(id="2", type=SectionType.ABSTRACT, content=" ".join(["word"] * 200), 
                   original_heading="Abstract", word_count=200),
            Section(id="3", type=SectionType.KEYWORDS, content="keywords", 
                   original_heading="Keywords", word_count=1),
            Section(id="4", type=SectionType.INTRODUCTION, content="intro", 
                   original_heading="Introduction", word_count=1),
            Section(id="5", type=SectionType.METHODOLOGY, content="methods", 
                   original_heading="Methodology", word_count=1),
            Section(id="6", type=SectionType.RESULTS, content="results", 
                   original_heading="Results", word_count=1),
            Section(id="7", type=SectionType.CONCLUSION, content="conclusion", 
                   original_heading="Conclusion", word_count=1),
            Section(id="8", type=SectionType.REFERENCES, content="refs", 
                   original_heading="References", word_count=1)
        ],
        metadata={}
    )
    
    issues = detector.detect_issues(doc)
    
    # Should have no issues
    assert len(issues) == 0
