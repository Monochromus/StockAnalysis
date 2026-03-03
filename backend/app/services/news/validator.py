"""
Grounding score validation for Gemini responses.
Implements anti-hallucination filtering based on grounding scores.
"""

import logging
from typing import List, Dict, Any, Optional

from app.schemas.news import (
    UpcomingEvent,
    SourceLink,
    ImpactLevel,
)

logger = logging.getLogger(__name__)


class GroundingValidator:
    """
    Validates and filters Gemini responses based on grounding scores.
    This is the third layer of anti-hallucination protection.
    """

    MIN_GROUNDING_SCORE = 0.7  # Events below this score are filtered out

    def __init__(self, min_score: float = 0.7):
        self.min_score = min_score

    def filter_events(
        self,
        events: List[Dict[str, Any]],
        grounding_metadata: Optional[Dict[str, Any]] = None
    ) -> List[UpcomingEvent]:
        """
        Filter events based on grounding scores.
        Events without sufficient grounding are removed.

        Args:
            events: List of event dictionaries from Gemini response
            grounding_metadata: Optional grounding metadata from API response

        Returns:
            List of validated UpcomingEvent objects
        """
        validated_events = []

        for event in events:
            # Extract grounding score if available
            grounding_score = event.get("grounding_score")

            # If no grounding score available, try to infer from metadata
            if grounding_score is None and grounding_metadata:
                grounding_score = self._get_event_grounding_score(
                    event, grounding_metadata
                )

            # Filter events without sufficient grounding
            if grounding_score is not None and grounding_score < self.min_score:
                logger.warning(
                    f"Event filtered due to low grounding score ({grounding_score:.2f}): "
                    f"{event.get('description', 'Unknown event')}"
                )
                continue

            # If no grounding score at all, be conservative and include with warning
            if grounding_score is None:
                logger.info(
                    f"Event included without grounding score: "
                    f"{event.get('description', 'Unknown event')}"
                )

            try:
                validated_event = UpcomingEvent(
                    date=event.get("date", "Unbekannt"),
                    description=event.get("description", ""),
                    impact=ImpactLevel(event.get("impact", "medium")),
                    source=event.get("source"),
                    grounding_score=grounding_score,
                )
                validated_events.append(validated_event)
            except Exception as e:
                logger.warning(f"Failed to parse event: {e}")
                continue

        return validated_events

    def extract_sources(
        self,
        grounding_metadata: Optional[Dict[str, Any]]
    ) -> List[SourceLink]:
        """
        Extract source links from grounding metadata.

        Args:
            grounding_metadata: Grounding metadata from Gemini API

        Returns:
            List of SourceLink objects with grounding scores
        """
        sources = []

        if not grounding_metadata:
            return sources

        # Extract grounding chunks/sources
        grounding_chunks = grounding_metadata.get("grounding_chunks", [])

        for chunk in grounding_chunks:
            web_info = chunk.get("web", {})
            uri = web_info.get("uri", "")
            title = web_info.get("title", uri)

            if uri:
                # Try to get confidence score for this source
                score = chunk.get("confidence_score")

                sources.append(SourceLink(
                    title=title,
                    url=uri,
                    grounding_score=score,
                ))

        return sources

    def _get_event_grounding_score(
        self,
        event: Dict[str, Any],
        grounding_metadata: Dict[str, Any]
    ) -> Optional[float]:
        """
        Try to determine grounding score for an event from metadata.

        This is a heuristic approach - looks for supporting evidence
        in the grounding metadata that relates to the event.
        """
        # Get grounding supports
        supports = grounding_metadata.get("grounding_supports", [])

        if not supports:
            return None

        # Look for support that mentions the event date or description
        event_date = event.get("date", "")
        event_desc = event.get("description", "").lower()

        for support in supports:
            segment = support.get("segment", {})
            text = segment.get("text", "").lower()

            # Check if support text relates to this event
            if event_date in text or any(
                word in text for word in event_desc.split()[:3]
            ):
                confidence_scores = support.get("grounding_chunk_indices", [])
                if confidence_scores:
                    # Return average confidence
                    return sum(confidence_scores) / len(confidence_scores)

        return None

    def validate_response(
        self,
        parsed_response: Dict[str, Any],
        grounding_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Validate and filter the complete parsed response.

        Args:
            parsed_response: Parsed JSON response from Gemini
            grounding_metadata: Optional grounding metadata

        Returns:
            Validated response with filtered events and extracted sources
        """
        # Filter events
        raw_events = parsed_response.get("upcoming_events", [])
        validated_events = self.filter_events(raw_events, grounding_metadata)

        # Log filtering results
        filtered_count = len(raw_events) - len(validated_events)
        if filtered_count > 0:
            logger.info(
                f"Filtered {filtered_count} events due to insufficient grounding"
            )

        # Extract sources
        sources = self.extract_sources(grounding_metadata)

        # Update response
        parsed_response["upcoming_events"] = [
            {
                "date": e.date,
                "description": e.description,
                "impact": e.impact.value,
                "source": e.source,
                "grounding_score": e.grounding_score,
            }
            for e in validated_events
        ]

        return parsed_response, sources
