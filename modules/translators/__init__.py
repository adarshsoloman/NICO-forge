"""Translator adapters package."""

from modules.translators.base import BaseTranslator
from modules.translators.openrouter import OpenRouterTranslator

__all__ = [
    'BaseTranslator',
    'OpenRouterTranslator',
]
