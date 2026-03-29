from __future__ import annotations

import os

from dotenv import load_dotenv
from google import genai
from google.cloud import storage
from google.genai import types
from pydantic import ValidationError

from pdf_data_extraction_agent.extractors.base import ExtractionStrategy
from pdf_data_extraction_agent.extractors.generic import GENERIC_STRATEGY
from pdf_data_extraction_agent.extractors.registry import get_strategy
from pdf_data_extraction_agent.model import ExtractionResult
from pdf_data_extraction_agent.pipeline.models import ExtractionRecord, ExtractionStatus

load_dotenv()

_GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")
_GOOGLE_CLOUD_LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION")
_MODEL_ID = os.getenv("GEMINI_MODEL_ID") or os.getenv("MODEL_ID", "gemini-2.5-flash")
_USE_VERTEXAI = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "true").lower() == "true"

_RAW_RESPONSE_MAX_BYTES = 10 * 1024  # 10KB truncation limit


def _get_genai_client() -> genai.Client:
    return genai.Client(
        vertexai=_USE_VERTEXAI,
        project=_GOOGLE_CLOUD_PROJECT,
        location=_GOOGLE_CLOUD_LOCATION,
    )


def _download_from_gcs(gcs_uri: str) -> bytes:
    """Download a file from GCS and return its bytes."""
    # gcs_uri format: gs://bucket-name/path/to/file
    assert gcs_uri.startswith("gs://"), f"Expected gs:// URI, got: {gcs_uri}"
    path = gcs_uri[len("gs://"):]
    bucket_name, _, blob_name = path.partition("/")
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    return blob.download_as_bytes()


def _build_generate_config(strategy: ExtractionStrategy) -> types.GenerateContentConfig:
    """Build the Gemini generation config for a given strategy."""
    system_instruction = (
        "You are a document data extraction specialist. "
        "Extract all financial data from the provided document accurately. "
        "Preserve locale-specific document type names exactly as they appear "
        "(e.g., 'Factura', 'Boleta de Venta', 'Recibo' — do NOT translate to English). "
        "Use ISO 8601 (YYYY-MM-DD) for all dates. "
        "All monetary values must be numbers (not strings). "
        "Extract each line item individually — do not merge or summarize."
    )
    if strategy.prompt_override:
        system_instruction = f"{system_instruction}\n\n{strategy.prompt_override}"

    return types.GenerateContentConfig(
        system_instruction=system_instruction,
        temperature=0,
        top_p=1,
        seed=0,
        max_output_tokens=65535,
        response_mime_type="application/json",
        thinking_config=types.ThinkingConfig(thinking_budget=512),
        response_schema=ExtractionResult,
    )


def _call_gemini(
    file_bytes: bytes,
    source_format: str,
    strategy: ExtractionStrategy,
) -> tuple[ExtractionResult | None, str | None, str | None]:
    """
    Call Gemini with the file and strategy. Returns (result, error_message, raw_response).
    raw_response is truncated to _RAW_RESPONSE_MAX_BYTES.
    """
    client = _get_genai_client()
    document_part = types.Part.from_bytes(data=file_bytes, mime_type=source_format)
    contents = [types.Content(role="user", parts=[document_part])]
    config = _build_generate_config(strategy)

    try:
        response = client.models.generate_content(
            model=_MODEL_ID,
            contents=contents,
            config=config,
        )
    except Exception as e:
        return None, f"Gemini API error: {e}", None

    raw_text = response.text or ""
    truncated_raw = raw_text[:_RAW_RESPONSE_MAX_BYTES] if len(raw_text) > _RAW_RESPONSE_MAX_BYTES else raw_text

    try:
        result = ExtractionResult.model_validate_json(raw_text.replace("\n", " "))
        return result, None, truncated_raw
    except ValidationError as e:
        return None, f"Pydantic validation error: {e}", truncated_raw


def _determine_status(result: ExtractionResult) -> ExtractionStatus:
    """Determine success vs partial based on whether optional fields are populated."""
    optional_monetary = [
        result.overall_subtotal,
        result.overall_discount,
        result.overall_tax,
        result.overall_amount_paid,
        result.outstanding_balance,
    ]
    if any(v is None for v in optional_monetary):
        return ExtractionStatus.partial
    return ExtractionStatus.success


def run_extraction(
    source_file_uri: str,
    source_format: str,
    strategy: ExtractionStrategy | None = None,
) -> ExtractionRecord:
    """
    Download a file from GCS, invoke Gemini extraction, and return an ExtractionRecord.

    Two-pass extraction for adaptive strategy:
    1. First pass with GENERIC_STRATEGY to detect issuer name.
    2. If the detected issuer maps to a custom strategy, re-run with that strategy.

    Always returns an ExtractionRecord — never raises.
    """
    try:
        file_bytes = _download_from_gcs(source_file_uri)
    except Exception as e:
        return ExtractionRecord(
            source_file_uri=source_file_uri,
            source_format=source_format,
            status=ExtractionStatus.failed,
            strategy_used=GENERIC_STRATEGY.name,
            error_message=f"GCS download failed: {e}",
        )

    # Pass 1: generic extraction to detect issuer
    first_strategy = strategy or GENERIC_STRATEGY
    result, error, raw = _call_gemini(file_bytes, source_format, first_strategy)

    if result is None:
        return ExtractionRecord(
            source_file_uri=source_file_uri,
            source_format=source_format,
            status=ExtractionStatus.failed,
            strategy_used=first_strategy.name,
            error_message=error,
            raw_gemini_response=raw,
        )

    # Pass 2: if no explicit strategy was forced, check registry for issuer-specific one
    if strategy is None:
        issuer_name = result.issuer.name if result.issuer else None
        detected_strategy = get_strategy(issuer_name)

        if detected_strategy.name != GENERIC_STRATEGY.name:
            # Re-run with issuer-specific strategy
            result2, error2, raw2 = _call_gemini(file_bytes, source_format, detected_strategy)
            if result2 is not None:
                result = result2
                raw = raw2
                first_strategy = detected_strategy
            # If re-run fails, keep the first-pass result but use the detected strategy name
            else:
                first_strategy = detected_strategy

    status = _determine_status(result)
    return ExtractionRecord(
        source_file_uri=source_file_uri,
        source_format=source_format,
        status=status,
        strategy_used=first_strategy.name,
        result=result,
        raw_gemini_response=raw,
    )
