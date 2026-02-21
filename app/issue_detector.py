"""Issue detection module for IEEE Paper Formatter"""
from app.models import Issue, IssueSeverity, Section, SectionType, ParsedDocument, FormattedDocument
from typing import List, Set


class IssueDetector:
    """Detects formatting issues in documents"""
    
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
    
    def detect_issues(self, document: ParsedDocument) -> List[Issue]:
        """
        Detect all formatting issues in the document
        Returns list of issues with severity levels
        """
        issues: List[Issue] = []
        
        # Detect missing required sections
        issues.extend(self._detect_missing_sections(document))
        
        # Detect out-of-order sections
        issues.extend(self._detect_section_order_issues(document))
        
        # Detect abstract word count violations
        issues.extend(self._detect_abstract_word_count_issues(document))
        
        # Detect missing section headings
        issues.extend(self._detect_missing_headings(document))
        
        return issues
    
    def _detect_missing_sections(self, document: ParsedDocument) -> List[Issue]:
        """
        Detect missing required sections
        Returns high-severity issues for each missing required section
        """
        issues: List[Issue] = []
        
        # Get set of section types present in document
        present_sections: Set[SectionType] = {section.type for section in document.sections}
        
        # Check each required section
        for required_section in self.REQUIRED_SECTIONS:
            if required_section not in present_sections:
                issues.append(Issue(
                    type="missing_required_section",
                    section=required_section.value,
                    severity=IssueSeverity.HIGH,
                    message=f"Required section '{required_section.value}' is missing",
                    current=None,
                    expected=required_section.value
                ))
        
        return issues
    
    def _detect_section_order_issues(self, document: ParsedDocument) -> List[Issue]:
        """
        Detect sections that are out of IEEE standard order
        Returns medium-severity issues for out-of-order sections
        """
        issues: List[Issue] = []
        
        # Build a mapping of section type to expected position
        expected_positions = {
            section_type: idx 
            for idx, section_type in enumerate(self.IEEE_SECTION_ORDER)
        }
        
        # Track the last position we saw
        last_position = -1
        
        for section in document.sections:
            # Skip UNKNOWN sections as they don't have a defined order
            if section.type == SectionType.UNKNOWN:
                continue
            
            # Get expected position for this section type
            expected_pos = expected_positions.get(section.type, -1)
            
            # Check if this section appears before a section that should come after it
            if expected_pos != -1 and expected_pos < last_position:
                # Find what section type should come before this one
                previous_section_types = [
                    st for st in self.IEEE_SECTION_ORDER 
                    if expected_positions.get(st, -1) == last_position
                ]
                
                if previous_section_types:
                    issues.append(Issue(
                        type="section_out_of_order",
                        section=section.type.value,
                        severity=IssueSeverity.MEDIUM,
                        message=f"Section '{section.type.value}' appears after '{previous_section_types[0].value}' but should come before it",
                        current=section.type.value,
                        expected=f"Should appear before {previous_section_types[0].value}"
                    ))
            
            if expected_pos != -1:
                last_position = max(last_position, expected_pos)
        
        return issues
    
    def _detect_abstract_word_count_issues(self, document: ParsedDocument) -> List[Issue]:
        """
        Detect abstract word count violations (not 150-250 words)
        Returns medium-severity issue if abstract is outside range
        """
        issues: List[Issue] = []
        
        # Find abstract section
        abstract_sections = [s for s in document.sections if s.type == SectionType.ABSTRACT]
        
        if not abstract_sections:
            # Missing abstract is already detected by _detect_missing_sections
            return issues
        
        # Check word count for each abstract (should only be one)
        for abstract in abstract_sections:
            word_count = abstract.word_count
            
            if word_count < self.ABSTRACT_MIN_WORDS:
                issues.append(Issue(
                    type="abstract_word_count_violation",
                    section=SectionType.ABSTRACT.value,
                    severity=IssueSeverity.MEDIUM,
                    message=f"Abstract has {word_count} words but should have {self.ABSTRACT_MIN_WORDS}-{self.ABSTRACT_MAX_WORDS} words",
                    current=word_count,
                    expected=f"{self.ABSTRACT_MIN_WORDS}-{self.ABSTRACT_MAX_WORDS} words"
                ))
            elif word_count > self.ABSTRACT_MAX_WORDS:
                issues.append(Issue(
                    type="abstract_word_count_violation",
                    section=SectionType.ABSTRACT.value,
                    severity=IssueSeverity.MEDIUM,
                    message=f"Abstract has {word_count} words but should have {self.ABSTRACT_MIN_WORDS}-{self.ABSTRACT_MAX_WORDS} words",
                    current=word_count,
                    expected=f"{self.ABSTRACT_MIN_WORDS}-{self.ABSTRACT_MAX_WORDS} words"
                ))
        
        return issues
    
    def _detect_missing_headings(self, document: ParsedDocument) -> List[Issue]:
        """
        Detect sections that are missing headings
        Returns low-severity issues for sections without headings
        """
        issues: List[Issue] = []
        
        # Sections that should have headings (all except Title)
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
        
        for section in document.sections:
            # Check if this section type should have a heading
            if section.type in sections_needing_headings:
                # Check if heading is missing or empty
                if not section.original_heading or not section.original_heading.strip():
                    issues.append(Issue(
                        type="missing_section_heading",
                        section=section.type.value,
                        severity=IssueSeverity.LOW,
                        message=f"Section '{section.type.value}' is missing a heading",
                        current=None,
                        expected=f"Heading for {section.type.value}"
                    ))
        
        return issues
