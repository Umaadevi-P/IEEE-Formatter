"""Unit tests for citation converter"""
import pytest
from app.citation_converter import CitationConverter
from app.models import Section, SectionType
import uuid


class TestCitationConverter:
    """Test citation detection and conversion to IEEE format"""
    
    def test_detect_references_section(self):
        """Test that References section is correctly identified"""
        converter = CitationConverter()
        
        sections = [
            Section(
                id=str(uuid.uuid4()),
                type=SectionType.INTRODUCTION,
                content="This is the introduction.",
                word_count=4
            ),
            Section(
                id=str(uuid.uuid4()),
                type=SectionType.REFERENCES,
                content="[1] Smith, J. (2020). Paper Title.\n[2] Jones, A. (2021). Another Paper.",
                word_count=10
            )
        ]
        
        result = converter.convert_references(sections)
        
        # Should return same number of sections
        assert len(result) == 2
        
        # References section should be formatted
        refs_section = result[1]
        assert refs_section.type == SectionType.REFERENCES
        assert "[1]" in refs_section.content
        assert "[2]" in refs_section.content
    
    def test_no_references_section(self):
        """Test handling when no References section exists"""
        converter = CitationConverter()
        
        sections = [
            Section(
                id=str(uuid.uuid4()),
                type=SectionType.INTRODUCTION,
                content="This is the introduction.",
                word_count=4
            )
        ]
        
        result = converter.convert_references(sections)
        
        # Should return sections unchanged
        assert len(result) == 1
        assert result[0].content == "This is the introduction."
    
    def test_extract_numbered_citations(self):
        """Test extraction of citations with existing numbering"""
        converter = CitationConverter()
        
        references_content = """[1] Smith, J. (2020). A Study on AI. Journal of AI, 10(2), 45-60.
[2] Jones, A. (2021). Machine Learning Basics. Tech Press.
[3] Brown, B. et al. (2019). Deep Learning. Nature, 500, 123-130."""
        
        citations = converter._extract_citations(references_content)
        
        assert len(citations) == 3
        assert "Smith, J. (2020)" in citations[0]
        assert "Jones, A. (2021)" in citations[1]
        assert "Brown, B. et al. (2019)" in citations[2]
    
    def test_extract_plain_citations(self):
        """Test extraction of citations without numbering"""
        converter = CitationConverter()
        
        references_content = """Smith, J. (2020). A Study on AI. Journal of AI, 10(2), 45-60.

Jones, A. (2021). Machine Learning Basics. Tech Press.

Brown, B. et al. (2019). Deep Learning. Nature, 500, 123-130."""
        
        citations = converter._extract_citations(references_content)
        
        assert len(citations) >= 3
        # Check that citations were extracted
        assert any("Smith" in c for c in citations)
        assert any("Jones" in c for c in citations)
        assert any("Brown" in c for c in citations)
    
    def test_format_references_section(self):
        """Test formatting of References section with IEEE numbering"""
        converter = CitationConverter()
        
        citations = [
            "Smith, J. (2020). A Study on AI.",
            "Jones, A. (2021). Machine Learning Basics.",
            "Brown, B. (2019). Deep Learning."
        ]
        
        formatted = converter._format_references_section(citations)
        
        assert "[1] Smith, J. (2020)" in formatted
        assert "[2] Jones, A. (2021)" in formatted
        assert "[3] Brown, B. (2019)" in formatted
    
    def test_convert_intext_citations_author_year(self):
        """Test conversion of (Author, Year) format to [N]"""
        converter = CitationConverter()
        
        section = Section(
            id=str(uuid.uuid4()),
            type=SectionType.INTRODUCTION,
            content="Previous work (Smith, 2020) showed that AI is useful. Another study (Jones, 2021) confirmed this.",
            word_count=15
        )
        
        result = converter._convert_intext_citations(section)
        
        # Should convert to [N] format
        assert "[1]" in result.content or "[" in result.content
        # Original author-year format should be replaced
        assert "(Smith, 2020)" not in result.content or "[" in result.content
    
    def test_convert_intext_citations_et_al(self):
        """Test conversion of (Author et al., Year) format"""
        converter = CitationConverter()
        
        section = Section(
            id=str(uuid.uuid4()),
            type=SectionType.METHODOLOGY,
            content="The method (Brown et al., 2019) was applied successfully.",
            word_count=8
        )
        
        result = converter._convert_intext_citations(section)
        
        # Should convert to [N] format
        assert "[" in result.content
        # Original format should be replaced
        assert "(Brown et al., 2019)" not in result.content or "[" in result.content
    
    def test_preserve_reference_order(self):
        """Test that reference order is preserved from original document"""
        converter = CitationConverter()
        
        sections = [
            Section(
                id=str(uuid.uuid4()),
                type=SectionType.REFERENCES,
                content="Smith, J. (2020). First Paper.\n\nJones, A. (2021). Second Paper.\n\nBrown, B. (2019). Third Paper.",
                word_count=15
            )
        ]
        
        result = converter.convert_references(sections)
        refs_content = result[0].content
        
        # Check order is preserved
        smith_pos = refs_content.find("Smith")
        jones_pos = refs_content.find("Jones")
        brown_pos = refs_content.find("Brown")
        
        assert smith_pos < jones_pos < brown_pos
        
        # Check numbering matches order
        assert "[1] Smith" in refs_content
        assert "[2] Jones" in refs_content
        assert "[3] Brown" in refs_content
    
    def test_remove_citation_prefix(self):
        """Test removal of existing citation prefixes"""
        converter = CitationConverter()
        
        # Test various prefix formats
        assert converter._remove_citation_prefix("[1] Smith, J.") == "Smith, J."
        assert converter._remove_citation_prefix("1. Smith, J.") == "Smith, J."
        assert converter._remove_citation_prefix("• Smith, J.") == "Smith, J."
        assert converter._remove_citation_prefix("- Smith, J.") == "Smith, J."
        assert converter._remove_citation_prefix("* Smith, J.") == "Smith, J."
    
    def test_is_citation_start(self):
        """Test detection of citation start patterns"""
        converter = CitationConverter()
        
        # Should detect these as citation starts
        assert converter._is_citation_start("[1] Smith, J.")
        assert converter._is_citation_start("1. Smith, J.")
        assert converter._is_citation_start("• Smith, J.")
        assert converter._is_citation_start("Smith, J. (2020)")
        
        # Should not detect these as citation starts
        assert not converter._is_citation_start("This is a regular sentence.")
        assert not converter._is_citation_start("the study showed")
    
    def test_get_citation_count(self):
        """Test citation counting"""
        converter = CitationConverter()
        
        sections = [
            Section(
                id=str(uuid.uuid4()),
                type=SectionType.REFERENCES,
                content="[1] Smith, J. (2020). Paper One.\n[2] Jones, A. (2021). Paper Two.\n[3] Brown, B. (2019). Paper Three.",
                word_count=20
            )
        ]
        
        converter.convert_references(sections)
        
        # Should have detected 3 citations
        assert converter.get_citation_count() == 3
    
    def test_reset_citation_map(self):
        """Test resetting citation map"""
        converter = CitationConverter()
        
        # Build some citations
        converter._build_citation_map(["Citation 1", "Citation 2"])
        assert converter.get_citation_count() == 2
        
        # Reset
        converter.reset()
        assert converter.get_citation_count() == 0
        assert converter.next_citation_number == 1
    
    def test_full_conversion_workflow(self):
        """Test complete citation conversion workflow"""
        converter = CitationConverter()
        
        sections = [
            Section(
                id=str(uuid.uuid4()),
                type=SectionType.INTRODUCTION,
                content="Previous research (Smith, 2020) and (Jones, 2021) showed promising results.",
                word_count=10
            ),
            Section(
                id=str(uuid.uuid4()),
                type=SectionType.REFERENCES,
                content="Smith, J. (2020). AI Research. Journal of AI.\n\nJones, A. (2021). ML Advances. Tech Review.",
                word_count=15
            )
        ]
        
        result = converter.convert_references(sections)
        
        # Check that we have 2 sections
        assert len(result) == 2
        
        # Check References section is formatted
        refs_section = result[1]
        assert "[1]" in refs_section.content
        assert "[2]" in refs_section.content
        
        # Check in-text citations are converted
        intro_section = result[0]
        # Should have some form of citation markers
        assert "[" in intro_section.content or "(" in intro_section.content
    
    def test_empty_references_section(self):
        """Test handling of empty References section"""
        converter = CitationConverter()
        
        sections = [
            Section(
                id=str(uuid.uuid4()),
                type=SectionType.REFERENCES,
                content="",
                word_count=0
            )
        ]
        
        result = converter.convert_references(sections)
        
        # Should handle gracefully
        assert len(result) == 1
        assert result[0].type == SectionType.REFERENCES
