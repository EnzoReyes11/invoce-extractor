from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ExtractionStrategy:
    """Configuration for an issuer-specific extraction strategy."""

    name: str
    issuer_pattern: str
    prompt_override: str = field(default="")
