"""Example demonstrating citation conversion to IEEE format"""
from app.citation_converter import CitationConverter
from app.models import Section, SectionType
import uuid


def main():
    """Demonstrate citation conversion functionality"""
    
    print("=" * 70)
    print("IEEE Citation Conversion Example")
    print("=" * 70)
    print()
    
    # Create a document with various citation formats
    sections = [
        Section(
            id=str(uuid.uuid4()),
            type=SectionType.INTRODUCTION,
            content="""
            Previous research has shown significant advances in AI (Smith, 2020).
            Machine learning techniques (Jones et al., 2021) have been particularly
            effective. The foundational work by Brown (2019) established the baseline.
            """,
            word_count=30
        ),
        Section(
            id=str(uuid.uuid4()),
            type=SectionType.METHODOLOGY,
            content="""
            We followed the approach described in (Chen, 2022) and extended it
            using methods from (Davis et al., 2020).
            """,
            word_count=20
        ),
        Section(
            id=str(uuid.uuid4()),
            type=SectionType.REFERENCES,
            content="""
Smith, J. (2020). Advances in Artificial Intelligence. Journal of AI Research, 15(3), 234-250.

Jones, A., Williams, B., and Taylor, C. (2021). Machine Learning Applications. IEEE Transactions on Neural Networks, 32(4), 567-589.

Brown, R. (2019). Foundations of Deep Learning. Nature Machine Intelligence, 1(2), 89-102.

Chen, L. (2022). Novel Approaches to Computer Vision. Computer Vision and Pattern Recognition, 45(1), 123-145.

Davis, M., Wilson, K., and Anderson, P. (2020). Advanced Neural Architectures. Neural Information Processing Systems, 33, 1234-1250.
            """,
            word_count=100
        )
    ]
    
    print("ORIGINAL DOCUMENT")
    print("-" * 70)
    print()
    
    for section in sections:
        print(f"[{section.type.value}]")
        print(section.content.strip())
        print()
    
    # Convert citations
    converter = CitationConverter()
    converted_sections = converter.convert_references(sections)
    
    print("\n" + "=" * 70)
    print("AFTER IEEE CITATION CONVERSION")
    print("=" * 70)
    print()
    
    for section in converted_sections:
        print(f"[{section.type.value}]")
        print(section.content.strip())
        print()
    
    print("-" * 70)
    print(f"Total citations detected: {converter.get_citation_count()}")
    print("-" * 70)
    print()
    
    print("Key Features Demonstrated:")
    print("1. ✓ References section formatted with IEEE numbering [1], [2], etc.")
    print("2. ✓ In-text citations converted to numbered format")
    print("3. ✓ Reference order preserved from original document")
    print("4. ✓ Multiple citation formats handled (Author, Year) and (Author et al., Year)")
    print()


if __name__ == "__main__":
    main()
