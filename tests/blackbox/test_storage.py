from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from pdf_data_extraction_agent.model import DocumentType
from pdf_data_extraction_agent.pipeline.extract import run_extraction
from pdf_data_extraction_agent.pipeline.models import ExtractionStatus


@pytest.fixture
def mock_gcs_download():
    with patch("pdf_data_extraction_agent.pipeline.extract._download_from_gcs") as mock:
        mock.return_value = b"%PDF-1.4 fake pdf content"
        yield mock


class TestFullPipeline:
    def test_successful_extraction_writes_to_bigquery(self, mock_gcs_download, generic_invoice_data):
        mock_gemini_response = MagicMock()
        mock_gemini_response.text = json.dumps(generic_invoice_data)

        with (
            patch("pdf_data_extraction_agent.pipeline.extract._get_genai_client") as mock_genai,
            patch("pdf_data_extraction_agent.pipeline.store.bigquery.Client") as mock_bq_client_cls,
        ):
            mock_genai_client = MagicMock()
            mock_genai.return_value = mock_genai_client
            mock_genai_client.models.generate_content.return_value = mock_gemini_response

            mock_bq = MagicMock()
            mock_bq_client_cls.return_value = mock_bq
            mock_bq.project = "test-project"
            mock_bq.insert_rows_json.return_value = []

            from pdf_data_extraction_agent.pipeline.store import BigQueryWriter

            record = run_extraction("gs://bucket/invoice.pdf", "application/pdf")
            writer = BigQueryWriter(dataset="expense_tracking", table="extractions")
            writer.write_record(record)

        mock_bq.insert_rows_json.assert_called_once()
        call_args = mock_bq.insert_rows_json.call_args
        table_ref = call_args[0][0]
        rows = call_args[0][1]

        assert "expense_tracking" in table_ref
        assert "extractions" in table_ref
        assert len(rows) == 1

    def test_failed_extraction_still_writes_to_bigquery(self, mock_gcs_download):
        with (
            patch("pdf_data_extraction_agent.pipeline.extract._get_genai_client") as mock_genai,
            patch("pdf_data_extraction_agent.pipeline.store.bigquery.Client") as mock_bq_client_cls,
        ):
            mock_genai_client = MagicMock()
            mock_genai.return_value = mock_genai_client
            mock_genai_client.models.generate_content.side_effect = Exception("model error")

            mock_bq = MagicMock()
            mock_bq_client_cls.return_value = mock_bq
            mock_bq.project = "test-project"
            mock_bq.insert_rows_json.return_value = []

            from pdf_data_extraction_agent.pipeline.store import BigQueryWriter

            record = run_extraction("gs://bucket/bad.pdf", "application/pdf")
            assert record.status == ExtractionStatus.failed

            writer = BigQueryWriter(dataset="expense_tracking", table="extractions")
            writer.write_record(record)

        mock_bq.insert_rows_json.assert_called_once()
        rows = mock_bq.insert_rows_json.call_args[0][1]
        assert rows[0]["status"] == "failed"
        assert rows[0]["error_message"] is not None
