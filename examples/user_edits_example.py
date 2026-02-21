"""
Example demonstrating user edits functionality

This example shows how to:
1. Parse a document
2. Apply user-provided edits (author, keywords, affiliation, section corrections)
3. Check for missing sections without auto-generating
4. Format the edited document
"""

from app.parser import DocumentParser
from app.user_edits import UserEditsApplicator
from app.formatter import IEEEFormatter
from app.models import UserEdits, SectionType
import uuid


def main():
    print("=" * 70)
    print("IEEE Paper Formatter - User Edits Example")
    print("=" * 70)
    
    # Simulate a parsed document with some sections
    from app.models import ParsedDocument, Section
    
    # Create a sample document with some sections
    sections = [
        Section(
            id=str(uuid.uuid4()),
            type=SectionType.TITLE,
            content="Machine Learning for Climate Prediction",
            original_heading=None,
            word_count=5
        ),
        Section(
            id=str(uuid.uuid4()),
            type=SectionType.ABSTRACT,
            content="This paper presents a novel approach to climate prediction using machine learning. " * 20,
            original_heading="Abstract",
            word_count=200
        ),
        Section(
            id=str(uuid.uuid4()),
            type=SectionType.INTRODUCTION,
            content="Climate change is one of the most pressing issues of our time...",
            original_heading="Introduction",
            word_count=50
        ),
        Section(
            id=str(uuid.uuid4()),
            type=SectionType.METHODOLOGY,
            content="We used a deep learning approach with LSTM networks...",
            original_heading="Methods",
            word_count=30
        )
    ]
    
    document = ParsedDocument(
        sections=sections,
        metadata={"filename": "climate_paper.docx"}
    )
    
    print("\n1. Original Document Structure:")
    print("-" * 70)
    for section in document.sections:
        print(f"   - {section.type.value}: {section.word_count} words")
    
    # Check for missing sections (without auto-generating)
    print("\n2. Checking for Missing Sections (Safety Check):")
    print("-" * 70)
    applicator = UserEditsApplicator(allow_auto_generation=False)
    issues, missing_sections = applicator.check_missing_sections_without_generation(document)
    
    if issues:
        print(f"   Found {len(issues)} missing required sections:")
        for issue in issues:
            print(f"   - {issue.section}: {issue.message}")
    else:
        print("   No missing sections!")
    
    # Apply user edits
    print("\n3. Applying User Edits:")
    print("-" * 70)
    
    edits = UserEdits(
        author_name="Dr. Jane Smith",
        author_email="jane.smith@university.edu",
        affiliation="Department of Computer Science, MIT",
        keywords=["machine learning", "climate prediction", "LSTM", "deep learning"],
        section_corrections={}  # No corrections needed in this example
    )
    
    print("   User provided:")
    print(f"   - Author: {edits.author_name}")
    print(f"   - Email: {edits.author_email}")
    print(f"   - Affiliation: {edits.affiliation}")
    print(f"   - Keywords: {', '.join(edits.keywords)}")
    
    # Apply the edits
    edited_document = applicator.apply_edits(document, edits)
    
    print("\n4. Document After Applying Edits:")
    print("-" * 70)
    for section in edited_document.sections:
        print(f"   - {section.type.value}: {section.word_count} words")
        if section.type in [SectionType.AUTHORS, SectionType.AFFILIATION, SectionType.KEYWORDS]:
            print(f"     Content: {section.content[:60]}...")
    
    # Verify safety: no auto-generation occurred
    print("\n5. Safety Verification:")
    print("-" * 70)
    print(f"   Auto-generation allowed: {edited_document.metadata['auto_generation_allowed']}")
    print(f"   User edits applied: {edited_document.metadata['user_edits_applied']}")
    print(f"   Edits summary: {edited_document.metadata['edits_summary']}")
    
    # Format the document
    print("\n6. Formatting Document with IEEE Rules:")
    print("-" * 70)
    formatter = IEEEFormatter("rules.docx")
    formatted_document = formatter.format(edited_document)
    
    print("   Formatted sections:")
    for section in formatted_document.sections:
        heading = section.formatted_heading or section.original_heading or "(no heading)"
        print(f"   - {section.type.value}: {heading}")
    
    print("\n" + "=" * 70)
    print("Example Complete!")
    print("=" * 70)
    print("\nKey Takeaways:")
    print("1. User edits are applied BEFORE formatting")
    print("2. Missing sections are flagged but NOT auto-generated")
    print("3. Only user-provided information is added to the document")
    print("4. Original document remains unchanged (immutability)")
    print("5. All changes are tracked in metadata")


if __name__ == "__main__":
    main()
