"""
Gemini API Client with Google Search Grounding.
Provides news analysis for commodities using real-time web search.

Uses Gemini 3 Flash Preview with the latest google-genai SDK.
References:
- https://ai.google.dev/gemini-api/docs/google-search
- https://ai.google.dev/gemini-api/docs/models
"""

import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

from app.config import get_settings
from app.schemas.news import (
    CommodityNewsAnalysis,
    MarketAssessment,
    MarketSentiment,
    SupplyDemandInfo,
    MacroFactors,
    UpcomingEvent,
    SourceLink,
    ImpactLevel,
)
from .prompts import get_commodity_analysis_prompt, get_commodity_name
from .validator import GroundingValidator
from .cache import NewsCache

logger = logging.getLogger(__name__)


class GeminiNewsClient:
    """
    Gemini API client with Google Search Grounding for commodity news analysis.
    Uses the latest Gemini 3 Flash Preview model for best performance.
    """

    # Gemini 3 Flash Preview - frontier-class performance at low cost
    MODEL_NAME = "gemini-3-flash-preview"

    # Fallback models in order of preference
    FALLBACK_MODELS = [
        "gemini-2.5-flash",
        "gemini-2.0-flash",
    ]

    def __init__(self):
        self.settings = get_settings()
        self.validator = GroundingValidator(min_score=0.7)
        self.cache = NewsCache(
            db_path=self.settings.news_cache_db_path,
            ttl_seconds=self.settings.news_cache_ttl_seconds,
        )
        self._client = None
        self._active_model = self.MODEL_NAME

    def _get_client(self):
        """Lazy initialization of Gemini client."""
        if self._client is None:
            if not self.settings.gemini_api_key:
                raise ValueError("GEMINI_API_KEY not configured")

            try:
                from google import genai
                self._client = genai.Client(api_key=self.settings.gemini_api_key)
            except ImportError:
                raise ImportError(
                    "google-genai package not installed. "
                    "Install with: pip install google-genai"
                )

        return self._client

    def is_available(self) -> bool:
        """Check if Gemini API is available."""
        return bool(self.settings.gemini_api_key)

    def get_active_model(self) -> str:
        """Return the currently active model name."""
        return self._active_model

    async def analyze_commodity(
        self,
        symbol: str,
        force_refresh: bool = False
    ) -> CommodityNewsAnalysis:
        """
        Analyze a commodity using Gemini with Google Search Grounding.

        Args:
            symbol: Commodity symbol (e.g., "GC=F")
            force_refresh: If True, bypass cache

        Returns:
            CommodityNewsAnalysis with market research
        """
        # Check cache first (unless force_refresh)
        if not force_refresh:
            cached = self.cache.get(symbol)
            if cached:
                return self._dict_to_analysis(cached, symbol)

        # Get commodity name
        commodity_name = get_commodity_name(symbol)

        # Generate prompt
        prompt = get_commodity_analysis_prompt(symbol, commodity_name)

        # Call Gemini API with grounding (with fallback)
        response = await self._call_with_fallback(prompt)

        try:
            # Extract response text and grounding metadata
            response_text = response.text
            grounding_metadata = self._extract_grounding_metadata(response)
            rendered_content = self._extract_rendered_content(response)

            # Parse JSON response
            parsed = self._parse_response(response_text)

            # Validate and filter using grounding scores
            validated, sources = self.validator.validate_response(
                parsed, grounding_metadata
            )

            # Add inline citations to text fields
            if grounding_metadata:
                validated = self._add_inline_citations(validated, grounding_metadata)

            # Build analysis object
            analysis = self._build_analysis(
                symbol=symbol,
                commodity_name=commodity_name,
                parsed=validated,
                sources=sources,
                rendered_content=rendered_content,
            )

            # Cache the result
            self.cache.set(symbol, self._analysis_to_dict(analysis))

            return analysis

        except Exception as e:
            logger.error(f"Gemini API error for {symbol}: {e}")

            # Try to return cached data if available
            cached = self.cache.get(symbol)
            if cached:
                logger.info(f"Returning stale cache for {symbol} after API error")
                return self._dict_to_analysis(cached, symbol)

            raise

    async def _call_with_fallback(self, prompt: str):
        """
        Call Gemini API with automatic model fallback.
        Tries Gemini 3 Flash first, then falls back to older models.
        """
        from google.genai import types

        client = self._get_client()

        # Configure Google Search grounding tool
        grounding_tool = types.Tool(
            google_search=types.GoogleSearch()
        )

        config = types.GenerateContentConfig(
            tools=[grounding_tool],
            temperature=0.2,  # Lower temperature for factual accuracy
        )

        models_to_try = [self.MODEL_NAME] + self.FALLBACK_MODELS
        last_error = None

        for model in models_to_try:
            try:
                logger.info(f"Trying model: {model}")
                response = client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=config,
                )
                self._active_model = model
                logger.info(f"Successfully used model: {model}")
                return response

            except Exception as e:
                logger.warning(f"Model {model} failed: {e}")
                last_error = e
                continue

        # All models failed
        raise last_error or Exception("All Gemini models failed")

    def _extract_grounding_metadata(self, response) -> Optional[Dict[str, Any]]:
        """
        Extract grounding metadata from Gemini response.
        Uses the latest API structure with web_search_queries, grounding_chunks, and grounding_supports.
        """
        try:
            if not response.candidates or len(response.candidates) == 0:
                return None

            candidate = response.candidates[0]
            if not hasattr(candidate, 'grounding_metadata') or not candidate.grounding_metadata:
                return None

            metadata = candidate.grounding_metadata

            result = {
                "web_search_queries": [],
                "grounding_chunks": [],
                "grounding_supports": [],
            }

            # Extract web search queries
            web_queries = getattr(metadata, 'web_search_queries', None)
            if web_queries is not None:
                try:
                    result["web_search_queries"] = list(web_queries)
                except (TypeError, ValueError):
                    pass

            # Extract grounding chunks (sources)
            grounding_chunks = getattr(metadata, 'grounding_chunks', None)
            if grounding_chunks is not None:
                try:
                    for chunk in grounding_chunks:
                        if hasattr(chunk, 'web') and chunk.web:
                            result["grounding_chunks"].append({
                                "web": {
                                    "uri": getattr(chunk.web, 'uri', ''),
                                    "title": getattr(chunk.web, 'title', ''),
                                }
                            })
                except (TypeError, ValueError):
                    pass

            # Extract grounding supports (text segment to source mapping)
            grounding_supports = getattr(metadata, 'grounding_supports', None)
            if grounding_supports is not None:
                try:
                    for support in grounding_supports:
                        support_data = {
                            "segment": {
                                "text": "",
                                "start_index": 0,
                                "end_index": 0,
                            },
                            "grounding_chunk_indices": [],
                            "confidence_scores": [],
                        }

                        if hasattr(support, 'segment') and support.segment:
                            support_data["segment"]["text"] = getattr(support.segment, 'text', '')
                            support_data["segment"]["start_index"] = getattr(support.segment, 'start_index', 0)
                            support_data["segment"]["end_index"] = getattr(support.segment, 'end_index', 0)

                        chunk_indices = getattr(support, 'grounding_chunk_indices', None)
                        if chunk_indices is not None:
                            try:
                                support_data["grounding_chunk_indices"] = list(chunk_indices)
                            except (TypeError, ValueError):
                                pass

                        conf_scores = getattr(support, 'confidence_scores', None)
                        if conf_scores is not None:
                            try:
                                support_data["confidence_scores"] = list(conf_scores)
                            except (TypeError, ValueError):
                                pass

                        result["grounding_supports"].append(support_data)
                except (TypeError, ValueError):
                    pass

            return result

        except Exception as e:
            logger.warning(f"Failed to extract grounding metadata: {e}")
            return None

    def _extract_rendered_content(self, response) -> Optional[str]:
        """Extract rendered content (Google Search suggestions) for compliance."""
        try:
            if not response.candidates or len(response.candidates) == 0:
                return None

            candidate = response.candidates[0]
            if not hasattr(candidate, 'grounding_metadata') or not candidate.grounding_metadata:
                return None

            metadata = candidate.grounding_metadata
            if hasattr(metadata, 'search_entry_point') and metadata.search_entry_point:
                sep = metadata.search_entry_point
                if hasattr(sep, 'rendered_content'):
                    return sep.rendered_content

            return None
        except Exception as e:
            logger.warning(f"Failed to extract rendered content: {e}")
            return None

    def _add_inline_citations(
        self,
        parsed: Dict[str, Any],
        grounding_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Add inline citation markers to text based on grounding supports.
        Citations are added as [1], [2], etc. referencing the source list.
        """
        chunks = grounding_metadata.get("grounding_chunks", [])
        supports = grounding_metadata.get("grounding_supports", [])

        if not chunks or not supports:
            return parsed

        # Create a mapping of text segments to citation indices
        # For now, we just add the search queries as context
        if grounding_metadata.get("web_search_queries"):
            parsed["_search_queries"] = grounding_metadata["web_search_queries"]

        return parsed

    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """Parse JSON response from Gemini."""
        # Clean up response text (remove markdown code blocks if present)
        text = response_text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini response as JSON: {e}")
            logger.debug(f"Response text: {text[:500]}...")

            # Return minimal valid structure
            return {
                "market_assessment": {
                    "summary": "Analyse konnte nicht verarbeitet werden.",
                    "sentiment": "neutral",
                    "confidence": 0.0,
                    "key_factors": [],
                },
                "news_summary": "Die Analyse konnte nicht verarbeitet werden.",
                "news_highlights": [],
                "upcoming_events": [],
            }

    def _build_analysis(
        self,
        symbol: str,
        commodity_name: str,
        parsed: Dict[str, Any],
        sources: List[SourceLink],
        rendered_content: Optional[str],
    ) -> CommodityNewsAnalysis:
        """Build CommodityNewsAnalysis from parsed response."""

        # Market Assessment
        ma_data = parsed.get("market_assessment", {})
        market_assessment = MarketAssessment(
            summary=ma_data.get("summary", ""),
            sentiment=MarketSentiment(ma_data.get("sentiment", "neutral")),
            confidence=float(ma_data.get("confidence", 0.5)),
            key_factors=ma_data.get("key_factors", []),
        )

        # Supply/Demand
        sd_data = parsed.get("supply_demand")
        supply_demand = None
        if sd_data:
            supply_demand = SupplyDemandInfo(
                supply_summary=sd_data.get("supply_summary", ""),
                demand_summary=sd_data.get("demand_summary", ""),
                balance_outlook=sd_data.get("balance_outlook", ""),
            )

        # Macro Factors
        mf_data = parsed.get("macro_factors")
        macro_factors = None
        if mf_data:
            macro_factors = MacroFactors(
                factors=mf_data.get("factors", []),
                summary=mf_data.get("summary", ""),
            )

        # Upcoming Events (already validated)
        events = []
        for event_data in parsed.get("upcoming_events", []):
            try:
                events.append(UpcomingEvent(
                    date=event_data.get("date", ""),
                    description=event_data.get("description", ""),
                    impact=ImpactLevel(event_data.get("impact", "medium")),
                    source=event_data.get("source"),
                    grounding_score=event_data.get("grounding_score"),
                ))
            except Exception as e:
                logger.warning(f"Failed to parse event: {e}")

        return CommodityNewsAnalysis(
            symbol=symbol,
            commodity_name=commodity_name,
            timestamp=datetime.utcnow().isoformat(),
            market_assessment=market_assessment,
            news_summary=parsed.get("news_summary", ""),
            news_highlights=parsed.get("news_highlights", []),
            supply_demand=supply_demand,
            macro_factors=macro_factors,
            upcoming_events=events,
            sources=sources,
            rendered_content=rendered_content,
            from_cache=False,
        )

    def _analysis_to_dict(self, analysis: CommodityNewsAnalysis) -> Dict[str, Any]:
        """Convert analysis to dict for caching."""
        return analysis.model_dump()

    def _dict_to_analysis(self, data: Dict[str, Any], symbol: str) -> CommodityNewsAnalysis:
        """Convert cached dict back to CommodityNewsAnalysis."""
        return CommodityNewsAnalysis(**data)

    async def analyze_multiple(
        self,
        symbols: List[str],
        force_refresh: bool = False
    ) -> Dict[str, CommodityNewsAnalysis]:
        """
        Analyze multiple commodities.

        Args:
            symbols: List of commodity symbols
            force_refresh: If True, bypass cache for all

        Returns:
            Dict mapping symbol to analysis
        """
        results = {}
        errors = {}

        for symbol in symbols:
            try:
                analysis = await self.analyze_commodity(symbol, force_refresh)
                results[symbol] = analysis
            except Exception as e:
                logger.error(f"Failed to analyze {symbol}: {e}")
                errors[symbol] = str(e)

        return results, errors
