"""Integration tests for citation conversion with formatter"""
import pytest
from app.formatter import IEEEFormatter
from app.parser import DocumentParser
from app.models import ParsedDocument, Section, SectionType
import uuid


class TestCitationIntegration:
    """Test citation conversion integrated with IEEE formatter"""
    
    def test_formatter_converts_citations(self):
        """Test that formatter includes citation conversion"""
        # Create a document with references
        sections = [
            Section(
                id=str(uuid.uuid4()),
                type=SectionType.INTRODUCTION,
                content="Previous work (Smith, 2020) showed results.",
                word_count=6
            ),
            Section(
                id=str(uuid.uuid4()),
                type=SectionType.REFERENCES,
                content="Smith, J. (2020). AI Research. Journal of AI.\n\nJones, A. (2021). ML Study. Tech Review.",
                word_count=15
            )
        ]
        
        parsed_doc = ParsedDocument(
            sections=sections,
            metadata={"test": True}
        )
        
        # Format the document
        formatter = IEEEFormatter("rules.docx")
        formatted_doc = formatter.format(parsed_doc)
        
        # Check that citations were converted
        assert formatted_doc.metadata.get("citations_converted") is True
        assert formatted_doc.metadata.get("citation_count", 0) > 0
        
        # Find References section
        refs_section = None
        for section in formatted_doc.sections:
            if section.type == SectionType.REFERENCES:
                refs_section = section
                break
        
        assert refs_section is not None
        # Should have IEEE numbered format
        assert "[1]" in refs_section.content
        assert "[2]" in refs_section.content
    
    def test_formatter_preserves_reference_order(self):
        """Test that formatter preserves reference order during conversion"""
        sections = [
            Section(
                id=str(uuid.uuid4()),
                type=SectionType.REFERENCES,
                content="Alpha, A. (2020). First Paper.\n\nBeta, B. (2021). Second Paper.\n\nGamma, G. (2019). Third Paper.",
                word_count=20
            )
        ]
        
        parsed_doc = ParsedDocument(
            sections=sections,
            metadata={"test": True}
        )
        
        formatter = IEEEFormatter("rules.docx")
        formatted_doc = formatter.format(parsed_doc)
        
        # Find References section
        refs_section = formatted_doc.sections[0]
        
        # Check order is preserved
        alpha_pos = refs_section.content.find("Alpha")
        beta_pos = refs_section.content.find("Beta")
        gamma_pos = refs_section.content.find("Gamma")
        
        assert alpha_pos < beta_pos < gamma_pos
        
        # Check numbering
        assert "[1] Alpha" in refs_section.content
        assert "[2] Beta" in refs_section.content
        assert "[3] Gamma" in refs_section.content
    
    def test_formatter_handles_no_references(self):
        """Test that formatter handles documents without References section"""
        sections = [
            Section(
                id=str(uuid.uuid4()),
                type=SectionType.INTRODUCTION,
                content="This is an introduction without references.",
                word_count=6
            )
        ]
        
        parsed_doc = ParsedDocument(
            sections=sections,
            metadata={"test": True}
        )
        
        formatter = IEEEFormatter("rules.docx")
        formatted_doc = formatter.format(parsed_doc)
        
        # Should complete without errors
        assert len(formatted_doc.sections) == 1
        assert formatted_doc.metadata.get("citations_converted") is True
    
    def test_full_pipeline_with_citations(self):
        """Test complete pipeline: parse → format with citation conversion"""
        sections = [
            Section(
                id=str(uuid.uuid4()),
                type=SectionType.TITLE,
                content="Research Paper Title",
                word_count=3
            ),
            Section(
                id=str(uuid.uuid4()),
                type=SectionType.ABSTRACT,
                content="This is the abstract of the paper.",
                word_count=7
            ),
            Section(
                id=str(uuid.uuid4()),
                type=SectionType.INTRODUCTION,
                content="Introduction with citation (Author, 2020).",
                word_count=5
            ),
            Section(
                id=str(uuid.uuid4()),
                type=SectionType.METHODOLOGY,
                content="We used the method from (Smith et al., 2019).",
                word_count=9
            ),
            Section(
                id=str(uuid.uuid4()),
                type=SectionType.REFERENCES,
                content="Author, A. (2020). Paper Title. Journal.\n\nSmith, S. et al. (2019). Method Paper. Conference.",
                word_count=15
            )
        ]
        
        parsed_doc = ParsedDocument(
            sections=sections,
            metadata={"original_file": "test.docx"}
        )
        
        # Format with citation conversion
        formatter = IEEEFormatter("rules.docx")
        formatted_doc = formatter.format(parsed_doc)
        
        # Verify structure
        assert len(formatted_doc.sections) == 5
        
        # Verify citations were converted
        assert formatted_doc.metadata.get("citations_converted") is True
        
        # Find and verify References section
        refs_section = None
        for section in formatted_doc.sections:
            if section.type == SectionType.REFERENCES:
                refs_section = section
                break
        
        assert refs_section is not None
        assert "[1]" in refs_section.content
        assert "[2]" in refs_section.content
        
        # Verify sections are in IEEE order
        section_types = [s.type for s in formatted_doc.sections]
        title_idx = section_types.index(SectionType.TITLE)
        abstract_idx = section_types.index(SectionType.ABSTRACT)
        intro_idx = section_types.index(SectionType.INTRODUCTION)
        refs_idx = section_types.index(SectionType.REFERENCES)
        
        # Title should come before Abstract, Abstract before Introduction, etc.
        assert title_idx < abstract_idx < intro_idx < refs_idx
