from __future__ import annotations

from pdf_data_extraction_agent.extractors.base import ExtractionStrategy

CLARO_STRATEGY = ExtractionStrategy(
    name="claro",
    issuer_pattern="claro",
    prompt_override=(
        "IMPORTANT: Claro invoices list multiple services and add-ons on a single bill. "
        "Extract each service, plan, or charge as a SEPARATE LineItem. "
        "Do not merge multiple services into one line item. "
        "Common line items include: base plan, data add-ons, roaming charges, equipment fees, "
        "and taxes listed per-service. Treat each as its own entry with its individual total."
    ),
)
