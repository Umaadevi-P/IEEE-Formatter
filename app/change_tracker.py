"""Change tracking module for IEEE Paper Formatter"""
from app.models import Fix, Section, ParsedDocument, FormattedDocument
from typing import List, Dict, Any


class ChangeTracker:
    """
    Tracks all changes made during formatting process
    Records original values, formatted values, and reasons for changes
    """
    
    def __init__(self):
        """Initialize change tracker"""
        self.fixes: List[Fix] = []
    
    def track_changes(
        self,
        document_before: ParsedDocument,
        document_after: FormattedDocument
    ) -> List[Fix]:
        """
        Track all changes between original and formatted documents
        Returns list of Fix objects documenting each change
        
        Requirements: 12.3
        """
        self.fixes = []
        
        # Create mappings for easier comparison
        before_sections_by_id = {s.id: s for s in document_before.sections}
        after_sections_by_id = {s.id: s for s in document_after.sections}
        
        # Track section reordering
        self._track_section_reordering(document_before, document_after)
        
        # Track changes for each section
        for after_section in document_after.sections:
            section_id = after_section.id
            
            # Find corresponding before section
            before_section = before_sections_by_id.get(section_id)
            
            if before_section:
                # Track heading changes
                self._track_heading_changes(before_section, after_section)
                
                # Track font rule changes
                self._track_font_changes(before_section, after_section)
                
                # Track content changes (grammar corrections)
                self._track_content_changes(before_section, after_section)
                
                # Track section type changes
                self._track_section_type_changes(before_section, after_section)
        
        return self.fixes
    
    def _track_section_reordering(
        self,
        document_before: ParsedDocument,
        document_after: FormattedDocument
    ) -> None:
        """Track section reordering changes"""
        # Create position mappings
        before_positions = {s.id: idx for idx, s in enumerate(document_before.sections)}
        after_positions = {s.id: idx for idx, s in enumerate(document_after.sections)}
        
        # Check if any sections were reordered
        for section_id in after_positions:
            if section_id in before_positions:
                before_pos = before_positions[section_id]
                after_pos = after_positions[section_id]
                
                if before_pos != after_pos:
                    # Find the section to get its type
                    section = next(s for s in document_after.sections if s.id == section_id)
                    
                    self.fixes.append(Fix(
                        section_id=section_id,
                        type="section_reordering",
                        original=f"Position {before_pos + 1}",
                        formatted=f"Position {after_pos + 1}",
                        reason=f"Section '{section.type.value}' reordered to match IEEE conference format standard sequence"
                    ))
    
    def _track_heading_changes(
        self,
        before_section: Section,
        after_section: Section
    ) -> None:
        """Track heading formatting changes"""
        # Check if heading was added
        if not before_section.original_heading and after_section.formatted_heading:
            self.fixes.append(Fix(
                section_id=after_section.id,
                type="heading_added",
                original=None,
                formatted=after_section.formatted_heading,
                reason=f"Added IEEE-compliant heading for {after_section.type.value} section"
            ))
        
        # Check if heading was formatted
        elif before_section.original_heading and after_section.formatted_heading:
            if before_section.original_heading != after_section.formatted_heading:
                self.fixes.append(Fix(
                    section_id=after_section.id,
                    type="heading_formatting",
                    original=before_section.original_heading,
                    formatted=after_section.formatted_heading,
                    reason="Applied IEEE heading format: Roman numerals, ALL CAPS, and bold styling"
                ))
    
    def _track_font_changes(
        self,
        before_section: Section,
        after_section: Section
    ) -> None:
        """Track font rule application changes"""
        # Check if font rule was applied
        if not before_section.font_rule and after_section.font_rule:
            font_rule = after_section.font_rule
            self.fixes.append(Fix(
                section_id=after_section.id,
                type="font_formatting",
                original="No font formatting",
                formatted=f"{font_rule.font_family}, {font_rule.font_size}pt, "
                          f"{'Bold' if font_rule.bold else 'Normal'}, "
                          f"{'Italic' if font_rule.italic else 'Regular'}, "
                          f"{font_rule.alignment.capitalize()} aligned",
                reason=f"Applied IEEE font rules for {after_section.type.value} section"
            ))
        
        # Check if heading font rule was applied
        if not before_section.heading_font_rule and after_section.heading_font_rule:
            heading_font = after_section.heading_font_rule
            self.fixes.append(Fix(
                section_id=after_section.id,
                type="heading_font_formatting",
                original="No heading font formatting",
                formatted=f"{heading_font.font_family}, {heading_font.font_size}pt, Bold",
                reason="Applied IEEE heading font rules: Times New Roman, 10pt, Bold"
            ))
    
    def _track_content_changes(
        self,
        before_section: Section,
        after_section: Section
    ) -> None:
        """Track content changes (grammar corrections)"""
        # Only track if content actually changed
        if before_section.content != after_section.content:
            # Calculate change magnitude
            before_words = len(before_section.content.split())
            after_words = len(after_section.content.split())
            word_diff = after_words - before_words
            
            # Only track significant changes (more than just whitespace)
            if abs(word_diff) > 0 or before_section.content.strip() != after_section.content.strip():
                change_description = f"Grammar and spelling corrections applied"
                if word_diff > 0:
                    change_description += f" (+{word_diff} words)"
                elif word_diff < 0:
                    change_description += f" ({word_diff} words)"
                
                self.fixes.append(Fix(
                    section_id=after_section.id,
                    type="grammar_correction",
                    original=f"{before_words} words",
                    formatted=f"{after_words} words",
                    reason=change_description
                ))
    
    def _track_section_type_changes(
        self,
        before_section: Section,
        after_section: Section
    ) -> None:
        """Track section type detection/correction changes"""
        if before_section.type != after_section.type:
            self.fixes.append(Fix(
                section_id=after_section.id,
                type="section_type_correction",
                original=before_section.type.value,
                formatted=after_section.type.value,
                reason="Section type detected and corrected based on content and heading keywords"
            ))
    
    def get_fixes(self) -> List[Fix]:
        """Return all tracked fixes"""
        return self.fixes
    
    def get_fixes_by_type(self, fix_type: str) -> List[Fix]:
        """Return fixes filtered by type"""
        return [fix for fix in self.fixes if fix.type == fix_type]
    
    def get_fixes_by_section(self, section_id: str) -> List[Fix]:
        """Return fixes for a specific section"""
        return [fix for fix in self.fixes if fix.section_id == section_id]
    
    def get_fix_summary(self) -> Dict[str, Any]:
        """
        Return summary of all changes
        Useful for displaying change statistics
        """
        fix_types = {}
        for fix in self.fixes:
            if fix.type not in fix_types:
                fix_types[fix.type] = 0
            fix_types[fix.type] += 1
        
        return {
            "total_changes": len(self.fixes),
            "changes_by_type": fix_types,
            "sections_affected": len(set(fix.section_id for fix in self.fixes))
        }
