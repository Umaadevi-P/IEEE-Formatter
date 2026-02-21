"""Unit tests for ChangeTracker"""
import pytest
from app.change_tracker import ChangeTracker
from app.models import (
    Section,
    SectionType,
    ParsedDocument,
    FormattedDocument,
    FontRule
)


def test_track_heading_changes():
    """Test tracking heading formatting changes"""
    # Create before document
    before_section = Section(
        id="section-1",
        type=SectionType.INTRODUCTION,
        content="This is the introduction content.",
        original_heading="Introduction",
        word_count=5
    )
    before_doc = ParsedDocument(
        sections=[before_section],
        metadata={}
    )
    
    # Create after document with formatted heading
    after_section = Section(
        id="section-1",
        type=SectionType.INTRODUCTION,
        content="This is the introduction content.",
        original_heading="Introduction",
        formatted_heading="I. INTRODUCTION",
        word_count=5
    )
    after_doc = FormattedDocument(
        sections=[after_section],
        metadata={},
        compliance_score=85.0
    )
    
    # Track changes
    tracker = ChangeTracker()
    fixes = tracker.track_changes(before_doc, after_doc)
    
    # Verify heading change was tracked
    heading_fixes = [f for f in fixes if f.type == "heading_formatting"]
    assert len(heading_fixes) == 1
    assert heading_fixes[0].section_id == "section-1"
    assert heading_fixes[0].original == "Introduction"
    assert heading_fixes[0].formatted == "I. INTRODUCTION"
    assert "Roman numerals" in heading_fixes[0].reason


def test_track_section_reordering():
    """Test tracking section reordering"""
    # Create before document with sections out of order
    section1 = Section(
        id="section-1",
        type=SectionType.INTRODUCTION,
        content="Introduction content",
        word_count=2
    )
    section2 = Section(
        id="section-2",
        type=SectionType.ABSTRACT,
        content="Abstract content",
        word_count=2
    )
    before_doc = ParsedDocument(
        sections=[section1, section2],  # Wrong order
        metadata={}
    )
    
    # Create after document with correct order
    after_doc = FormattedDocument(
        sections=[section2, section1],  # Correct order (Abstract before Introduction)
        metadata={},
        compliance_score=90.0
    )
    
    # Track changes
    tracker = ChangeTracker()
    fixes = tracker.track_changes(before_doc, after_doc)
    
    # Verify reordering was tracked
    reorder_fixes = [f for f in fixes if f.type == "section_reordering"]
    assert len(reorder_fixes) == 2  # Both sections changed position
    
    # Check that positions changed
    for fix in reorder_fixes:
        assert "Position" in fix.original
        assert "Position" in fix.formatted


def test_track_font_changes():
    """Test tracking font rule application"""
    # Create before document without font rules
    before_section = Section(
        id="section-1",
        type=SectionType.ABSTRACT,
        content="Abstract content",
        word_count=2
    )
    before_doc = ParsedDocument(
        sections=[before_section],
        metadata={}
    )
    
    # Create after document with font rules applied
    after_section = Section(
        id="section-1",
        type=SectionType.ABSTRACT,
        content="Abstract content",
        word_count=2,
        font_rule=FontRule(
            font_family="Times New Roman",
            font_size=9,
            bold=False,
            italic=False,
            alignment="justify"
        )
    )
    after_doc = FormattedDocument(
        sections=[after_section],
        metadata={},
        compliance_score=85.0
    )
    
    # Track changes
    tracker = ChangeTracker()
    fixes = tracker.track_changes(before_doc, after_doc)
    
    # Verify font change was tracked
    font_fixes = [f for f in fixes if f.type == "font_formatting"]
    assert len(font_fixes) == 1
    assert font_fixes[0].section_id == "section-1"
    assert "Times New Roman" in font_fixes[0].formatted
    assert "9pt" in font_fixes[0].formatted


def test_track_content_changes():
    """Test tracking grammar correction changes"""
    # Create before document
    before_section = Section(
        id="section-1",
        type=SectionType.INTRODUCTION,
        content="This is a sentance with a spelling eror.",
        word_count=8
    )
    before_doc = ParsedDocument(
        sections=[before_section],
        metadata={}
    )
    
    # Create after document with corrected content
    after_section = Section(
        id="section-1",
        type=SectionType.INTRODUCTION,
        content="This is a sentence with a spelling error.",
        word_count=8
    )
    after_doc = FormattedDocument(
        sections=[after_section],
        metadata={},
        compliance_score=90.0
    )
    
    # Track changes
    tracker = ChangeTracker()
    fixes = tracker.track_changes(before_doc, after_doc)
    
    # Verify content change was tracked
    grammar_fixes = [f for f in fixes if f.type == "grammar_correction"]
    assert len(grammar_fixes) == 1
    assert grammar_fixes[0].section_id == "section-1"
    assert "Grammar" in grammar_fixes[0].reason


def test_track_heading_added():
    """Test tracking when heading is added to section without one"""
    # Create before document without heading
    before_section = Section(
        id="section-1",
        type=SectionType.ABSTRACT,
        content="Abstract content",
        word_count=2
    )
    before_doc = ParsedDocument(
        sections=[before_section],
        metadata={}
    )
    
    # Create after document with heading added
    after_section = Section(
        id="section-1",
        type=SectionType.ABSTRACT,
        content="Abstract content",
        formatted_heading="ABSTRACT",
        word_count=2
    )
    after_doc = FormattedDocument(
        sections=[after_section],
        metadata={},
        compliance_score=85.0
    )
    
    # Track changes
    tracker = ChangeTracker()
    fixes = tracker.track_changes(before_doc, after_doc)
    
    # Verify heading addition was tracked
    heading_fixes = [f for f in fixes if f.type == "heading_added"]
    assert len(heading_fixes) == 1
    assert heading_fixes[0].section_id == "section-1"
    assert heading_fixes[0].original is None
    assert heading_fixes[0].formatted == "ABSTRACT"


def test_get_fix_summary():
    """Test getting summary of all changes"""
    # Create documents with multiple changes
    before_doc = ParsedDocument(
        sections=[
            Section(
                id="section-1",
                type=SectionType.INTRODUCTION,
                content="Content 1",
                original_heading="Introduction",
                word_count=2
            ),
            Section(
                id="section-2",
                type=SectionType.ABSTRACT,
                content="Content 2",
                word_count=2
            )
        ],
        metadata={}
    )
    
    after_doc = FormattedDocument(
        sections=[
            Section(
                id="section-2",
                type=SectionType.ABSTRACT,
                content="Content 2",
                formatted_heading="ABSTRACT",
                word_count=2,
                font_rule=FontRule(
                    font_family="Times New Roman",
                    font_size=9,
                    bold=False,
                    italic=False,
                    alignment="justify"
                )
            ),
            Section(
                id="section-1",
                type=SectionType.INTRODUCTION,
                content="Content 1",
                original_heading="Introduction",
                formatted_heading="I. INTRODUCTION",
                word_count=2,
                font_rule=FontRule(
                    font_family="Times New Roman",
                    font_size=10,
                    bold=False,
                    italic=False,
                    alignment="justify"
                )
            )
        ],
        metadata={},
        compliance_score=90.0
    )
    
    # Track changes
    tracker = ChangeTracker()
    fixes = tracker.track_changes(before_doc, after_doc)
    
    # Get summary
    summary = tracker.get_fix_summary()
    
    # Verify summary
    assert summary["total_changes"] > 0
    assert "changes_by_type" in summary
    assert "sections_affected" in summary
    assert summary["sections_affected"] == 2


def test_get_fixes_by_type():
    """Test filtering fixes by type"""
    # Create documents with multiple change types
    before_doc = ParsedDocument(
        sections=[
            Section(
                id="section-1",
                type=SectionType.INTRODUCTION,
                content="Content",
                original_heading="Introduction",
                word_count=1
            )
        ],
        metadata={}
    )
    
    after_doc = FormattedDocument(
        sections=[
            Section(
                id="section-1",
                type=SectionType.INTRODUCTION,
                content="Content",
                original_heading="Introduction",
                formatted_heading="I. INTRODUCTION",
                word_count=1,
                font_rule=FontRule(
                    font_family="Times New Roman",
                    font_size=10,
                    bold=False,
                    italic=False,
                    alignment="justify"
                )
            )
        ],
        metadata={},
        compliance_score=90.0
    )
    
    # Track changes
    tracker = ChangeTracker()
    tracker.track_changes(before_doc, after_doc)
    
    # Get fixes by type
    heading_fixes = tracker.get_fixes_by_type("heading_formatting")
    font_fixes = tracker.get_fixes_by_type("font_formatting")
    
    # Verify filtering works
    assert len(heading_fixes) >= 1
    assert len(font_fixes) >= 1
    assert all(f.type == "heading_formatting" for f in heading_fixes)
    assert all(f.type == "font_formatting" for f in font_fixes)


def test_get_fixes_by_section():
    """Test filtering fixes by section ID"""
    # Create documents with changes to multiple sections
    before_doc = ParsedDocument(
        sections=[
            Section(
                id="section-1",
                type=SectionType.INTRODUCTION,
                content="Content 1",
                original_heading="Introduction",
                word_count=2
            ),
            Section(
                id="section-2",
                type=SectionType.ABSTRACT,
                content="Content 2",
                word_count=2
            )
        ],
        metadata={}
    )
    
    after_doc = FormattedDocument(
        sections=[
            Section(
                id="section-1",
                type=SectionType.INTRODUCTION,
                content="Content 1",
                original_heading="Introduction",
                formatted_heading="I. INTRODUCTION",
                word_count=2
            ),
            Section(
                id="section-2",
                type=SectionType.ABSTRACT,
                content="Content 2",
                formatted_heading="ABSTRACT",
                word_count=2
            )
        ],
        metadata={},
        compliance_score=90.0
    )
    
    # Track changes
    tracker = ChangeTracker()
    tracker.track_changes(before_doc, after_doc)
    
    # Get fixes for specific section
    section1_fixes = tracker.get_fixes_by_section("section-1")
    section2_fixes = tracker.get_fixes_by_section("section-2")
    
    # Verify filtering works
    assert len(section1_fixes) >= 1
    assert len(section2_fixes) >= 1
    assert all(f.section_id == "section-1" for f in section1_fixes)
    assert all(f.section_id == "section-2" for f in section2_fixes)


def test_no_changes_tracked_when_identical():
    """Test that no changes are tracked when documents are identical"""
    # Create identical documents
    section = Section(
        id="section-1",
        type=SectionType.INTRODUCTION,
        content="Content",
        word_count=1
    )
    
    before_doc = ParsedDocument(
        sections=[section],
        metadata={}
    )
    
    after_doc = FormattedDocument(
        sections=[section.model_copy(deep=True)],
        metadata={},
        compliance_score=100.0
    )
    
    # Track changes
    tracker = ChangeTracker()
    fixes = tracker.track_changes(before_doc, after_doc)
    
    # Verify no changes tracked
    assert len(fixes) == 0
