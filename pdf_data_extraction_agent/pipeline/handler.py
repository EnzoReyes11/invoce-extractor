from __future__ import annotations

import base64
import json
import logging
import os

from dotenv import load_dotenv

from pdf_data_extraction_agent.pipeline.extract import run_extraction
from pdf_data_extraction_agent.pipeline.store import BigQueryWriter

load_dotenv()

logger = logging.getLogger(__name__)

# Supported MIME types for extraction
SUPPORTED_FORMATS = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
    "image/heic",
    "image/heif",
}

# Validated at startup to surface misconfiguration early
_REQUIRED_ENV_VARS = ("BQ_DATASET", "BQ_TABLE", "GOOGLE_CLOUD_PROJECT")


def _validate_env() -> None:
    missing = [v for v in _REQUIRED_ENV_VARS if not os.getenv(v)]
    if missing:
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(missing)}"
        )


_validate_env()


def _parse_pubsub_message(body: dict) -> tuple[str, str]:
    """
    Parse a Pub/Sub push message and return (gcs_uri, source_format).
    Raises ValueError on unsupported format or malformed message.
    """
    try:
        encoded = body["message"]["data"]
        payload = json.loads(base64.b64decode(encoded).decode("utf-8"))
    except (KeyError, ValueError, TypeError) as e:
        raise ValueError(f"Malformed Pub/Sub message: {e}") from e

    bucket = payload.get("bucket", "")
    name = payload.get("name", "")
    content_type = payload.get("contentType", "application/octet-stream")

    if not bucket or not name:
        raise ValueError(f"Missing bucket or name in GCS event payload: {payload}")

    gcs_uri = f"gs://{bucket}/{name}"

    if content_type not in SUPPORTED_FORMATS:
        raise ValueError(
            f"Unsupported file format '{content_type}' for {gcs_uri}. "
            f"Supported: {sorted(SUPPORTED_FORMATS)}"
        )

    return gcs_uri, content_type


def handle_pubsub(body: dict) -> tuple[str, int]:
    """
    Process a Pub/Sub push message from GCS OBJECT_FINALIZE event.

    Returns (response_body, http_status_code).
    - 200: processed (success, partial, or stored failure)
    - 400: unsupported file type — Pub/Sub should not retry
    - 500: transient error — Pub/Sub will retry
    """
    try:
        gcs_uri, source_format = _parse_pubsub_message(body)
    except ValueError as e:
        logger.warning("Rejected message: %s", e)
        return str(e), 400

    logger.info("Processing %s (%s)", gcs_uri, source_format)

    try:
        record = run_extraction(gcs_uri, source_format)
    except Exception as e:
        logger.exception("Unexpected error during extraction for %s", gcs_uri)
        return f"Extraction error: {e}", 500

    try:
        writer = BigQueryWriter()
        writer.write_record(record)
    except Exception as e:
        logger.exception("Failed to write record for %s to BigQuery", gcs_uri)
        return f"BigQuery write error: {e}", 500

    logger.info(
        "Stored record %s for %s with status=%s strategy=%s",
        record.id,
        gcs_uri,
        record.status.value,
        record.strategy_used,
    )
    return record.id, 200
