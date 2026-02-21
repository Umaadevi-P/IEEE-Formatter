"""Unit tests for section type detection"""
import pytest
from app.parser import DocumentParser
from app.models import SectionType


class TestSectionTypeDetection:
    """Test section type detection with keyword matching"""
    
    def setup_method(self):
        self.parser = DocumentParser()
    
    def test_abstract_detection(self):
        """Test Abstract section detection"""
        assert self.parser.detect_section_type("Abstract", "") == SectionType.ABSTRACT
        assert self.parser.detect_section_type("ABSTRACT", "") == SectionType.ABSTRACT
        assert self.parser.detect_section_type("Summary", "") == SectionType.ABSTRACT
        assert self.parser.detect_section_type("I. Abstract", "") == SectionType.ABSTRACT
    
    def test_keywords_detection(self):
        """Test Keywords section detection"""
        assert self.parser.detect_section_type("Keywords", "") == SectionType.KEYWORDS
        assert self.parser.detect_section_type("Index Terms", "") == SectionType.KEYWORDS
        assert self.parser.detect_section_type("Key Words", "") == SectionType.KEYWORDS
        assert self.parser.detect_section_type("II. Keywords", "") == SectionType.KEYWORDS
    
    def test_introduction_detection(self):
        """Test Introduction section detection"""
        assert self.parser.detect_section_type("Introduction", "") == SectionType.INTRODUCTION
        assert self.parser.detect_section_type("INTRODUCTION", "") == SectionType.INTRODUCTION
        assert self.parser.detect_section_type("I. Introduction", "") == SectionType.INTRODUCTION
        assert self.parser.detect_section_type("1. Introduction", "") == SectionType.INTRODUCTION
    
    def test_methodology_detection(self):
        """Test Methodology section detection"""
        assert self.parser.detect_section_type("Methodology", "") == SectionType.METHODOLOGY
        assert self.parser.detect_section_type("Methods", "") == SectionType.METHODOLOGY
        assert self.parser.detect_section_type("Approach", "") == SectionType.METHODOLOGY
        assert self.parser.detect_section_type("II. Methodology", "") == SectionType.METHODOLOGY
    
    def test_results_detection(self):
        """Test Results section detection"""
        assert self.parser.detect_section_type("Results", "") == SectionType.RESULTS
        assert self.parser.detect_section_type("Findings", "") == SectionType.RESULTS
        assert self.parser.detect_section_type("Experiments", "") == SectionType.RESULTS
        assert self.parser.detect_section_type("III. Results", "") == SectionType.RESULTS
    
    def test_conclusion_detection(self):
        """Test Conclusion section detection"""
        assert self.parser.detect_section_type("Conclusion", "") == SectionType.CONCLUSION
        assert self.parser.detect_section_type("Conclusions", "") == SectionType.CONCLUSION
        assert self.parser.detect_section_type("Concluding Remarks", "") == SectionType.CONCLUSION
        assert self.parser.detect_section_type("IV. Conclusion", "") == SectionType.CONCLUSION
    
    def test_references_detection(self):
        """Test References section detection"""
        assert self.parser.detect_section_type("References", "") == SectionType.REFERENCES
        assert self.parser.detect_section_type("Bibliography", "") == SectionType.REFERENCES
        assert self.parser.detect_section_type("Works Cited", "") == SectionType.REFERENCES
    
    def test_optional_sections_detection(self):
        """Test optional section detection"""
        assert self.parser.detect_section_type("Related Work", "") == SectionType.RELATED_WORK
        assert self.parser.detect_section_type("Literature Review", "") == SectionType.LITERATURE_REVIEW
        assert self.parser.detect_section_type("Discussion", "") == SectionType.DISCUSSION
        assert self.parser.detect_section_type("Future Work", "") == SectionType.FUTURE_WORK
        assert self.parser.detect_section_type("Acknowledgments", "") == SectionType.ACKNOWLEDGMENTS
        assert self.parser.detect_section_type("Appendix", "") == SectionType.APPENDIX
    
    def test_unknown_section(self):
        """Test unknown section type"""
        assert self.parser.detect_section_type("Random Section", "") == SectionType.UNKNOWN
        assert self.parser.detect_section_type("Some Other Heading", "") == SectionType.UNKNOWN
    
    def test_numbering_removal(self):
        """Test that numbering is properly removed before detection"""
        # Roman numerals
        assert self.parser.detect_section_type("I. Introduction", "") == SectionType.INTRODUCTION
        assert self.parser.detect_section_type("II. Methodology", "") == SectionType.METHODOLOGY
        assert self.parser.detect_section_type("III. Results", "") == SectionType.RESULTS
        
        # Arabic numerals
        assert self.parser.detect_section_type("1. Introduction", "") == SectionType.INTRODUCTION
        assert self.parser.detect_section_type("2. Methodology", "") == SectionType.METHODOLOGY
        
        # Section prefix
        assert self.parser.detect_section_type("Section 1: Introduction", "") == SectionType.INTRODUCTION
