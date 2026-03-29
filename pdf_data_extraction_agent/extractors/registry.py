from __future__ import annotations

from pdf_data_extraction_agent.extractors.base import ExtractionStrategy
from pdf_data_extraction_agent.extractors.claro import CLARO_STRATEGY
from pdf_data_extraction_agent.extractors.generic import GENERIC_STRATEGY

# Maps lowercase issuer pattern → ExtractionStrategy.
# Lookup is case-insensitive substring matching against the detected issuer name.
STRATEGY_REGISTRY: dict[str, ExtractionStrategy] = {
    "claro": CLARO_STRATEGY,
}


def get_strategy(issuer_name: str | None) -> ExtractionStrategy:
    """Return the ExtractionStrategy matching the issuer name, or GENERIC_STRATEGY."""
    if not issuer_name:
        return GENERIC_STRATEGY
    normalized = issuer_name.lower()
    for pattern, strategy in STRATEGY_REGISTRY.items():
        if pattern in normalized:
            return strategy
    return GENERIC_STRATEGY
