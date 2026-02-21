"""Integration tests for issue detection and compliance scoring"""
import pytest
from app.parser import DocumentParser
from app.formatter import IEEEFormatter
from app.issue_detector import IssueDetector
from app.compliance_scorer import ComplianceScorer
from app.models import SectionType
import os


def test_full_pipeline_with_sample_document():
    """Test the full pipeline: parse -> format -> detect issues -> score compliance"""
    # Use a sample document from uploads
    sample_file = "uploads/Meteor_Shower_Review_Wrong_Format_Exaggerated.docx"
    
    if not os.path.exists(sample_file):
        pytest.skip(f"Sample file {sample_file} not found")
    
    # Parse document
    parser = DocumentParser()
    parsed_doc = parser.parse(sample_file)
    
    assert len(parsed_doc.sections) > 0
    
    # Format document
    formatter = IEEEFormatter("rules.docx")
    formatted_doc = formatter.format(parsed_doc)
    
    assert len(formatted_doc.sections) > 0
    
    # Detect issues
    detector = IssueDetector()
    issues = detector.detect_issues(parsed_doc)
    
    # Issues should be a list (may be empty or have items)
    assert isinstance(issues, list)
    
    # Calculate compliance score
    scorer = ComplianceScorer()
    compliance = scorer.calculate(formatted_doc, issues)
    
    # Verify compliance score structure
    assert 0.0 <= compliance.score <= 100.0
    assert "required_sections" in compliance.breakdown
    assert "section_order" in compliance.breakdown
    assert "abstract_compliance" in compliance.breakdown
    assert "heading_hierarchy" in compliance.breakdown
    assert "formatting_consistency" in compliance.breakdown
    
    # Verify weights sum to 1.0
    total_weight = sum(compliance.weights.values())
    assert abs(total_weight - 1.0) < 0.001


def test_issue_detection_with_minimal_document():
    """Test issue detection with a minimal document"""
    detector = IssueDetector()
    
    # Create minimal parsed document
    from app.models import ParsedDocument, Section
    
    doc = ParsedDocument(
        sections=[
            Section(
                id="1",
                type=SectionType.TITLE,
                content="Test Paper",
                word_count=2
            )
        ],
        metadata={}
    )
    
    issues = detector.detect_issues(doc)
    
    # Should detect many missing required sections
    missing_section_issues = [i for i in issues if i.type == "missing_required_section"]
    assert len(missing_section_issues) >= 5  # At least Abstract, Keywords, Intro, Methods, Results, Conclusion, References


def test_compliance_scoring_with_formatted_document():
    """Test compliance scoring with a properly formatted document"""
    from app.models import FormattedDocument, Section
    
    # Create a well-formatted document
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
    
    scorer = ComplianceScorer()
    compliance = scorer.calculate(doc, [])
    
    # Should have high compliance score
    assert compliance.score >= 95.0
    
    # All breakdown components should be high
    for component, score in compliance.breakdown.items():
        assert score >= 0.9, f"Component {component} has low score: {score}"
