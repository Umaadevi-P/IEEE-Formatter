"""Citation detection and conversion module for IEEE format"""
from app.models import Section, SectionType
from typing import List, Dict, Tuple, Optional
import re


class CitationConverter:
    """Detects and converts citations to IEEE numbered format"""
    
    def __init__(self):
        """Initialize citation converter"""
        self.citation_map: Dict[str, int] = {}  # Maps original citation to IEEE number
        self.next_citation_number = 1
    
    def convert_references(self, sections: List[Section]) -> List[Section]:
        """
        Convert citations in document to IEEE numbered format
        
        Process:
        1. Find References section
        2. Extract individual citations and assign numbers
        3. Convert in-text citations to numbered format
        4. Format References section with IEEE numbering
        
        Returns: List of sections with converted citations
        """
        # Find References section
        references_section = None
        references_index = -1
        
        for i, section in enumerate(sections):
            if section.type == SectionType.REFERENCES:
                references_section = section
                references_index = i
                break
        
        if not references_section:
            # No references section found, return sections unchanged
            return sections
        
        # Extract and number individual citations from References section
        citations = self._extract_citations(references_section.content)
        
        # Build citation map (original text -> IEEE number)
        self._build_citation_map(citations)
        
        # Convert References section to IEEE format
        converted_sections = []
        for i, section in enumerate(sections):
            if i == references_index:
                # Format References section with IEEE numbering
                formatted_content = self._format_references_section(citations)
                converted_section = section.model_copy(deep=True)
                converted_section.content = formatted_content
                converted_sections.append(converted_section)
            else:
                # Convert in-text citations in other sections
                converted_section = self._convert_intext_citations(section)
                converted_sections.append(converted_section)
        
        return converted_sections
    
    def _extract_citations(self, references_content: str) -> List[str]:
        """
        Extract individual citation entries from References section
        
        Handles various citation formats:
        - Numbered: [1] Author, Title...
        - Bulleted: • Author, Title...
        - Plain paragraphs separated by blank lines
        """
        citations = []
        
        # Split by common citation separators
        lines = references_content.split('\n')
        
        current_citation = []
        
        for line in lines:
            line = line.strip()
            
            if not line:
                # Empty line might indicate end of citation
                if current_citation:
                    citations.append(' '.join(current_citation))
                    current_citation = []
                continue
            
            # Check if line starts a new citation
            # Common patterns: [1], 1., [Author], etc.
            if self._is_citation_start(line):
                # Save previous citation
                if current_citation:
                    citations.append(' '.join(current_citation))
                    current_citation = []
                
                # Remove existing numbering/bullets
                clean_line = self._remove_citation_prefix(line)
                current_citation.append(clean_line)
            else:
                # Continuation of current citation
                current_citation.append(line)
        
        # Add last citation
        if current_citation:
            citations.append(' '.join(current_citation))
        
        # If no citations were detected (no clear separators), try splitting by periods
        # followed by capital letters (common in some formats)
        if not citations and references_content.strip():
            # Fallback: treat each sentence-like block as a citation
            # This is a simple heuristic
            potential_citations = re.split(r'\.\s+(?=[A-Z])', references_content)
            citations = [c.strip() + '.' for c in potential_citations if c.strip()]
        
        return citations
    
    def _is_citation_start(self, line: str) -> bool:
        """Check if line starts a new citation entry"""
        # Patterns that indicate start of citation:
        # [1], [2], etc.
        if re.match(r'^\[\d+\]', line):
            return True
        
        # 1., 2., etc.
        if re.match(r'^\d+\.', line):
            return True
        
        # Bullet points
        if line.startswith('•') or line.startswith('-') or line.startswith('*'):
            return True
        
        # Author name pattern (Last, First or Last, F.)
        if re.match(r'^[A-Z][a-z]+,\s+[A-Z]', line):
            return True
        
        return False
    
    def _remove_citation_prefix(self, line: str) -> str:
        """Remove existing numbering or bullets from citation"""
        # Remove [1], [2], etc.
        line = re.sub(r'^\[\d+\]\s*', '', line)
        
        # Remove 1., 2., etc.
        line = re.sub(r'^\d+\.\s*', '', line)
        
        # Remove bullets
        line = re.sub(r'^[•\-*]\s*', '', line)
        
        return line.strip()
    
    def _build_citation_map(self, citations: List[str]) -> None:
        """Build mapping from citation text to IEEE number"""
        self.citation_map = {}
        self.next_citation_number = 1
        
        for citation in citations:
            # Use first 100 chars as key (to handle long citations)
            key = citation[:100].strip()
            self.citation_map[key] = self.next_citation_number
            self.next_citation_number += 1
    
    def _format_references_section(self, citations: List[str]) -> str:
        """Format References section with IEEE numbered format [1], [2], etc."""
        formatted_refs = []
        
        for i, citation in enumerate(citations, start=1):
            # IEEE format: [1] Citation text
            formatted_refs.append(f"[{i}] {citation}")
        
        return '\n\n'.join(formatted_refs)
    
    def _convert_intext_citations(self, section: Section) -> Section:
        """
        Convert in-text citations to IEEE numbered format
        
        Handles various citation formats:
        - (Author, Year) -> [N]
        - (Author et al., Year) -> [N]
        - Author (Year) -> Author [N]
        - [Author, Year] -> [N]
        """
        converted_section = section.model_copy(deep=True)
        content = section.content
        
        # Pattern 1: (Author, Year) or (Author et al., Year)
        # Replace with [N] where N is the citation number
        # This is a simplified conversion - in production, we'd need to match
        # the author/year to the actual reference
        
        # For now, we'll convert common citation patterns to generic [N] format
        # where N increments for each unique citation
        
        # Pattern: (Author, YYYY) or (Author et al., YYYY)
        content = re.sub(
            r'\(([A-Z][a-z]+(?:\s+et\s+al\.)?),?\s+\d{4}\)',
            lambda m: self._get_citation_number(m.group(0)),
            content
        )
        
        # Pattern: [Author, YYYY] or [Author et al., YYYY]
        content = re.sub(
            r'\[([A-Z][a-z]+(?:\s+et\s+al\.)?),?\s+\d{4}\]',
            lambda m: self._get_citation_number(m.group(0)),
            content
        )
        
        # Pattern: Author (YYYY) - keep author name, convert year to [N]
        content = re.sub(
            r'([A-Z][a-z]+(?:\s+et\s+al\.)?)\s+\(\d{4}\)',
            lambda m: f"{m.group(1)} {self._get_citation_number(m.group(0))}",
            content
        )
        
        converted_section.content = content
        return converted_section
    
    def _get_citation_number(self, citation_text: str) -> str:
        """
        Get or assign IEEE number for a citation
        
        For in-text citations, we assign numbers sequentially as we encounter them
        In a production system, we would match to the References section
        """
        # Use citation text as key
        key = citation_text.strip()
        
        if key not in self.citation_map:
            self.citation_map[key] = self.next_citation_number
            self.next_citation_number += 1
        
        return f"[{self.citation_map[key]}]"
    
    def get_citation_count(self) -> int:
        """Return total number of citations detected"""
        return len(self.citation_map)
    
    def reset(self) -> None:
        """Reset citation map and counter"""
        self.citation_map = {}
        self.next_citation_number = 1
