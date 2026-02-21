"""Grammar correction using Gemini API"""
import os
import logging
from typing import List, Optional
import google.generativeai as genai

from app.models import Section

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GrammarCorrector:
    """
    Grammar correction service using Gemini API
    
    This class sends text content to Gemini API for grammar and spelling
    correction only. It preserves document structure and content.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize GrammarCorrector with Gemini API key
        
        Args:
            api_key: Gemini API key. If None, reads from GEMINI_API_KEY env variable
        
        Raises:
            ValueError: If API key is not provided and not found in environment
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        
        if not self.api_key:
            logger.warning("GEMINI_API_KEY not found. Grammar correction will be disabled.")
            self.enabled = False
        else:
            try:
                genai.configure(api_key=self.api_key)
                # Use the latest Gemini Flash model (fastest and most efficient)
                self.model = genai.GenerativeModel('gemini-2.5-flash')
                self.enabled = True
                logger.info("GrammarCorrector initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini API: {e}")
                self.enabled = False
    
    def build_prompt(self, text: str) -> str:
        """
        Build prompt that instructs LLM to ONLY fix grammar/spelling
        
        Args:
            text: Original text content to correct
            
        Returns:
            Formatted prompt with strict instructions
        """
        prompt = f"""You are a grammar correction assistant. Your ONLY job is to fix grammar and spelling errors.

STRICT RULES:
1. Do NOT remove any content
2. Do NOT change the structure or order
3. Do NOT summarize or rewrite
4. Do NOT add new content
5. ONLY fix grammar, spelling, and punctuation errors

Original text:
{text}

Return ONLY the corrected text with no explanations."""
        
        return prompt
    
    def correct_text(self, text: str) -> str:
        """
        Send text to Gemini API for grammar correction
        
        Args:
            text: Text content to correct
            
        Returns:
            Grammar-corrected text, or original text if correction fails
        """
        if not self.enabled:
            logger.debug("Grammar correction disabled, returning original text")
            return text
        
        if not text or not text.strip():
            return text
        
        try:
            prompt = self.build_prompt(text)
            response = self.model.generate_content(prompt)
            
            if response and response.text:
                corrected_text = response.text.strip()
                logger.debug(f"Successfully corrected text (length: {len(text)} -> {len(corrected_text)})")
                return corrected_text
            else:
                logger.warning("Empty response from Gemini API, returning original text")
                return text
                
        except Exception as e:
            logger.error(f"Error during grammar correction: {e}")
            logger.info("Falling back to original text")
            return text
    
    def correct(self, sections: List[Section]) -> List[Section]:
        """
        Correct grammar in all sections of a document
        
        Args:
            sections: List of document sections to correct
            
        Returns:
            List of sections with grammar-corrected content
        """
        if not self.enabled:
            logger.info("Grammar correction disabled, returning original sections")
            return sections
        
        corrected_sections = []
        
        for section in sections:
            # Create a copy of the section
            corrected_section = section.model_copy(deep=True)
            
            # Correct the content
            if section.content:
                corrected_section.content = self.correct_text(section.content)
            
            # Correct the original heading if present
            if section.original_heading:
                corrected_section.original_heading = self.correct_text(section.original_heading)
            
            corrected_sections.append(corrected_section)
        
        logger.info(f"Corrected {len(corrected_sections)} sections")
        return corrected_sections
