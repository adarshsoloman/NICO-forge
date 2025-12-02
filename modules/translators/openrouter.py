"""OpenRouter translator adapter."""

import os
import aiohttp
import asyncio
from typing import List, Dict, Any

from modules.translators.base import BaseTranslator
from utils.exceptions import (
    APIKeyMissingError,
    AuthenticationError,
    RateLimitError,
    APIRequestError,
    TimeoutError,
    ParseError,
    EmptyResponseError
)
from utils.logger import get_logger

logger = get_logger(__name__)


class OpenRouterTranslator(BaseTranslator):
    """OpenRouter API translator adapter."""
    
    def __init__(
        self,
        api_key: str = None,
        base_url: str = "https://openrouter.ai/api/v1",
        model: str = "google/gemini-2.0-flash-thinking-exp:free",
        timeout: int = 30,
        custom_prompt: str = None,
        request_delay: float = 0
    ):
        """Initialize OpenRouter translator.
        
        Args:
            api_key: OpenRouter API key
            base_url: API base URL
            model: Model name
            timeout: Request timeout in seconds
            custom_prompt: Custom prompt template
            request_delay: Delay in seconds between requests (for rate limiting)
        """
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise APIKeyMissingError(
                "OpenRouter API key not provided. Set OPENROUTER_API_KEY env var."
            )
        
        self.base_url = base_url
        self.model = model
        self.timeout = timeout
        self.custom_prompt = custom_prompt
        self.request_delay = request_delay
    
    async def translate_batch(
        self,
        chunks: List[str],
        source_lang: str = "en",
        target_lang: str = "hi"
    ) -> List[str]:
        """Translate a batch of chunks using OpenRouter API.
        
        Args:
            chunks: List of text chunks
            source_lang: Source language
            target_lang: Target language
            
        Returns:
            List of translated chunks
        """
        if not chunks:
            return []
        
        # Create session
        async with aiohttp.ClientSession() as session:
            translations = []
            
            # Process one at a time with delay to respect rate limits
            for i, chunk in enumerate(chunks):
                if i > 0 and self.request_delay > 0:
                    await asyncio.sleep(self.request_delay)
                
                try:
                    result = await self._translate_single(session, chunk)
                    translations.append(result)
                except Exception as e:
                    logger.error(f"Translation failed for chunk {i}: {e}")
                    translations.append("")  # Empty translation on failure
            
            return translations
    
    async def _translate_single(
        self,
        session: aiohttp.ClientSession,
        text: str
    ) -> str:
        """Translate a single text chunk.
        
        Args:
            session: aiohttp session
            text: Text to translate
            
        Returns:
            Translated text
        """
        url = f"{self.base_url}/chat/completions"
        
        # Build prompt
        prompt = self._build_prompt(text, self.custom_prompt)
        
        # Prepare request
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
        
        # Make request with retry logic handled by caller
        try:
            async with session.post(
                url,
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                # Handle different status codes
                if response.status == 401:
                    raise AuthenticationError("Invalid API key")
                elif response.status == 429:
                    raise RateLimitError("Rate limit exceeded")
                elif response.status >= 500:
                    raise APIRequestError(f"Server error: {response.status}")
                elif response.status != 200:
                    error_text = await response.text()
                    raise APIRequestError(f"API error {response.status}: {error_text}")
                
                # Parse response
                data = await response.json()
                
                # Extract translation
                try:
                    translation = data["choices"][0]["message"]["content"].strip()
                    if not translation:
                        raise EmptyResponseError("Empty translation received")
                    return translation
                except (KeyError, IndexError) as e:
                    raise ParseError(f"Failed to parse response: {e}")
        
        except asyncio.TimeoutError:
            raise TimeoutError(f"Request timed out after {self.timeout}s")
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get model information.
        
        Returns:
            Model info dictionary
        """
        return {
            "adapter": "openrouter",
            "model": self.model,
            "base_url": self.base_url
        }
    
    def estimate_cost(self, word_count: int, token_multiplier: float = 1.5) -> float:
        """Estimate translation cost.
        
        Args:
            word_count: Number of words
            token_multiplier: Multiplier to convert words to tokens
            
        Returns:
            Estimated cost (rough estimate, actual may vary)
        """
        # Rough estimation - free tier models have no cost
        if ":free" in self.model:
            return 0.0
        
        # For paid models, rough estimate
        # This would need actual pricing data from OpenRouter
        estimated_tokens = int(word_count * token_multiplier)
        
        # Placeholder - update with actual pricing
        cost_per_1k_tokens = 0.001  # Example: $0.001 per 1K tokens
        estimated_cost_usd = (estimated_tokens / 1000) * cost_per_1k_tokens
        
        # Convert to INR (rough rate: 1 USD = 83 INR)
        estimated_cost_inr = estimated_cost_usd * 83
        
        return round(estimated_cost_inr, 2)
