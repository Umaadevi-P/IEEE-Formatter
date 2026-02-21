"""User edits application module for IEEE Paper Formatter"""
from app.models import (
    UserEdits,
    ParsedDocument,
    Section,
    SectionType,
    FontRule,
    Issue,
    IssueSeverity
)
from typing import List, Dict, Tuple
import uuid


class UserEditsApplicator:
    """Applies user-provided edits to documents"""
    
    def __init__(self, allow_auto_generation: bool = False):
        """
        Initialize UserEditsApplicator
        
        Args:
            allow_auto_generation: Whether to allow automatic section generation
                                   Default is False for safety
        """
        self.allow_auto_generation = allow_auto_generation
    
    def apply_edits(self, document: ParsedDocument, edits: UserEdits) -> ParsedDocument:
        """
        Apply user edits to document before final formatting
        
        SAFETY: This method will NOT auto-generate any sections unless
        allow_auto_generation is explicitly set to True. It only applies
        user-provided edits.
        
        This implements Requirements 6.1-6.5:
        - Flags missing sections but does NOT auto-generate content
        - Only creates sections when user explicitly provides the content
        - Never adds sections without user approval
        
        Args:
            document: The parsed document to modify
            edits: User-provided corrections and additions
            
        Returns:
            Modified ParsedDocument with edits applied
        """
        # CRITICAL SAFETY CHECK: Verify auto-generation is disabled
        # This ensures we never add sections without explicit user approval
        if not self.allow_auto_generation:
            # Only apply user-provided edits, never auto-generate
            # This is the core safety mechanism per Requirements 6.1-6.5
            pass
        
        # Create a copy of sections to avoid modifying original
        modified_sections = [section.model_copy(deep=True) for section in document.sections]
        
        # Apply section type corrections
        if edits.section_corrections:
            modified_sections = self._apply_section_corrections(
                modified_sections, 
                edits.section_corrections
            )
        
        # Apply author information (only if user provided it)
        if edits.author_name or edits.author_email:
            modified_sections = self._apply_author_info(
                modified_sections,
                edits.author_name,
                edits.author_email
            )
        
        # Apply affiliation information (only if user provided it)
        if edits.affiliation:
            modified_sections = self._apply_affiliation(
                modified_sections,
                edits.affiliation
            )
        
        # Apply keywords (only if user provided them)
        if edits.keywords:
            modified_sections = self._apply_keywords(
                modified_sections,
                edits.keywords
            )
        
        # Create updated document
        updated_document = ParsedDocument(
            sections=modified_sections,
            metadata={
                **document.metadata,
                "user_edits_applied": True,
                "auto_generation_allowed": self.allow_auto_generation,
                "edits_summary": self._create_edits_summary(edits)
            }
        )
        
        return updated_document
    
    def check_missing_sections_without_generation(
        self, 
        document: ParsedDocument
    ) -> Tuple[List[Issue], List[SectionType]]:
        """
        Check for missing sections and flag them as issues WITHOUT auto-generating
        
        This is the safety mechanism that ensures we never auto-generate content
        without explicit user approval.
        
        Args:
            document: The parsed document to check
            
        Returns:
            Tuple of (issues, missing_section_types)
            - issues: List of Issue objects for missing sections
            - missing_section_types: List of SectionType values that are missing
        """
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
        
        # Get set of section types present in document
        present_sections = {section.type for section in document.sections}
        
        # Find missing sections
        missing_sections = REQUIRED_SECTIONS - present_sections
        
        # Create issues for missing sections
        issues = []
        for missing_section in missing_sections:
            issues.append(Issue(
                type="missing_required_section",
                section=missing_section.value,
                severity=IssueSeverity.HIGH,
                message=f"Required section '{missing_section.value}' is missing. Please add this section manually.",
                current=None,
                expected=missing_section.value
            ))
        
        return issues, list(missing_sections)
    
    def _apply_section_corrections(
        self, 
        sections: List[Section], 
        corrections: Dict[str, SectionType]
    ) -> List[Section]:
        """
        Apply user corrections to section types
        
        Args:
            sections: List of sections to modify
            corrections: Dict mapping section IDs to corrected SectionType
            
        Returns:
            Modified list of sections
        """
        for section in sections:
            if section.id in corrections:
                # Update section type based on user correction
                section.type = corrections[section.id]
        
        return sections
    
    def _apply_author_info(
        self,
        sections: List[Section],
        author_name: str = None,
        author_email: str = None
    ) -> List[Section]:
        """
        Apply user-provided author information
        
        SAFETY: Only creates AUTHORS section if user explicitly provided
        author information. Never auto-generates content.
        
        Args:
            sections: List of sections to modify
            author_name: Author's name
            author_email: Author's email
            
        Returns:
            Modified list of sections with author info added/updated
        """
        # SAFETY CHECK: Only proceed if user provided author information
        # This ensures we never auto-generate an AUTHORS section
        if not author_name and not author_email:
            # No user-provided author info, don't create section
            return sections
        
        # Find existing AUTHORS section
        authors_section = None
        authors_index = None
        
        for idx, section in enumerate(sections):
            if section.type == SectionType.AUTHORS:
                authors_section = section
                authors_index = idx
                break
        
        # Build author content from user-provided data only
        author_content = ""
        if author_name:
            author_content = author_name
        if author_email:
            if author_content:
                author_content += f"\n{author_email}"
            else:
                author_content = author_email
        
        if not author_content:
            return sections
        
        if authors_section:
            # Update existing AUTHORS section with user-provided content
            authors_section.content = author_content
            authors_section.word_count = len(author_content.split())
        else:
            # Create new AUTHORS section ONLY because user provided content
            # This is NOT auto-generation - it's applying user edits
            # Insert after TITLE if it exists, otherwise at the beginning
            title_index = -1
            for idx, section in enumerate(sections):
                if section.type == SectionType.TITLE:
                    title_index = idx
                    break
            
            new_authors_section = Section(
                id=str(uuid.uuid4()),
                type=SectionType.AUTHORS,
                content=author_content,
                original_heading="Authors",
                word_count=len(author_content.split())
            )
            
            insert_position = title_index + 1 if title_index >= 0 else 0
            sections.insert(insert_position, new_authors_section)
        
        return sections
    
    def _apply_affiliation(
        self,
        sections: List[Section],
        affiliation: str
    ) -> List[Section]:
        """
        Apply user-provided affiliation information
        
        Args:
            sections: List of sections to modify
            affiliation: Affiliation text
            
        Returns:
            Modified list of sections with affiliation added/updated
        """
        # Find existing AFFILIATION section
        affiliation_section = None
        affiliation_index = None
        
        for idx, section in enumerate(sections):
            if section.type == SectionType.AFFILIATION:
                affiliation_section = section
                affiliation_index = idx
                break
        
        if affiliation_section:
            # Update existing AFFILIATION section
            affiliation_section.content = affiliation
            affiliation_section.word_count = len(affiliation.split())
        else:
            # Create new AFFILIATION section
            # Insert after AUTHORS if it exists, otherwise after TITLE
            insert_position = 0
            for idx, section in enumerate(sections):
                if section.type == SectionType.AUTHORS:
                    insert_position = idx + 1
                    break
                elif section.type == SectionType.TITLE:
                    insert_position = idx + 1
            
            new_affiliation_section = Section(
                id=str(uuid.uuid4()),
                type=SectionType.AFFILIATION,
                content=affiliation,
                original_heading="Affiliation",
                word_count=len(affiliation.split())
            )
            
            sections.insert(insert_position, new_affiliation_section)
        
        return sections
    
    def _apply_keywords(
        self,
        sections: List[Section],
        keywords: List[str]
    ) -> List[Section]:
        """
        Apply user-provided keywords
        
        Args:
            sections: List of sections to modify
            keywords: List of keyword strings
            
        Returns:
            Modified list of sections with keywords added/updated
        """
        # Find existing KEYWORDS section
        keywords_section = None
        keywords_index = None
        
        for idx, section in enumerate(sections):
            if section.type == SectionType.KEYWORDS:
                keywords_section = section
                keywords_index = idx
                break
        
        # Format keywords as comma-separated list
        keywords_content = ", ".join(keywords)
        
        if keywords_section:
            # Update existing KEYWORDS section
            keywords_section.content = keywords_content
            keywords_section.word_count = len(keywords_content.split())
        else:
            # Create new KEYWORDS section
            # Insert after ABSTRACT if it exists
            insert_position = 0
            for idx, section in enumerate(sections):
                if section.type == SectionType.ABSTRACT:
                    insert_position = idx + 1
                    break
            
            new_keywords_section = Section(
                id=str(uuid.uuid4()),
                type=SectionType.KEYWORDS,
                content=keywords_content,
                original_heading="Index Terms",
                word_count=len(keywords_content.split())
            )
            
            sections.insert(insert_position, new_keywords_section)
        
        return sections
    
    def _create_edits_summary(self, edits: UserEdits) -> Dict[str, bool]:
        """
        Create a summary of which edits were applied
        
        Args:
            edits: UserEdits object
            
        Returns:
            Dictionary indicating which edit types were applied
        """
        return {
            "author_info_applied": bool(edits.author_name or edits.author_email),
            "affiliation_applied": bool(edits.affiliation),
            "keywords_applied": bool(edits.keywords),
            "section_corrections_applied": bool(edits.section_corrections)
        }
