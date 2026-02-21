"""Integration tests for change tracking with formatter and parser"""
import pytest
from app.change_tracker import ChangeTracker
from app.parser import DocumentParser
from app.formatter import IEEEFormatter
from app.models import ParsedDocument, Section, SectionType
import uuid
import os


class TestChangeTrackingIntegration:
    """Test change tracking integrated with parser and formatter"""
    
    def test_change_tracker_with_formatter(self):
        """Test that change tracker works with formatter"""
        # Create a simple document
        sections = [
            Section(
                id=str(uuid.uuid4()),
                type=SectionType.INTRODUCTION,
                content="This is the introduction.",
                original_heading="Introduction",
                word_count=4
            ),
            Section(
                id=str(uuid.uuid4()),
                type=SectionType.ABSTRACT,
                content="This is the abstract.",
                original_heading="Abstract",
                word_count=4
            )
        ]
        
        parsed_doc = ParsedDocument(
            sections=sections,
            metadata={"test": True}
        )
        
        # Store original for comparison
        document_before = parsed_doc.model_copy(deep=True)
        
        # Format the document
        formatter = IEEEFormatter("rules.docx")
        formatted_doc = formatter.format(parsed_doc)
        
        # Track changes
        tracker = ChangeTracker()
        fixes = tracker.track_changes(document_before, formatted_doc)
        
        # Verify fixes were tracked
        assert len(fixes) > 0
        
        # Verify fix structure
        for fix in fixes:
            assert fix.section_id
            assert fix.type
            assert fix.reason
        
        # Should have heading formatting fixes
        heading_fixes = [f for f in fixes if f.type == "heading_formatting"]
        assert len(heading_fixes) > 0
        
        # Should have font formatting fixes
        font_fixes = [f for f in fixes if f.type == "font_formatting"]
        assert len(font_fixes) > 0
    
    def test_change_tracker_tracks_reordering(self):
        """Test that change tracker detects section reordering"""
        # Create document with sections out of order
        sections = [
            Section(
                id="intro-1",
                type=SectionType.INTRODUCTION,
                content="Introduction content",
                word_count=2
            ),
            Section(
                id="abstract-1",
                type=SectionType.ABSTRACT,
                content="Abstract content",
                word_count=2
            )
        ]
        
        parsed_doc = ParsedDocument(
            sections=sections,
            metadata={"test": True}
        )
        
        document_before = parsed_doc.model_copy(deep=True)
        
        # Format (will reorder to IEEE standard)
        formatter = IEEEFormatter("rules.docx")
        formatted_doc = formatter.format(parsed_doc)
        
        # Track changes
        tracker = ChangeTracker()
        fixes = tracker.track_changes(document_before, formatted_doc)
        
        # Should have reordering fixes
        reorder_fixes = [f for f in fixes if f.type == "section_reordering"]
        assert len(reorder_fixes) > 0
        
        # Verify reordering fix details
        for fix in reorder_fixes:
            assert "Position" in fix.original
            assert "Position" in fix.formatted
            assert "IEEE" in fix.reason or "standard" in fix.reason
    
    def test_change_tracker_with_real_document(self):
        """Test change tracker with a real parsed document"""
        # Use an existing test document
        test_file_path = "uploads/Exp 1.docx"
        
        # Skip test if file doesn't exist
        if not os.path.exists(test_file_path):
            pytest.skip(f"Test file not found: {test_file_path}")
        
        # Parse document
        parser = DocumentParser()
        parsed_doc = parser.parse(test_file_path)
        
        # Store original
        document_before = parsed_doc.model_copy(deep=True)
        
        # Format document
        formatter = IEEEFormatter("rules.docx")
        formatted_doc = formatter.format(parsed_doc)
        
        # Track changes
        tracker = ChangeTracker()
        fixes = tracker.track_changes(document_before, formatted_doc)
        
        # Verify fixes were tracked
        assert len(fixes) > 0
        
        # Verify all fix types are valid
        valid_fix_types = [
            "heading_formatting",
            "heading_added",
            "section_reordering",
            "font_formatting",
            "heading_font_formatting",
            "grammar_correction",
            "section_type_correction"
        ]
        
        for fix in fixes:
            assert fix.type in valid_fix_types
        
        # Verify all section IDs are valid
        section_ids = set(s.id for s in formatted_doc.sections)
        for fix in fixes:
            assert fix.section_id in section_ids
    
    def test_change_tracker_summary(self):
        """Test that change tracker provides useful summary"""
        # Create document
        sections = [
            Section(
                id=str(uuid.uuid4()),
                type=SectionType.INTRODUCTION,
                content="Introduction",
                original_heading="Introduction",
                word_count=1
            ),
            Section(
                id=str(uuid.uuid4()),
                type=SectionType.METHODOLOGY,
                content="Methodology",
                original_heading="Methodology",
                word_count=1
            )
        ]
        
        parsed_doc = ParsedDocument(
            sections=sections,
            metadata={"test": True}
        )
        
        document_before = parsed_doc.model_copy(deep=True)
        
        # Format
        formatter = IEEEFormatter("rules.docx")
        formatted_doc = formatter.format(parsed_doc)
        
        # Track changes
        tracker = ChangeTracker()
        tracker.track_changes(document_before, formatted_doc)
        
        # Get summary
        summary = tracker.get_fix_summary()
        
        # Verify summary structure
        assert "total_changes" in summary
        assert "changes_by_type" in summary
        assert "sections_affected" in summary
        
        # Verify summary values
        assert summary["total_changes"] > 0
        assert len(summary["changes_by_type"]) > 0
        assert summary["sections_affected"] > 0
    
    def test_fixes_have_meaningful_content(self):
        """Test that fixes contain meaningful information"""
        # Create document
        sections = [
            Section(
                id=str(uuid.uuid4()),
                type=SectionType.INTRODUCTION,
                content="Introduction content",
                original_heading="Introduction",
                word_count=2
            )
        ]
        
        parsed_doc = ParsedDocument(
            sections=sections,
            metadata={"test": True}
        )
        
        document_before = parsed_doc.model_copy(deep=True)
        
        # Format
        formatter = IEEEFormatter("rules.docx")
        formatted_doc = formatter.format(parsed_doc)
        
        # Track changes
        tracker = ChangeTracker()
        fixes = tracker.track_changes(document_before, formatted_doc)
        
        # Verify all fixes have meaningful reasons
        for fix in fixes:
            assert fix.reason
            assert len(fix.reason) > 10
            
            # Verify reason contains useful keywords
            reason_lower = fix.reason.lower()
            useful_keywords = ["ieee", "format", "applied", "reordered", "correction", "added", "roman", "caps"]
            assert any(keyword in reason_lower for keyword in useful_keywords)
