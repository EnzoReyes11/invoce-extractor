from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from pdf_data_extraction_agent.model import ExtractionResult


class ExtractionStatus(str, Enum):
    success = "success"
    partial = "partial"
    failed = "failed"


class ExtractionRecord(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str = Field(default_factory=lambda: str(uuid4()))
    source_file_uri: str = Field(..., description="GCS URI of the source document.")
    source_format: str = Field(
        ..., description="MIME type: application/pdf, image/jpeg, etc."
    )
    status: ExtractionStatus = Field(
        ..., description="Extraction outcome: success, partial, or failed."
    )
    strategy_used: str = Field(
        ..., description='Strategy name used: "generic" or issuer name (e.g. "claro").'
    )
    result: ExtractionResult | None = Field(
        None, description="Extracted data. Null only when status = failed."
    )
    error_message: str | None = Field(
        None, description="Human-readable error description."
    )
    raw_gemini_response: str | None = Field(
        None, description="Raw Gemini response for debugging (truncated to 10KB)."
    )
    extracted_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of extraction.",
    )
