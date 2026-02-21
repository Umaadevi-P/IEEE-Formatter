"""Unit tests for user edits application"""
import pytest
from app.user_edits import UserEditsApplicator
from app.models import (
    UserEdits,
    ParsedDocument,
    Section,
    SectionType,
    IssueSeverity
)
import uuid


def create_test_section(section_type: SectionType, content: str = "Test content") -> Section:
    """Helper to create a test section"""
    return Section(
        id=str(uuid.uuid4()),
        type=section_type,
        content=content,
        original_heading=section_type.value,
        word_count=len(content.split())
    )


def test_apply_author_info_to_existing_section():
    """Test applying author info when AUTHORS section already exists"""
    # Create document with existing AUTHORS section
    sections = [
        create_test_section(SectionType.TITLE, "Test Paper"),
        create_test_section(SectionType.AUTHORS, "Old Author"),
        create_test_section(SectionType.ABSTRACT, "Abstract content")
    ]
    document = ParsedDocument(sections=sections, metadata={})
    
    # Create edits with new author info
    edits = UserEdits(
        author_name="John Doe",
        author_email="john@example.com"
    )
    
    # Apply edits
    applicator = UserEditsApplicator()
    updated_doc = applicator.apply_edits(document, edits)
    
    # Verify author section was updated
    authors_sections = [s for s in updated_doc.sections if s.type == SectionType.AUTHORS]
    assert len(authors_sections) == 1
    assert "John Doe" in authors_sections[0].content
    assert "john@example.com" in authors_sections[0].content


def test_apply_author_info_creates_new_section():
    """Test applying author info when no AUTHORS section exists"""
    # Create document without AUTHORS section
    sections = [
        create_test_section(SectionType.TITLE, "Test Paper"),
        create_test_section(SectionType.ABSTRACT, "Abstract content")
    ]
    document = ParsedDocument(sections=sections, metadata={})
    
    # Create edits with author info
    edits = UserEdits(author_name="Jane Smith")
    
    # Apply edits
    applicator = UserEditsApplicator()
    updated_doc = applicator.apply_edits(document, edits)
    
    # Verify new AUTHORS section was created
    authors_sections = [s for s in updated_doc.sections if s.type == SectionType.AUTHORS]
    assert len(authors_sections) == 1
    assert "Jane Smith" in authors_sections[0].content
    
    # Verify it was inserted after TITLE
    title_idx = next(i for i, s in enumerate(updated_doc.sections) if s.type == SectionType.TITLE)
    authors_idx = next(i for i, s in enumerate(updated_doc.sections) if s.type == SectionType.AUTHORS)
    assert authors_idx == title_idx + 1


def test_apply_affiliation():
    """Test applying affiliation information"""
    sections = [
        create_test_section(SectionType.TITLE, "Test Paper"),
        create_test_section(SectionType.AUTHORS, "John Doe")
    ]
    document = ParsedDocument(sections=sections, metadata={})
    
    edits = UserEdits(affiliation="MIT Computer Science Department")
    
    applicator = UserEditsApplicator()
    updated_doc = applicator.apply_edits(document, edits)
    
    # Verify AFFILIATION section was created
    affiliation_sections = [s for s in updated_doc.sections if s.type == SectionType.AFFILIATION]
    assert len(affiliation_sections) == 1
    assert "MIT Computer Science Department" in affiliation_sections[0].content


def test_apply_keywords():
    """Test applying keywords"""
    sections = [
        create_test_section(SectionType.TITLE, "Test Paper"),
        create_test_section(SectionType.ABSTRACT, "Abstract content")
    ]
    document = ParsedDocument(sections=sections, metadata={})
    
    edits = UserEdits(keywords=["machine learning", "neural networks", "AI"])
    
    applicator = UserEditsApplicator()
    updated_doc = applicator.apply_edits(document, edits)
    
    # Verify KEYWORDS section was created
    keywords_sections = [s for s in updated_doc.sections if s.type == SectionType.KEYWORDS]
    assert len(keywords_sections) == 1
    assert "machine learning" in keywords_sections[0].content
    assert "neural networks" in keywords_sections[0].content
    assert "AI" in keywords_sections[0].content


def test_apply_section_corrections():
    """Test correcting section types"""
    section_id = str(uuid.uuid4())
    sections = [
        Section(
            id=section_id,
            type=SectionType.UNKNOWN,
            content="This is actually the methodology",
            original_heading="Methods",
            word_count=5
        )
    ]
    document = ParsedDocument(sections=sections, metadata={})
    
    # Correct the section type
    edits = UserEdits(
        section_corrections={section_id: SectionType.METHODOLOGY}
    )
    
    applicator = UserEditsApplicator()
    updated_doc = applicator.apply_edits(document, edits)
    
    # Verify section type was corrected
    corrected_section = next(s for s in updated_doc.sections if s.id == section_id)
    assert corrected_section.type == SectionType.METHODOLOGY


def test_no_auto_generation_by_default():
    """Test that auto-generation is disabled by default"""
    sections = [create_test_section(SectionType.TITLE, "Test Paper")]
    document = ParsedDocument(sections=sections, metadata={})
    
    # Apply empty edits
    edits = UserEdits()
    
    applicator = UserEditsApplicator()
    updated_doc = applicator.apply_edits(document, edits)
    
    # Verify no new sections were auto-generated
    assert len(updated_doc.sections) == len(document.sections)
    assert updated_doc.metadata["auto_generation_allowed"] is False


def test_check_missing_sections_without_generation():
    """Test that missing sections are flagged but not auto-generated"""
    # Create document missing several required sections
    sections = [
        create_test_section(SectionType.TITLE, "Test Paper"),
        create_test_section(SectionType.INTRODUCTION, "Intro content")
    ]
    document = ParsedDocument(sections=sections, metadata={})
    
    applicator = UserEditsApplicator()
    issues, missing_sections = applicator.check_missing_sections_without_generation(document)
    
    # Verify issues were created for missing sections
    assert len(issues) > 0
    
    # Verify expected missing sections are flagged
    missing_types = {issue.section for issue in issues}
    assert "Abstract" in missing_types
    assert "Keywords" in missing_types
    assert "Methodology" in missing_types
    assert "Results" in missing_types
    assert "Conclusion" in missing_types
    assert "References" in missing_types
    
    # Verify all issues are high severity
    for issue in issues:
        assert issue.severity == IssueSeverity.HIGH
        assert "missing" in issue.message.lower()
        assert "manually" in issue.message.lower()


def test_multiple_edits_applied_together():
    """Test applying multiple types of edits at once"""
    section_id = str(uuid.uuid4())
    sections = [
        create_test_section(SectionType.TITLE, "Test Paper"),
        Section(
            id=section_id,
            type=SectionType.UNKNOWN,
            content="Abstract content",
            original_heading="Summary",
            word_count=2
        )
    ]
    document = ParsedDocument(sections=sections, metadata={})
    
    # Apply multiple edits
    edits = UserEdits(
        author_name="Alice Johnson",
        affiliation="Stanford University",
        keywords=["research", "testing"],
        section_corrections={section_id: SectionType.ABSTRACT}
    )
    
    applicator = UserEditsApplicator()
    updated_doc = applicator.apply_edits(document, edits)
    
    # Verify all edits were applied
    assert any(s.type == SectionType.AUTHORS for s in updated_doc.sections)
    assert any(s.type == SectionType.AFFILIATION for s in updated_doc.sections)
    assert any(s.type == SectionType.KEYWORDS for s in updated_doc.sections)
    
    # Verify section correction was applied
    corrected_section = next(s for s in updated_doc.sections if s.id == section_id)
    assert corrected_section.type == SectionType.ABSTRACT
    
    # Verify metadata
    assert updated_doc.metadata["user_edits_applied"] is True
    edits_summary = updated_doc.metadata["edits_summary"]
    assert edits_summary["author_info_applied"] is True
    assert edits_summary["affiliation_applied"] is True
    assert edits_summary["keywords_applied"] is True
    assert edits_summary["section_corrections_applied"] is True


def test_edits_do_not_modify_original_document():
    """Test that applying edits doesn't modify the original document"""
    sections = [create_test_section(SectionType.TITLE, "Test Paper")]
    document = ParsedDocument(sections=sections, metadata={})
    
    original_section_count = len(document.sections)
    
    edits = UserEdits(author_name="Test Author")
    
    applicator = UserEditsApplicator()
    updated_doc = applicator.apply_edits(document, edits)
    
    # Verify original document is unchanged
    assert len(document.sections) == original_section_count
    assert not any(s.type == SectionType.AUTHORS for s in document.sections)
    
    # Verify updated document has the changes
    assert any(s.type == SectionType.AUTHORS for s in updated_doc.sections)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
