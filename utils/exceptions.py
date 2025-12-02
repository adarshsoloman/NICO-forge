"""Custom exceptions for NICO-Forge pipeline."""


# ============================================================================
# EXTRACTION MODULE EXCEPTIONS
# ============================================================================

class ExtractionError(Exception):
    """Base exception for extraction module."""
    pass


class UnsupportedFileTypeError(ExtractionError):
    """Raised when file format is not supported."""
    pass


class PDFReadError(ExtractionError):
    """Raised when PDF cannot be read or is corrupted."""
    pass


class EncodingError(ExtractionError):
    """Raised when text encoding issues occur."""
    pass


# ============================================================================
# CLEANER MODULE EXCEPTIONS
# ============================================================================

class CleanerError(Exception):
    """Base exception for cleaner module."""
    pass


class EmptyInputError(CleanerError):
    """Raised when input text is empty."""
    pass


class RegexError(CleanerError):
    """Raised when regex processing fails."""
    pass


# ============================================================================
# CHUNKER MODULE EXCEPTIONS
# ============================================================================

class ChunkerError(Exception):
    """Base exception for chunker module."""
    pass


class EmptyTextError(ChunkerError):
    """Raised when text to chunk is empty."""
    pass


class InvalidChunkSizeError(ChunkerError):
    """Raised when chunk size is invalid."""
    pass


class TokenizationError(ChunkerError):
    """Raised when text tokenization fails."""
    pass


# ============================================================================
# TRANSLATION PIPELINE EXCEPTIONS
# ============================================================================

class TranslationError(Exception):
    """Base exception for translation pipeline."""
    pass


class APIKeyMissingError(TranslationError):
    """Raised when API key is not provided."""
    pass


class AuthenticationError(TranslationError):
    """Raised when API authentication fails."""
    pass


class RateLimitError(TranslationError):
    """Raised when API rate limit is exceeded (429)."""
    pass


class APIRequestError(TranslationError):
    """Raised when API request fails (5xx errors)."""
    pass


class TimeoutError(TranslationError):
    """Raised when API request times out."""
    pass


class ParseError(TranslationError):
    """Raised when API response cannot be parsed."""
    pass


class EmptyResponseError(TranslationError):
    """Raised when API returns empty response."""
    pass


class TranslationQualityError(TranslationError):
    """Raised when translation fails QA checks."""
    pass


class QuotaExceededError(TranslationError):
    """Raised when API quota is exceeded."""
    pass


# ============================================================================
# CONFIGURATION EXCEPTIONS
# ============================================================================

class ConfigError(Exception):
    """Base exception for configuration issues."""
    pass


class ConfigFileNotFoundError(ConfigError):
    """Raised when config file is missing."""
    pass


class InvalidConfigError(ConfigError):
    """Raised when config file is malformed."""
    pass


# ============================================================================
# COST EXCEPTIONS
# ============================================================================

class CostError(Exception):
    """Base exception for cost-related issues."""
    pass


class CostThresholdExceededError(CostError):
    """Raised when estimated cost exceeds threshold."""
    pass
