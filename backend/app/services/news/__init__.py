"""
News Service - Gemini API client with Google Search Grounding.
"""

from .gemini_client import GeminiNewsClient
from .cache import NewsCache
from .validator import GroundingValidator

__all__ = ["GeminiNewsClient", "NewsCache", "GroundingValidator"]
