from __future__ import annotations

from pdf_data_extraction_agent.extractors.base import ExtractionStrategy

GENERIC_STRATEGY = ExtractionStrategy(
    name="generic",
    issuer_pattern="",
    prompt_override="",
)
