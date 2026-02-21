"""Compliance scoring module for IEEE Paper Formatter"""
from app.models import ComplianceScore, Issue, IssueSeverity, ParsedDocument, FormattedDocument, SectionType
from typing import List, Dict


class ComplianceScorer:
    """Calculates IEEE compliance percentage for documents"""
    
    # Component weights (must sum to 1.0)
    WEIGHTS = {
        "required_sections": 0.30,  # 30%
        "section_order": 0.25,      # 25%
        "abstract_compliance": 0.20, # 20%
        "heading_hierarchy": 0.15,   # 15%
        "formatting_consistency": 0.10  # 10%
    }
    
    # Required sections for IEEE papers
    REQUIRED_SECTIONS = {
        SectionType.ABSTRACT,
        SectionType.KEYWORDS,
        SectionType.INTRODUCTION,
        SectionType.METHODOLOGY,
        SectionType.RESULTS,
        SectionType.CONCLUSION,
        SectionType.REFERENCES
    }
    
    # IEEE standard section order
    IEEE_SECTION_ORDER = [
        SectionType.TITLE,
        SectionType.AUTHORS,
        SectionType.AFFILIATION,
        SectionType.ABSTRACT,
        SectionType.KEYWORDS,
        SectionType.INTRODUCTION,
        SectionType.RELATED_WORK,
        SectionType.LITERATURE_REVIEW,
        SectionType.METHODOLOGY,
        SectionType.RESULTS,
        SectionType.DISCUSSION,
        SectionType.CONCLUSION,
        SectionType.FUTURE_WORK,
        SectionType.ACKNOWLEDGMENTS,
        SectionType.REFERENCES,
        SectionType.APPENDIX
    ]
    
    # Abstract word count constraints
    ABSTRACT_MIN_WORDS = 150
    ABSTRACT_MAX_WORDS = 250
    
    def calculate(self, document: FormattedDocument, issues: List[Issue]) -> ComplianceScore:
        """
        Calculate compliance score with weighted components:
        - Required sections present: 30%
        - Correct section order: 25%
        - Abstract compliance (150-250 words): 20%
        - Heading hierarchy: 15%
        - Formatting consistency: 10%
        
        Returns ComplianceScore with total score (0-100) and detailed breakdown
        """
        # Calculate each component score
        breakdown = {
            "required_sections": self._score_required_sections(document),
            "section_order": self._score_section_order(document, issues),
            "abstract_compliance": self._score_abstract_compliance(document),
            "heading_hierarchy": self._score_heading_hierarchy(document),
            "formatting_consistency": self._score_formatting_consistency(document, issues)
        }
        
        # Calculate weighted total score
        total_score = sum(
            breakdown[component] * self.WEIGHTS[component]
            for component in self.WEIGHTS.keys()
        )
        
        # Convert to percentage (0-100)
        total_score_percentage = total_score * 100
        
        return ComplianceScore(
            score=round(total_score_percentage, 2),
            breakdown=breakdown,
            weights=self.WEIGHTS
        )
    
    def _score_required_sections(self, document: FormattedDocument) -> float:
        """
        Score based on presence of required sections
        Returns: 0.0 to 1.0
        """
        # Get set of section types present in document
        present_sections = {section.type for section in document.sections}
        
        # Count how many required sections are present
        present_required = len(self.REQUIRED_SECTIONS & present_sections)
        total_required = len(self.REQUIRED_SECTIONS)
        
        if total_required == 0:
            return 1.0
        
        return present_required / total_required
    
    def _score_section_order(self, document: FormattedDocument, issues: List[Issue]) -> float:
        """
        Score based on correct section ordering
        Returns: 0.7 if out of order, 1.0 if correct
        """
        # Check if there are any section order issues
        order_issues = [
            issue for issue in issues 
            if issue.type == "section_out_of_order"
        ]
        
        if order_issues:
            return 0.7  # Partial credit for out-of-order sections
        
        return 1.0
    
    def _score_abstract_compliance(self, document: FormattedDocument) -> float:
        """
        Score based on abstract word count (150-250 words)
        Returns: 0.6 if out of range, 1.0 if in range
        """
        # Find abstract section
        abstract_sections = [
            s for s in document.sections 
            if s.type == SectionType.ABSTRACT
        ]
        
        if not abstract_sections:
            # No abstract present - return 0
            return 0.0
        
        # Check word count
        abstract = abstract_sections[0]
        word_count = abstract.word_count
        
        if self.ABSTRACT_MIN_WORDS <= word_count <= self.ABSTRACT_MAX_WORDS:
            return 1.0
        else:
            return 0.6  # Partial credit for abstract outside range
    
    def _score_heading_hierarchy(self, document: FormattedDocument) -> float:
        """
        Score based on heading hierarchy correctness
        Checks if sections have properly formatted headings
        Returns: 0.0 to 1.0
        """
        # Sections that should have formatted headings
        sections_needing_headings = [
            SectionType.ABSTRACT,
            SectionType.KEYWORDS,
            SectionType.INTRODUCTION,
            SectionType.RELATED_WORK,
            SectionType.LITERATURE_REVIEW,
            SectionType.METHODOLOGY,
            SectionType.RESULTS,
            SectionType.DISCUSSION,
            SectionType.CONCLUSION,
            SectionType.FUTURE_WORK,
            SectionType.ACKNOWLEDGMENTS,
            SectionType.REFERENCES,
            SectionType.APPENDIX
        ]
        
        # Count sections that need headings
        sections_with_heading_requirement = [
            s for s in document.sections 
            if s.type in sections_needing_headings
        ]
        
        if not sections_with_heading_requirement:
            return 1.0  # No sections need headings, perfect score
        
        # Count sections with properly formatted headings
        properly_formatted = 0
        for section in sections_with_heading_requirement:
            # Check if section has a formatted heading
            if section.formatted_heading and section.formatted_heading.strip():
                properly_formatted += 1
        
        return properly_formatted / len(sections_with_heading_requirement)
    
    def _score_formatting_consistency(self, document: FormattedDocument, issues: List[Issue]) -> float:
        """
        Score based on formatting consistency
        Penalizes high-severity issues
        Returns: 0.0 to 1.0
        """
        # Count high-severity issues
        high_severity_issues = [
            issue for issue in issues 
            if issue.severity == IssueSeverity.HIGH
        ]
        
        # Start with perfect score
        score = 1.0
        
        # Deduct 0.2 for each high-severity issue (max 5 issues = 0 score)
        penalty = len(high_severity_issues) * 0.2
        score = max(0.0, score - penalty)
        
        return score
