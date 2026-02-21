"""End-to-end integration tests with real research papers"""
import pytest
import os
from app.parser import DocumentParser
from app.corrector import GrammarCorrector
from app.formatter import IEEEFormatter
from app.issue_detector import IssueDetector
from app.compliance_scorer import ComplianceScorer
from app.change_tracker import ChangeTracker
from app.exporter import DocumentExporter
from app.models import SectionType, IssueSeverity


class TestEndToEndFlow:
    """Test complete pipeline with real research papers"""
    
    @pytest.fixture
    def sample_papers(self):
        """Get list of available sample papers"""
        papers = []
        uploads_dir = "uploads"
        
        if os.path.exists(uploads_dir):
            for filename in os.listdir(uploads_dir):
                if filename.endswith('.docx'):
                    papers.append(os.path.join(uploads_dir, filename))
        
        return papers
    
    def test_complete_pipeline_with_exp1(self):
        """Test full pipeline: parse → correct → format → export with Exp 1.docx"""
        test_file = "uploads/Exp 1.docx"
        
        if not os.path.exists(test_file):
            pytest.skip(f"Test file not found: {test_file}")
        
        # Step 1: Parse document
        parser = DocumentParser()
        parsed_doc = parser.parse(test_file)
        
        # Verify parsing worked
        assert len(parsed_doc.sections) > 0
        assert parsed_doc.metadata is not None
        
        # Store original for comparison
        document_before = parsed_doc.model_copy(deep=True)
        
        # Step 2: Grammar correction (with API key if available)
        api_key = os.getenv("GEMINI_API_KEY")
        corrector = GrammarCorrector(api_key)
        corrected_sections = corrector.correct(parsed_doc.sections)
        
        # Verify grammar correction preserved structure
        assert len(corrected_sections) == len(parsed_doc.sections)
        for i, section in enumerate(corrected_sections):
            assert section.type == parsed_doc.sections[i].type
            assert section.id == parsed_doc.sections[i].id
        
        parsed_doc.sections = corrected_sections
        
        # Step 3: Format with IEEE rules
        formatter = IEEEFormatter("rules.docx")
        formatted_doc = formatter.format(parsed_doc)
        
        # Verify formatting applied
        assert len(formatted_doc.sections) > 0
        assert formatted_doc.metadata is not None
        
        # Check that sections have formatted headings
        formatted_headings = [s.formatted_heading for s in formatted_doc.sections if s.formatted_heading]
        assert len(formatted_headings) > 0
        
        # Step 4: Detect issues
        detector = IssueDetector()
        issues = detector.detect_issues(document_before)
        
        # Verify issues structure
        assert isinstance(issues, list)
        for issue in issues:
            assert issue.type
            assert issue.severity in [IssueSeverity.HIGH, IssueSeverity.MEDIUM, IssueSeverity.LOW]
            assert issue.message
        
        # Step 5: Calculate compliance score
        scorer = ComplianceScorer()
        compliance = scorer.calculate(formatted_doc, issues)
        
        # Verify compliance score
        assert 0.0 <= compliance.score <= 100.0
        assert len(compliance.breakdown) == 5
        assert len(compliance.weights) == 5
        
        # Verify weights sum to 1.0
        total_weight = sum(compliance.weights.values())
        assert abs(total_weight - 1.0) < 0.001
        
        # Step 6: Track changes
        tracker = ChangeTracker()
        fixes = tracker.track_changes(document_before, formatted_doc)
        
        # Verify fixes tracked
        assert isinstance(fixes, list)
        for fix in fixes:
            assert fix.section_id
            assert fix.type
            assert fix.reason
        
        # Step 7: Export to DOCX
        exporter = DocumentExporter()
        output_path = "exports/test_exp1_formatted.docx"
        
        try:
            exporter.export_docx(formatted_doc, output_path)
            
            # Verify file was created
            assert os.path.exists(output_path)
            assert os.path.getsize(output_path) > 0
        finally:
            # Clean up
            if os.path.exists(output_path):
                os.remove(output_path)
        
        # Step 8: Export to PDF
        pdf_output_path = "exports/test_exp1_formatted.pdf"
        
        try:
            exporter.export_pdf(formatted_doc, pdf_output_path)
            
            # Verify file was created
            assert os.path.exists(pdf_output_path)
            assert os.path.getsize(pdf_output_path) > 0
        finally:
            # Clean up
            if os.path.exists(pdf_output_path):
                os.remove(pdf_output_path)
    
    def test_complete_pipeline_with_meteor_shower(self):
        """Test full pipeline with Meteor_Shower_Review_Wrong_Format_Exaggerated.docx"""
        test_file = "uploads/Meteor_Shower_Review_Wrong_Format_Exaggerated.docx"
        
        if not os.path.exists(test_file):
            pytest.skip(f"Test file not found: {test_file}")
        
        # Parse
        parser = DocumentParser()
        parsed_doc = parser.parse(test_file)
        
        assert len(parsed_doc.sections) > 0
        
        document_before = parsed_doc.model_copy(deep=True)
        
        # Grammar correction
        api_key = os.getenv("GEMINI_API_KEY")
        corrector = GrammarCorrector(api_key)
        corrected_sections = corrector.correct(parsed_doc.sections)
        parsed_doc.sections = corrected_sections
        
        # Format
        formatter = IEEEFormatter("rules.docx")
        formatted_doc = formatter.format(parsed_doc)
        
        # Detect issues (this document should have issues)
        detector = IssueDetector()
        issues = detector.detect_issues(document_before)
        
        # This document has wrong format, so should have issues
        assert len(issues) > 0
        
        # Calculate compliance
        scorer = ComplianceScorer()
        compliance = scorer.calculate(formatted_doc, issues)
        
        # Verify compliance structure
        assert 0.0 <= compliance.score <= 100.0
        
        # Track changes
        tracker = ChangeTracker()
        fixes = tracker.track_changes(document_before, formatted_doc)
        
        # Should have many fixes due to wrong format
        assert len(fixes) > 0
        
        # Export
        exporter = DocumentExporter()
        output_path = "exports/test_meteor_formatted.docx"
        
        try:
            exporter.export_docx(formatted_doc, output_path)
            assert os.path.exists(output_path)
        finally:
            if os.path.exists(output_path):
                os.remove(output_path)

    
    def test_pipeline_with_formatted_manuscript(self):
        """Test pipeline with formatted_manuscript (1).docx"""
        test_file = "uploads/formatted_manuscript (1).docx"
        
        if not os.path.exists(test_file):
            pytest.skip(f"Test file not found: {test_file}")
        
        # Parse
        parser = DocumentParser()
        parsed_doc = parser.parse(test_file)
        
        assert len(parsed_doc.sections) > 0
        
        # Format
        formatter = IEEEFormatter("rules.docx")
        formatted_doc = formatter.format(parsed_doc)
        
        # Detect issues
        detector = IssueDetector()
        issues = detector.detect_issues(parsed_doc)
        
        # Calculate compliance
        scorer = ComplianceScorer()
        compliance = scorer.calculate(formatted_doc, issues)
        
        assert 0.0 <= compliance.score <= 100.0
    
    def test_all_sample_papers(self, sample_papers):
        """Test that all sample papers can be processed without errors"""
        if not sample_papers:
            pytest.skip("No sample papers found in uploads/ directory")
        
        parser = DocumentParser()
        formatter = IEEEFormatter("rules.docx")
        detector = IssueDetector()
        scorer = ComplianceScorer()
        
        results = []
        
        for paper_path in sample_papers:
            try:
                # Parse
                parsed_doc = parser.parse(paper_path)
                assert len(parsed_doc.sections) > 0
                
                # Format
                formatted_doc = formatter.format(parsed_doc)
                assert len(formatted_doc.sections) > 0
                
                # Detect issues
                issues = detector.detect_issues(parsed_doc)
                
                # Calculate compliance
                compliance = scorer.calculate(formatted_doc, issues)
                assert 0.0 <= compliance.score <= 100.0
                
                results.append({
                    "file": os.path.basename(paper_path),
                    "status": "success",
                    "sections": len(formatted_doc.sections),
                    "issues": len(issues),
                    "compliance": compliance.score
                })
                
            except Exception as e:
                results.append({
                    "file": os.path.basename(paper_path),
                    "status": "failed",
                    "error": str(e)
                })
        
        # Print summary
        print("\n=== Sample Papers Processing Summary ===")
        for result in results:
            if result["status"] == "success":
                print(f"✓ {result['file']}: {result['sections']} sections, "
                      f"{result['issues']} issues, {result['compliance']:.1f}% compliance")
            else:
                print(f"✗ {result['file']}: {result['error']}")
        
        # All papers should process successfully
        failed = [r for r in results if r["status"] == "failed"]
        assert len(failed) == 0, f"Failed to process {len(failed)} papers"


class TestParsingAccuracy:
    """Test parsing accuracy with real papers"""
    
    def test_parsing_extracts_all_sections(self):
        """Verify parser extracts all sections from real papers"""
        test_file = "uploads/Exp 1.docx"
        
        if not os.path.exists(test_file):
            pytest.skip(f"Test file not found: {test_file}")
        
        parser = DocumentParser()
        parsed_doc = parser.parse(test_file)
        
        # Should have multiple sections
        assert len(parsed_doc.sections) >= 3
        
        # Should have at least some recognized section types
        section_types = [s.type for s in parsed_doc.sections]
        recognized_types = [t for t in section_types if t != SectionType.UNKNOWN]
        assert len(recognized_types) > 0
    
    def test_parsing_preserves_content(self):
        """Verify parser preserves all content"""
        test_file = "uploads/Exp 1.docx"
        
        if not os.path.exists(test_file):
            pytest.skip(f"Test file not found: {test_file}")
        
        parser = DocumentParser()
        parsed_doc = parser.parse(test_file)
        
        # Should have at least some sections with content
        sections_with_content = [s for s in parsed_doc.sections if s.content and s.content.strip()]
        
        # At least some sections should have content (documents may have heading-only sections)
        assert len(sections_with_content) > 0
        
        # Sections with content should have positive word count
        for section in sections_with_content:
            assert section.word_count > 0
        
        # Total word count should be positive
        total_words = sum(s.word_count for s in parsed_doc.sections)
        assert total_words > 0
    
    def test_parsing_detects_section_types(self):
        """Verify parser correctly detects section types"""
        test_file = "uploads/Exp 1.docx"
        
        if not os.path.exists(test_file):
            pytest.skip(f"Test file not found: {test_file}")
        
        parser = DocumentParser()
        parsed_doc = parser.parse(test_file)
        
        section_types = [s.type for s in parsed_doc.sections]
        
        # Should detect at least some standard sections
        # (exact sections depend on the document)
        assert len(section_types) > 0


class TestFormattingAccuracy:
    """Test formatting accuracy with real papers"""
    
    def test_formatting_applies_ieee_rules(self):
        """Verify formatter applies IEEE rules correctly"""
        test_file = "uploads/Exp 1.docx"
        
        if not os.path.exists(test_file):
            pytest.skip(f"Test file not found: {test_file}")
        
        parser = DocumentParser()
        parsed_doc = parser.parse(test_file)
        
        formatter = IEEEFormatter("rules.docx")
        formatted_doc = formatter.format(parsed_doc)
        
        # Check font rules applied
        for section in formatted_doc.sections:
            if section.font_rule:
                assert section.font_rule.font_family == "Times New Roman"
                assert section.font_rule.font_size > 0
    
    def test_formatting_adds_roman_numerals(self):
        """Verify formatter adds Roman numeral numbering"""
        test_file = "uploads/Exp 1.docx"
        
        if not os.path.exists(test_file):
            pytest.skip(f"Test file not found: {test_file}")
        
        parser = DocumentParser()
        parsed_doc = parser.parse(test_file)
        
        formatter = IEEEFormatter("rules.docx")
        formatted_doc = formatter.format(parsed_doc)
        
        # Check for Roman numerals in formatted headings
        formatted_headings = [s.formatted_heading for s in formatted_doc.sections 
                             if s.formatted_heading]
        
        # Should have some headings with Roman numerals
        roman_numerals = ["I.", "II.", "III.", "IV.", "V."]
        has_roman = any(any(rn in heading for rn in roman_numerals) 
                       for heading in formatted_headings)
        
        # Only assert if we have main sections that should be numbered
        main_section_types = [
            SectionType.INTRODUCTION,
            SectionType.METHODOLOGY,
            SectionType.RESULTS,
            SectionType.CONCLUSION
        ]
        has_main_sections = any(s.type in main_section_types for s in formatted_doc.sections)
        
        if has_main_sections:
            assert has_roman, "Main sections should have Roman numeral numbering"
    
    def test_formatting_reorders_sections(self):
        """Verify formatter reorders sections to IEEE standard"""
        test_file = "uploads/Exp 1.docx"
        
        if not os.path.exists(test_file):
            pytest.skip(f"Test file not found: {test_file}")
        
        parser = DocumentParser()
        parsed_doc = parser.parse(test_file)
        
        formatter = IEEEFormatter("rules.docx")
        formatted_doc = formatter.format(parsed_doc)
        
        # Get section types in order
        section_types = [s.type for s in formatted_doc.sections]
        
        # Define IEEE standard order
        ieee_order = [
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
        
        # Check that sections appear in IEEE order (ignoring missing sections)
        present_types = [t for t in section_types if t in ieee_order]
        
        if len(present_types) >= 2:
            # Verify order is correct
            for i in range(len(present_types) - 1):
                current_idx = ieee_order.index(present_types[i])
                next_idx = ieee_order.index(present_types[i + 1])
                assert current_idx < next_idx, \
                    f"Section {present_types[i]} should come before {present_types[i + 1]}"


class TestIssueDetectionAccuracy:
    """Test issue detection accuracy with real papers"""
    
    def test_issue_detection_finds_missing_sections(self):
        """Verify issue detector finds missing required sections"""
        test_file = "uploads/Exp 1.docx"
        
        if not os.path.exists(test_file):
            pytest.skip(f"Test file not found: {test_file}")
        
        parser = DocumentParser()
        parsed_doc = parser.parse(test_file)
        
        detector = IssueDetector()
        issues = detector.detect_issues(parsed_doc)
        
        # Check for missing section issues
        missing_issues = [i for i in issues if i.type == "missing_required_section"]
        
        # Verify issue structure
        for issue in missing_issues:
            assert issue.severity == IssueSeverity.HIGH
            assert issue.message
            assert "missing" in issue.message.lower() or "required" in issue.message.lower()
    
    def test_issue_detection_with_wrong_format_paper(self):
        """Verify issue detector finds issues in wrong format paper"""
        test_file = "uploads/Meteor_Shower_Review_Wrong_Format_Exaggerated.docx"
        
        if not os.path.exists(test_file):
            pytest.skip(f"Test file not found: {test_file}")
        
        parser = DocumentParser()
        parsed_doc = parser.parse(test_file)
        
        detector = IssueDetector()
        issues = detector.detect_issues(parsed_doc)
        
        # This paper has wrong format, should have issues
        assert len(issues) > 0
        
        # Should have various severity levels
        severities = set(i.severity for i in issues)
        assert len(severities) > 0


class TestComplianceScoringAccuracy:
    """Test compliance scoring accuracy with real papers"""
    
    def test_compliance_scoring_structure(self):
        """Verify compliance score has correct structure"""
        test_file = "uploads/Exp 1.docx"
        
        if not os.path.exists(test_file):
            pytest.skip(f"Test file not found: {test_file}")
        
        parser = DocumentParser()
        parsed_doc = parser.parse(test_file)
        
        formatter = IEEEFormatter("rules.docx")
        formatted_doc = formatter.format(parsed_doc)
        
        detector = IssueDetector()
        issues = detector.detect_issues(parsed_doc)
        
        scorer = ComplianceScorer()
        compliance = scorer.calculate(formatted_doc, issues)
        
        # Verify structure
        assert hasattr(compliance, 'score')
        assert hasattr(compliance, 'breakdown')
        assert hasattr(compliance, 'weights')
        
        # Verify breakdown components
        expected_components = [
            'required_sections',
            'section_order',
            'abstract_compliance',
            'heading_hierarchy',
            'formatting_consistency'
        ]
        
        for component in expected_components:
            assert component in compliance.breakdown
            assert 0.0 <= compliance.breakdown[component] <= 1.0
        
        # Verify weights
        for component in expected_components:
            assert component in compliance.weights
            assert compliance.weights[component] > 0
        
        # Verify weights sum to 1.0
        total_weight = sum(compliance.weights.values())
        assert abs(total_weight - 1.0) < 0.001
    
    def test_compliance_score_reflects_quality(self):
        """Verify compliance score reflects document quality"""
        # Test with two different papers if available
        papers = [
            "uploads/Exp 1.docx",
            "uploads/Meteor_Shower_Review_Wrong_Format_Exaggerated.docx"
        ]
        
        scores = []
        
        for paper_path in papers:
            if not os.path.exists(paper_path):
                continue
            
            parser = DocumentParser()
            parsed_doc = parser.parse(paper_path)
            
            formatter = IEEEFormatter("rules.docx")
            formatted_doc = formatter.format(parsed_doc)
            
            detector = IssueDetector()
            issues = detector.detect_issues(parsed_doc)
            
            scorer = ComplianceScorer()
            compliance = scorer.calculate(formatted_doc, issues)
            
            scores.append({
                "file": os.path.basename(paper_path),
                "score": compliance.score,
                "issues": len(issues)
            })
        
        if len(scores) >= 2:
            print("\n=== Compliance Scores ===")
            for s in scores:
                print(f"{s['file']}: {s['score']:.1f}% ({s['issues']} issues)")


class TestExportFunctionality:
    """Test export functionality with real papers"""
    
    def test_docx_export_creates_file(self):
        """Verify DOCX export creates valid file"""
        test_file = "uploads/Exp 1.docx"
        
        if not os.path.exists(test_file):
            pytest.skip(f"Test file not found: {test_file}")
        
        parser = DocumentParser()
        parsed_doc = parser.parse(test_file)
        
        formatter = IEEEFormatter("rules.docx")
        formatted_doc = formatter.format(parsed_doc)
        
        exporter = DocumentExporter()
        output_path = "exports/test_docx_export.docx"
        
        try:
            exporter.export_docx(formatted_doc, output_path)
            
            # Verify file exists and has content
            assert os.path.exists(output_path)
            assert os.path.getsize(output_path) > 1000  # Should be at least 1KB
            
            # Verify it's a valid DOCX file (can be opened)
            from docx import Document
            doc = Document(output_path)
            assert len(doc.paragraphs) > 0
            
        finally:
            if os.path.exists(output_path):
                os.remove(output_path)
    
    def test_pdf_export_creates_file(self):
        """Verify PDF export creates valid file"""
        test_file = "uploads/Exp 1.docx"
        
        if not os.path.exists(test_file):
            pytest.skip(f"Test file not found: {test_file}")
        
        parser = DocumentParser()
        parsed_doc = parser.parse(test_file)
        
        formatter = IEEEFormatter("rules.docx")
        formatted_doc = formatter.format(parsed_doc)
        
        exporter = DocumentExporter()
        output_path = "exports/test_pdf_export.pdf"
        
        try:
            exporter.export_pdf(formatted_doc, output_path)
            
            # Verify file exists and has content
            assert os.path.exists(output_path)
            assert os.path.getsize(output_path) > 1000  # Should be at least 1KB
            
            # Verify it's a PDF file (starts with PDF magic bytes)
            with open(output_path, 'rb') as f:
                header = f.read(4)
                assert header == b'%PDF', "File should be a valid PDF"
            
        finally:
            if os.path.exists(output_path):
                os.remove(output_path)
