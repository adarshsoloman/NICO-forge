"""Base translator interface."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any


class BaseTranslator(ABC):
    """Abstract base class for translation adapters."""
    
    @abstractmethod
    async def translate_batch(
        self,
        chunks: List[str],
        source_lang: str = "en",
        target_lang: str = "hi"
    ) -> List[str]:
        """Translate a batch of text chunks.
        
        Args:
            chunks: List of text chunks to translate
            source_lang: Source language code
            target_lang: Target language code
            
        Returns:
            List of translated chunks
        """
        pass
    
    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the translation model.
        
        Returns:
            Dictionary with model information
        """
        pass
    
    @abstractmethod
    def estimate_cost(self, word_count: int) -> float:
        """Estimate cost for translating given number of words.
        
        Args:
            word_count: Number of words to translate
            
        Returns:
            Estimated cost in configured currency
        """
        pass
    
    def _build_prompt(self, text: str, custom_prompt: str = None) -> str:
        """Build translation prompt.
        
        Args:
            text: Text to translate
            custom_prompt: Custom prompt template (optional)
            
        Returns:
            Formatted prompt
        """
        if custom_prompt:
            return custom_prompt.format(text=text)
        
        # Default prompt
        return f"""Translate the following English text to Hindi.
Maintain the tone, style, and meaning accurately.
Output ONLY the Hindi translation, no explanations.

English text:
{text}

Hindi translation:"""
