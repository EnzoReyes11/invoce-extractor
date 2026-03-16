from __future__ import annotations

import os
from decimal import Decimal
from typing import Any

from google.cloud import bigquery

from pdf_data_extraction_agent.pipeline.models import ExtractionRecord


def _serialize_value(value: Any) -> Any:
    """Recursively convert Decimal to string for BigQuery NUMERIC wire format."""
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {k: _serialize_value(v) for k, v in value.items() if not (isinstance(v, list) and len(v) == 0)}
    if isinstance(value, list):
        return [_serialize_value(item) for item in value]
    return value


def _record_to_bq_row(record: ExtractionRecord) -> dict:
    """Serialize an ExtractionRecord to a BigQuery-compatible row dict."""
    row = record.model_dump(mode="python")

    # Convert datetime to ISO string
    row["extracted_at"] = record.extracted_at.isoformat()

    # Recursively convert all Decimal fields to strings
    row = _serialize_value(row)

    # Flatten enum values to their string representation
    row["status"] = record.status.value

    # Serialize result sub-model
    if record.result is not None:
        result_dict = record.result.model_dump(mode="python")
        result_dict = _serialize_value(result_dict)

        # Serialize nested enum
        if result_dict.get("document_type") is not None:
            result_dict["document_type"] = record.result.document_type.value

        # Serialize payment_method enum
        if result_dict.get("payment_method") and result_dict["payment_method"].get("method"):
            result_dict["payment_method"]["method"] = record.result.payment_method.method.value

        result_dict.pop("shipping_information", None)
        for repeated_field in ("tags", "line_items", "taxes"):
            if not result_dict.get(repeated_field):
                result_dict.pop(repeated_field, None)
        row["result"] = result_dict
    else:
        row["result"] = None

    return row


class BigQueryWriter:
    """Writes ExtractionRecord rows to BigQuery via streaming insert."""

    def __init__(self, dataset: str | None = None, table: str | None = None) -> None:
        self.dataset = dataset or os.environ["BQ_DATASET"]
        self.table = table or os.environ["BQ_TABLE"]
        self._client: bigquery.Client | None = None

    @property
    def client(self) -> bigquery.Client:
        if self._client is None:
            self._client = bigquery.Client()
        return self._client

    @property
    def table_ref(self) -> str:
        project = self.client.project
        return f"{project}.{self.dataset}.{self.table}"

    def write_record(self, record: ExtractionRecord) -> None:
        """Serialize and stream-insert one ExtractionRecord into BigQuery."""
        row = _record_to_bq_row(record)
        errors = self.client.insert_rows_json(self.table_ref, [row])
        if errors:
            raise RuntimeError(f"BigQuery insert errors for record {record.id}: {errors}")
