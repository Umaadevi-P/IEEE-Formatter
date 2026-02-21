"""Unit tests for GrammarCorrector error handling"""
import pytest
from unittest.mock import Mock, patch
from app.corrector import GrammarCorrector
from app.models import Section, SectionType


class TestGrammarCorrectorErrorHandling:
    """Test error handling in GrammarCorrector"""
    
    def test_api_key_missing(self):
        """Test that missing API key disables grammar correction"""
        with patch.dict('os.environ', {}, clear=True):
            corrector = GrammarCorrector()
            
            # Should be disabled
            assert corrector.enabled is False
            
            # Should return original text
            original_text = "This is test text."
            result = corrector.correct_text(original_text)
            assert result == original_text
    
    def test_api_key_missing_with_sections(self):
        """Test that missing API key returns original sections unchanged"""
        with patch.dict('os.environ', {}, clear=True):
            corrector = GrammarCorrector()
            
            sections = [
                Section(id="1", type=SectionType.ABSTRACT, content="Test content 1"),
                Section(id="2", type=SectionType.INTRODUCTION, content="Test content 2")
            ]
            
            result = corrector.correct(sections)
            
            # Should return same sections
            assert len(result) == len(sections)
            assert result[0].content == sections[0].content
            assert result[1].content == sections[1].content
    
    def test_api_timeout(self):
        """Test graceful fallback when API times out"""
        corrector = GrammarCorrector(api_key="test_key")
        
        # Mock the model to raise a timeout exception
        with patch.object(corrector, 'model') as mock_model:
            mock_model.generate_content.side_effect = TimeoutError("API timeout")
            
            original_text = "This is test text."
            result = corrector.correct_text(original_text)
            
            # Should fallback to original text
            assert result == original_text
    
    def test_rate_limit_exceeded(self):
        """Test graceful fallback when rate limit is exceeded"""
        corrector = GrammarCorrector(api_key="test_key")
        
        # Mock the model to raise a rate limit exception
        with patch.object(corrector, 'model') as mock_model:
            mock_model.generate_content.side_effect = Exception("429 Rate limit exceeded")
            
            original_text = "This is test text."
            result = corrector.correct_text(original_text)
            
            # Should fallback to original text
            assert result == original_text
    
    def test_empty_response_from_api(self):
        """Test graceful fallback when API returns empty response"""
        corrector = GrammarCorrector(api_key="test_key")
        
        # Mock the model to return empty response
        with patch.object(corrector, 'model') as mock_model:
            mock_response = Mock()
            mock_response.text = None
            mock_model.generate_content.return_value = mock_response
            
            original_text = "This is test text."
            result = corrector.correct_text(original_text)
            
            # Should fallback to original text
            assert result == original_text
    
    def test_empty_text_input(self):
        """Test that empty text is returned unchanged"""
        corrector = GrammarCorrector(api_key="test_key")
        
        # Test with empty string
        assert corrector.correct_text("") == ""
        
        # Test with whitespace only
        assert corrector.correct_text("   ") == "   "
    
    def test_api_error_with_sections(self):
        """Test that API errors don't break section processing"""
        corrector = GrammarCorrector(api_key="test_key")
        
        # Mock the model to raise an exception
        with patch.object(corrector, 'model') as mock_model:
            mock_model.generate_content.side_effect = Exception("API error")
            
            sections = [
                Section(id="1", type=SectionType.ABSTRACT, content="Test content 1"),
                Section(id="2", type=SectionType.INTRODUCTION, content="Test content 2")
            ]
            
            result = corrector.correct(sections)
            
            # Should return sections with original content
            assert len(result) == len(sections)
            assert result[0].content == sections[0].content
            assert result[1].content == sections[1].content
    
    def test_invalid_api_key_initialization(self):
        """Test that invalid API key is handled during initialization"""
        # This will attempt to configure with invalid key
        # The corrector should still be created but may be disabled
        corrector = GrammarCorrector(api_key="invalid_key_12345")
        
        # Should have initialized (even if API calls will fail)
        assert corrector is not None
        
        # When trying to correct, should fallback gracefully
        original_text = "This is test text."
        result = corrector.correct_text(original_text)
        
        # Should return original text (fallback on error)
        assert result == original_text
