"""Unit tests for compliance scoring"""
import pytest
from app.compliance_scorer import ComplianceScorer
from app.models import FormattedDocument, Section, SectionType, Issue, IssueSeverity


def test_compliance_score_weights_sum_to_one():
    """Test that component weights sum to 1.0"""
    scorer = ComplianceScorer()
    
    total_weight = sum(scorer.WEIGHTS.values())
    assert abs(total_weight - 1.0) < 0.001  # Allow for floating point precision


def test_perfect_compliance_score():
    """Test compliance score for a perfect document"""
    scorer = ComplianceScorer()
    
    # Create a perfect document with all required sections in correct order
    doc = FormattedDocument(
        sections=[
            Section(id="1", type=SectionType.TITLE, content="Title", word_count=1, formatted_heading=None),
            Section(id="2", type=SectionType.ABSTRACT, content=" ".join(["word"] * 200), 
                   original_heading="Abstract", formatted_heading="ABSTRACT", word_count=200),
            Section(id="3", type=SectionType.KEYWORDS, content="keywords", 
                   original_heading="Keywords", formatted_heading="KEYWORDS", word_count=1),
            Section(id="4", type=SectionType.INTRODUCTION, content="intro", 
                   original_heading="Introduction", formatted_heading="I. INTRODUCTION", word_count=1),
            Section(id="5", type=SectionType.METHODOLOGY, content="methods", 
                   original_heading="Methodology", formatted_heading="II. METHODOLOGY", word_count=1),
            Section(id="6", type=SectionType.RESULTS, content="results", 
                   original_heading="Results", formatted_heading="III. RESULTS", word_count=1),
            Section(id="7", type=SectionType.CONCLUSION, content="conclusion", 
                   original_heading="Conclusion", formatted_heading="IV. CONCLUSION", word_count=1),
            Section(id="8", type=SectionType.REFERENCES, content="refs", 
                   original_heading="References", formatted_heading="V. REFERENCES", word_count=1)
        ],
        metadata={},
        compliance_score=0.0
    )
    
    issues = []  # No issues
    
    score = scorer.calculate(doc, issues)
    
    # Should have perfect score (100%)
    assert score.score == 100.0
    assert score.breakdown["required_sections"] == 1.0
    assert score.breakdown["section_order"] == 1.0
    assert score.breakdown["abstract_compliance"] == 1.0
    assert score.breakdown["heading_hierarchy"] == 1.0
    assert score.breakdown["formatting_consistency"] == 1.0


def test_compliance_score_missing_sections():
    """Test compliance score when required sections are missing"""
    scorer = ComplianceScorer()
    
    # Create document missing several required sections
    doc = FormattedDocument(
        sections=[
            Section(id="1", type=SectionType.TITLE, content="Title", word_count=1),
            Section(id="2", type=SectionType.INTRODUCTION, content="intro", 
                   original_heading="Introduction", formatted_heading="I. INTRODUCTION", word_count=1)
        ],
        metadata={},
        compliance_score=0.0
    )
    
    issues = [
        Issue(type="missing_required_section", section="Abstract", 
              severity=IssueSeverity.HIGH, message="Missing Abstract"),
        Issue(type="missing_required_section", section="Keywords", 
              severity=IssueSeverity.HIGH, message="Missing Keywords"),
        Issue(type="missing_required_section", section="Methodology", 
              severity=IssueSeverity.HIGH, message="Missing Methodology"),
        Issue(type="missing_required_section", section="Results", 
              severity=IssueSeverity.HIGH, message="Missing Results"),
        Issue(type="missing_required_section", section="Conclusion", 
              severity=IssueSeverity.HIGH, message="Missing Conclusion"),
        Issue(type="missing_required_section", section="References", 
              severity=IssueSeverity.HIGH, message="Missing References")
    ]
    
    score = scorer.calculate(doc, issues)
    
    # Required sections score should be low (1/7 = ~0.14)
    assert score.breakdown["required_sections"] < 0.2
    
    # Formatting consistency should be 0 (6 high-severity issues * 0.2 = 1.2 penalty)
    assert score.breakdown["formatting_consistency"] == 0.0
    
    # Overall score should be low
    assert score.score < 50.0


def test_compliance_score_out_of_order():
    """Test compliance score when sections are out of order"""
    scorer = ComplianceScorer()
    
    # Create document with all sections but out of order
    doc = FormattedDocument(
        sections=[
            Section(id="1", type=SectionType.TITLE, content="Title", word_count=1),
            Section(id="2", type=SectionType.ABSTRACT, content=" ".join(["word"] * 200), 
                   original_heading="Abstract", formatted_heading="ABSTRACT", word_count=200),
            Section(id="3", type=SectionType.KEYWORDS, content="keywords", 
                   original_heading="Keywords", formatted_heading="KEYWORDS", word_count=1),
            Section(id="4", type=SectionType.INTRODUCTION, content="intro", 
                   original_heading="Introduction", formatted_heading="I. INTRODUCTION", word_count=1),
            Section(id="5", type=SectionType.METHODOLOGY, content="methods", 
                   original_heading="Methodology", formatted_heading="II. METHODOLOGY", word_count=1),
            Section(id="6", type=SectionType.RESULTS, content="results", 
                   original_heading="Results", formatted_heading="III. RESULTS", word_count=1),
            Section(id="7", type=SectionType.CONCLUSION, content="conclusion", 
                   original_heading="Conclusion", formatted_heading="IV. CONCLUSION", word_count=1),
            Section(id="8", type=SectionType.REFERENCES, content="refs", 
                   original_heading="References", formatted_heading="V. REFERENCES", word_count=1)
        ],
        metadata={},
        compliance_score=0.0
    )
    
    issues = [
        Issue(type="section_out_of_order", section="Results", 
              severity=IssueSeverity.MEDIUM, message="Results out of order")
    ]
    
    score = scorer.calculate(doc, issues)
    
    # Section order score should be 0.7 (partial credit)
    assert score.breakdown["section_order"] == 0.7
    
    # Other components should be perfect
    assert score.breakdown["required_sections"] == 1.0
    assert score.breakdown["abstract_compliance"] == 1.0


def test_compliance_score_abstract_out_of_range():
    """Test compliance score when abstract word count is out of range"""
    scorer = ComplianceScorer()
    
    # Create document with short abstract
    doc = FormattedDocument(
        sections=[
            Section(id="1", type=SectionType.TITLE, content="Title", word_count=1),
            Section(id="2", type=SectionType.ABSTRACT, content="Short abstract", 
                   original_heading="Abstract", formatted_heading="ABSTRACT", word_count=2),
            Section(id="3", type=SectionType.KEYWORDS, content="keywords", 
                   original_heading="Keywords", formatted_heading="KEYWORDS", word_count=1),
            Section(id="4", type=SectionType.INTRODUCTION, content="intro", 
                   original_heading="Introduction", formatted_heading="I. INTRODUCTION", word_count=1),
            Section(id="5", type=SectionType.METHODOLOGY, content="methods", 
                   original_heading="Methodology", formatted_heading="II. METHODOLOGY", word_count=1),
            Section(id="6", type=SectionType.RESULTS, content="results", 
                   original_heading="Results", formatted_heading="III. RESULTS", word_count=1),
            Section(id="7", type=SectionType.CONCLUSION, content="conclusion", 
                   original_heading="Conclusion", formatted_heading="IV. CONCLUSION", word_count=1),
            Section(id="8", type=SectionType.REFERENCES, content="refs", 
                   original_heading="References", formatted_heading="V. REFERENCES", word_count=1)
        ],
        metadata={},
        compliance_score=0.0
    )
    
    issues = []
    
    score = scorer.calculate(doc, issues)
    
    # Abstract compliance score should be 0.6 (partial credit)
    assert score.breakdown["abstract_compliance"] == 0.6


def test_compliance_score_range():
    """Test that compliance score is always between 0 and 100"""
    scorer = ComplianceScorer()
    
    # Create worst-case document
    doc = FormattedDocument(
        sections=[
            Section(id="1", type=SectionType.TITLE, content="Title", word_count=1)
        ],
        metadata={},
        compliance_score=0.0
    )
    
    # Many high-severity issues
    issues = [
        Issue(type="missing_required_section", section=f"Section{i}", 
              severity=IssueSeverity.HIGH, message=f"Missing Section {i}")
        for i in range(10)
    ]
    
    score = scorer.calculate(doc, issues)
    
    # Score should be between 0 and 100
    assert 0.0 <= score.score <= 100.0


def test_compliance_score_missing_headings():
    """Test compliance score when sections are missing formatted headings"""
    scorer = ComplianceScorer()
    
    # Create document with sections but no formatted headings
    doc = FormattedDocument(
        sections=[
            Section(id="1", type=SectionType.TITLE, content="Title", word_count=1),
            Section(id="2", type=SectionType.ABSTRACT, content=" ".join(["word"] * 200), 
                   original_heading="Abstract", formatted_heading=None, word_count=200),
            Section(id="3", type=SectionType.KEYWORDS, content="keywords", 
                   original_heading="Keywords", formatted_heading=None, word_count=1),
            Section(id="4", type=SectionType.INTRODUCTION, content="intro", 
                   original_heading="Introduction", formatted_heading=None, word_count=1),
            Section(id="5", type=SectionType.METHODOLOGY, content="methods", 
                   original_heading="Methodology", formatted_heading=None, word_count=1),
            Section(id="6", type=SectionType.RESULTS, content="results", 
                   original_heading="Results", formatted_heading=None, word_count=1),
            Section(id="7", type=SectionType.CONCLUSION, content="conclusion", 
                   original_heading="Conclusion", formatted_heading=None, word_count=1),
            Section(id="8", type=SectionType.REFERENCES, content="refs", 
                   original_heading="References", formatted_heading=None, word_count=1)
        ],
        metadata={},
        compliance_score=0.0
    )
    
    issues = []
    
    score = scorer.calculate(doc, issues)
    
    # Heading hierarchy score should be 0 (no formatted headings)
    assert score.breakdown["heading_hierarchy"] == 0.0
