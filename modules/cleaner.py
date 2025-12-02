"""Text cleaning module."""

import re
from pathlib import Path
from typing import Optional

from utils.exceptions import EmptyInputError, EncodingError
from utils.logger import get_logger
from utils.progress import ProgressBar
from utils.state_manager import StateManager

logger = get_logger(__name__)


class TextCleaner:
    """Clean and normalize extracted text."""
    
    def __init__(
        self,
        output_path: str,
        preview_path: Optional[str] = None,
        state_manager: Optional[StateManager] = None,
        remove_urls: bool = True,
        remove_emails: bool = True,
        remove_references: bool = True,
        normalize_whitespace: bool = True
    ):
        """Initialize text cleaner.
        
        Args:
            output_path: Path to save cleaned text
            preview_path: Path to save preview (optional)
            state_manager: State manager for resume capability
            remove_urls: Whether to remove URLs
            remove_emails: Whether to remove emails
            remove_references: Whether to remove reference markers
            normalize_whitespace: Whether to normalize whitespace
        """
        self.output_path = Path(output_path)
        self.preview_path = Path(preview_path) if preview_path else None
        self.state_manager = state_manager
        self.remove_urls = remove_urls
        self.remove_emails = remove_emails
        self.remove_references = remove_references
        self.normalize_whitespace = normalize_whitespace
        
        # Regex patterns
        self.url_pattern = re.compile(
            r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        )
        self.email_pattern = re.compile(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        )
        self.reference_pattern = re.compile(
            r'\[\d+\]|\(\d+\)|(?:fig\.|figure|table|ref\.)\s*\d+',
            re.IGNORECASE
        )
        
        # Create output directory
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
    
    def clean(self, input_path: str) -> dict:
        """Clean text from input file.
        
        Args:
            input_path: Path to raw text file
            
        Returns:
            Dictionary with cleaning statistics
        """
        input_path = Path(input_path)
        
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")
        
        # Read input text
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                raw_text = f.read()
        except UnicodeDecodeError as e:
            raise EncodingError(f"Failed to read input file: {e}")
        
        if not raw_text.strip():
            raise EmptyInputError("Input text is empty")
        
        logger.info(f"Cleaning text ({len(raw_text)} characters)")
        
        # Clean the text
        cleaned_text = self._clean_text(raw_text)
        
        # Write output
        with open(self.output_path, 'w', encoding='utf-8') as f:
            f.write(cleaned_text)
        
        # Write preview if requested
        if self.preview_path:
            preview_length = min(2000, len(cleaned_text))
            with open(self.preview_path, 'w', encoding='utf-8') as f:
                f.write(cleaned_text[:preview_length])
            logger.info(f"Preview saved to {self.preview_path}")
        
        # Update state
        if self.state_manager:
            self.state_manager.save_state(
                "cleaner",
                "completed",
                {
                    "input_length": len(raw_text),
                    "output_length": len(cleaned_text),
                    "reduction_pct": round((1 - len(cleaned_text) / len(raw_text)) * 100, 2)
                }
            )
        
        logger.info(f"✓ Cleaning complete: {len(cleaned_text)} characters ({len(raw_text)} → {len(cleaned_text)})")
        
        return {
            "input_length": len(raw_text),
            "output_length": len(cleaned_text),
            "output_path": str(self.output_path)
        }
    
    def _clean_text(self, text: str) -> str:
        """Apply cleaning operations to text.
        
        Args:
            text: Raw text
            
        Returns:
            Cleaned text
        """
        lines = text.split('\n')
        cleaned_lines = []
        
        # Process with progress bar
        with ProgressBar(
            total=len(lines),
            desc="Cleaning lines",
            unit="line"
        ) as pbar:
            for line in lines:
                cleaned_line = self._clean_line(line)
                if cleaned_line.strip():  # Skip empty lines
                    cleaned_lines.append(cleaned_line)
                pbar.update()
            
            pbar.close("Text cleaning complete")
        
        # Join lines
        cleaned_text = '\n'.join(cleaned_lines)
        
        # Final normalization
        if self.normalize_whitespace:
            # Replace multiple spaces with single space
            cleaned_text = re.sub(r' +', ' ', cleaned_text)
            # Replace multiple newlines with double newline
            cleaned_text = re.sub(r'\n{3,}', '\n\n', cleaned_text)
        
        return cleaned_text.strip()
    
    def _clean_line(self, line: str) -> str:
        """Clean a single line of text.
        
        Args:
            line: Input line
            
        Returns:
            Cleaned line
        """
        # Remove URLs
        if self.remove_urls:
            line = self.url_pattern.sub('', line)
        
        # Remove emails
        if self.remove_emails:
            line = self.email_pattern.sub('', line)
        
        # Remove references
        if self.remove_references:
            line = self.reference_pattern.sub('', line)
        
        # Remove unicode garbage (control characters, etc.)
        line = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]', '', line)
        
        # Normalize whitespace within line
        line = re.sub(r'\s+', ' ', line)
        
        return line.strip()
