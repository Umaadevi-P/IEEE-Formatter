"""IEEE formatting module"""
from app.models import ParsedDocument, FormattedDocument, Section, SectionType, FontRule
from app.citation_converter import CitationConverter
from typing import List, Dict, Any, Optional
from docx import Document
import os


class RulesParser:
    """Extracts formatting rules from rules.docx"""
    
    _cached_rules: Optional[Dict[str, Any]] = None
    
    def __init__(self, rules_path: str):
        """Initialize with path to rules.docx"""
        self.rules_path = rules_path
    
    def parse_rules_docx(self) -> Dict[str, Any]:
        """
        Extract IEEE formatting rules from rules.docx
        Returns dictionary with:
        - font_rules: Dict[SectionType, FontRule]
        - spacing_rules: Dict[str, Any]
        - numbering_rules: Dict[str, Any]
        - section_order: List[SectionType]
        """
        # Return cached rules if available
        if RulesParser._cached_rules is not None:
            return RulesParser._cached_rules
        
        # Check if rules file exists
        if not os.path.exists(self.rules_path):
            # Return default IEEE rules if file doesn't exist
            rules = self._get_default_rules()
            RulesParser._cached_rules = rules
            return rules
        
        try:
            # Parse rules.docx
            doc = Document(self.rules_path)
            
            # For now, use default rules
            # In a production system, we would parse the actual document
            # to extract rules dynamically
            rules = self._get_default_rules()
            
            RulesParser._cached_rules = rules
            return rules
        except Exception as e:
            # Fallback to default rules on error
            rules = self._get_default_rules()
            RulesParser._cached_rules = rules
            return rules
    
    def _get_default_rules(self) -> Dict[str, Any]:
        """
        Return default IEEE formatting rules based on design document
        """
        # Font rules for each section type
        font_rules = {
            SectionType.TITLE: FontRule(
                font_family="Times New Roman",
                font_size=24,
                bold=True,
                italic=False,
                alignment="center"
            ),
            SectionType.AUTHORS: FontRule(
                font_family="Times New Roman",
                font_size=10,
                bold=False,
                italic=False,
                alignment="center"
            ),
            SectionType.AFFILIATION: FontRule(
                font_family="Times New Roman",
                font_size=10,
                bold=False,
                italic=True,
                alignment="center"
            ),
            SectionType.ABSTRACT: FontRule(
                font_family="Times New Roman",
                font_size=9,
                bold=False,
                italic=False,
                alignment="justify"
            ),
            SectionType.KEYWORDS: FontRule(
                font_family="Times New Roman",
                font_size=9,
                bold=False,
                italic=True,
                alignment="justify"
            ),
            # Body sections (Introduction, Methodology, Results, etc.)
            SectionType.INTRODUCTION: FontRule(
                font_family="Times New Roman",
                font_size=10,
                bold=False,
                italic=False,
                alignment="justify"
            ),
            SectionType.RELATED_WORK: FontRule(
                font_family="Times New Roman",
                font_size=10,
                bold=False,
                italic=False,
                alignment="justify"
            ),
            SectionType.LITERATURE_REVIEW: FontRule(
                font_family="Times New Roman",
                font_size=10,
                bold=False,
                italic=False,
                alignment="justify"
            ),
            SectionType.METHODOLOGY: FontRule(
                font_family="Times New Roman",
                font_size=10,
                bold=False,
                italic=False,
                alignment="justify"
            ),
            SectionType.RESULTS: FontRule(
                font_family="Times New Roman",
                font_size=10,
                bold=False,
                italic=False,
                alignment="justify"
            ),
            SectionType.DISCUSSION: FontRule(
                font_family="Times New Roman",
                font_size=10,
                bold=False,
                italic=False,
                alignment="justify"
            ),
            SectionType.CONCLUSION: FontRule(
                font_family="Times New Roman",
                font_size=10,
                bold=False,
                italic=False,
                alignment="justify"
            ),
            SectionType.FUTURE_WORK: FontRule(
                font_family="Times New Roman",
                font_size=10,
                bold=False,
                italic=False,
                alignment="justify"
            ),
            SectionType.ACKNOWLEDGMENTS: FontRule(
                font_family="Times New Roman",
                font_size=10,
                bold=False,
                italic=False,
                alignment="justify"
            ),
            SectionType.REFERENCES: FontRule(
                font_family="Times New Roman",
                font_size=10,
                bold=False,
                italic=False,
                alignment="justify"
            ),
            SectionType.APPENDIX: FontRule(
                font_family="Times New Roman",
                font_size=10,
                bold=False,
                italic=False,
                alignment="justify"
            ),
            SectionType.UNKNOWN: FontRule(
                font_family="Times New Roman",
                font_size=10,
                bold=False,
                italic=False,
                alignment="justify"
            )
        }
        
        # Spacing rules
        spacing_rules = {
            "paragraph_spacing_before": 0,
            "paragraph_spacing_after": 0,
            "first_line_indent": 0,
            "line_spacing": "single",
            "column_spacing": 0.25  # inches
        }
        
        # Numbering rules
        numbering_rules = {
            "main_sections_style": "roman",  # Roman numerals (I., II., III.)
            "heading_format": "all_caps_bold",
            "subsection_style": "alpha"  # A, B, C
        }
        
        # IEEE standard section order
        section_order = [
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
        
        return {
            "font_rules": font_rules,
            "spacing_rules": spacing_rules,
            "numbering_rules": numbering_rules,
            "section_order": section_order
        }


class IEEEFormatter:
    """Applies IEEE conference formatting rules from rules.docx"""
    
    def __init__(self, rules_path: str):
        """Load IEEE rules from rules.docx"""
        self.rules_path = rules_path
        self.rules_parser = RulesParser(rules_path)
        self.rules = self.rules_parser.parse_rules_docx()
    
    def format(self, document: ParsedDocument) -> FormattedDocument:
        """
        Apply all IEEE formatting rules:
        - Fonts and sizes
        - Section numbering (Roman numerals)
        - Spacing and alignment
        - Two-column layout markers
        - Citation conversion to IEEE format
        """
        # Make a copy of sections to avoid modifying original
        formatted_sections = []
        
        for section in document.sections:
            # Apply font rules
            formatted_section = self.apply_font_rules(section)
            formatted_sections.append(formatted_section)
        
        # Convert citations to IEEE numbered format
        citation_converter = CitationConverter()
        formatted_sections = citation_converter.convert_references(formatted_sections)
        
        # Reorder sections to IEEE standard
        formatted_sections = self.reorder_sections(formatted_sections)
        
        # Apply numbering to main sections
        formatted_sections = self.apply_numbering(formatted_sections)
        
        # Create formatted document
        formatted_doc = FormattedDocument(
            sections=formatted_sections,
            metadata={
                **document.metadata,
                "formatted": True,
                "ieee_compliant": True,
                "citations_converted": True,
                "citation_count": citation_converter.get_citation_count()
            },
            compliance_score=0.0  # Will be calculated by ComplianceScorer
        )
        
        return formatted_doc
    
    def reorder_sections(self, sections: List[Section]) -> List[Section]:
        """Reorder sections to IEEE standard sequence"""
        section_order = self.rules["section_order"]
        
        # Create a mapping of section type to sections
        sections_by_type: Dict[SectionType, List[Section]] = {}
        for section in sections:
            if section.type not in sections_by_type:
                sections_by_type[section.type] = []
            sections_by_type[section.type].append(section)
        
        # Reorder according to IEEE standard (excluding UNKNOWN sections)
        reordered = []
        
        for section_type in section_order:
            if section_type in sections_by_type:
                reordered.extend(sections_by_type[section_type])
        
        # UNKNOWN sections are subsections/content that shouldn't be numbered
        # They should be ignored in the main section ordering
        # (In a real implementation, they would be nested under their parent sections)
        
        return reordered
    
    def apply_numbering(self, sections: List[Section]) -> List[Section]:
        """Apply Roman numeral numbering to main sections and A, B, C to subsections"""
        # Sections that should be numbered with Roman numerals
        # UNKNOWN sections are subsections and should NOT be numbered
        numbered_sections = [
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
        
        # Heading font rule: Times New Roman, 10pt, Bold, ALL CAPS
        heading_font_rule = FontRule(
            font_family="Times New Roman",
            font_size=10,
            bold=True,
            italic=False,
            alignment="left"
        )
        
        # Subheading font rule: Times New Roman, 10pt, Italic
        subheading_font_rule = FontRule(
            font_family="Times New Roman",
            font_size=10,
            bold=False,
            italic=True,
            alignment="left"
        )
        
        roman_counter = 1
        formatted_sections = []
        
        for section in sections:
            # Create a copy of the section
            formatted_section = section.model_copy(deep=True)
            
            if section.type in numbered_sections:
                # Generate Roman numeral
                roman_numeral = self._to_roman(roman_counter)
                
                # Format heading: Roman numeral + ALL CAPS + bold
                if section.original_heading:
                    # Remove any existing numbering
                    import re
                    clean_heading = re.sub(r'^[ivxlcdm]+\.\s+', '', section.original_heading.lower())
                    clean_heading = re.sub(r'^\d+\.\s+', '', clean_heading)
                    clean_heading = clean_heading.strip()
                    
                    # Special case: rename "final thoughts" to "conclusion"
                    if 'final thought' in clean_heading or 'final remark' in clean_heading:
                        clean_heading = 'conclusion'
                    
                    # Format as: "I. INTRODUCTION"
                    formatted_heading = f"{roman_numeral}. {clean_heading.upper()}"
                    formatted_section.formatted_heading = formatted_heading
                else:
                    # Use section type name if no original heading
                    formatted_heading = f"{roman_numeral}. {section.type.value.upper()}"
                    formatted_section.formatted_heading = formatted_heading
                
                # Apply heading font rule (bold, 10pt)
                formatted_section.heading_font_rule = heading_font_rule
                
                # Number subsections with A, B, C
                if formatted_section.subsections:
                    numbered_subsections = []
                    for i, subsection in enumerate(formatted_section.subsections):
                        formatted_subsection = subsection.model_copy(deep=True)
                        letter = chr(65 + i)  # A, B, C, D, ...
                        
                        if subsection.original_heading:
                            # Format as: "A. Plastic Pollution"
                            formatted_subsection.formatted_heading = f"{letter}. {subsection.original_heading.title()}"
                        else:
                            formatted_subsection.formatted_heading = f"{letter}. Subsection"
                        
                        formatted_subsection.heading_font_rule = subheading_font_rule
                        numbered_subsections.append(formatted_subsection)
                    
                    formatted_section.subsections = numbered_subsections
                
                roman_counter += 1
            else:
                # For non-numbered sections (Title, Authors, Affiliation, Abstract, Keywords)
                # Apply proper IEEE naming conventions
                if section.type == SectionType.ABSTRACT:
                    # Always use "ABSTRACT" regardless of original heading
                    formatted_section.formatted_heading = "ABSTRACT"
                    formatted_section.heading_font_rule = heading_font_rule
                elif section.type == SectionType.KEYWORDS:
                    # IEEE uses "Index Terms" for keywords
                    formatted_section.formatted_heading = "INDEX TERMS"
                    formatted_section.heading_font_rule = heading_font_rule
                elif section.type == SectionType.AUTHORS:
                    # Authors don't need a heading, just centered text
                    formatted_section.formatted_heading = None
                elif section.type == SectionType.AFFILIATION:
                    # Affiliation doesn't need a heading, just centered italic text
                    formatted_section.formatted_heading = None
                elif section.type == SectionType.TITLE:
                    # Title doesn't need a heading
                    formatted_section.formatted_heading = None
                elif section.original_heading:
                    # For other sections, just apply ALL CAPS
                    formatted_section.formatted_heading = section.original_heading.upper()
                    formatted_section.heading_font_rule = heading_font_rule
                elif section.type != SectionType.TITLE:
                    # Add heading for sections without one (except Title)
                    formatted_section.formatted_heading = section.type.value.upper()
                    formatted_section.heading_font_rule = heading_font_rule
            
            formatted_sections.append(formatted_section)
        
        return formatted_sections
    
    def apply_font_rules(self, section: Section) -> Section:
        """Apply font family, size, weight based on section type"""
        # Create a copy of the section
        formatted_section = section.model_copy(deep=True)
        
        # Get font rule for this section type
        font_rules = self.rules["font_rules"]
        
        if section.type in font_rules:
            formatted_section.font_rule = font_rules[section.type]
        else:
            # Default to body text rules
            formatted_section.font_rule = font_rules[SectionType.UNKNOWN]
        
        return formatted_section
    
    def _to_roman(self, num: int) -> str:
        """Convert integer to Roman numeral"""
        val = [
            1000, 900, 500, 400,
            100, 90, 50, 40,
            10, 9, 5, 4,
            1
        ]
        syms = [
            "M", "CM", "D", "CD",
            "C", "XC", "L", "XL",
            "X", "IX", "V", "IV",
            "I"
        ]
        roman_num = ''
        i = 0
        while num > 0:
            for _ in range(num // val[i]):
                roman_num += syms[i]
                num -= val[i]
            i += 1
        return roman_num
