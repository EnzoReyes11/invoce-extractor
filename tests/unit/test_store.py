from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from pdf_data_extraction_agent.model import DocumentType, ExtractionResult, Issuer, LineItem, Tax
from pdf_data_extraction_agent.pipeline.models import ExtractionRecord, ExtractionStatus
from pdf_data_extraction_agent.pipeline.store import BigQueryWriter, _record_to_bq_row


@pytest.fixture
def success_record():
    result = ExtractionResult(
        document_type=DocumentType.Invoice,
        currency="USD",
        issuer=Issuer(name="Acme Corp", tax_id="12-345"),
        line_items=[
            LineItem(description="Widget", quantity=2.0, unit_price="50.00", total="100.00")
        ],
        taxes=[Tax(name="VAT 10%", rate="10.000000000", amount="10.00")],
        overall_subtotal="100.00",
        overall_total="110.00",
    )
    return ExtractionRecord(
        source_file_uri="gs://bucket/invoice.pdf",
        source_format="application/pdf",
        status=ExtractionStatus.success,
        strategy_used="generic",
        result=result,
    )


@pytest.fixture
def failed_record():
    return ExtractionRecord(
        source_file_uri="gs://bucket/bad.pdf",
        source_format="application/pdf",
        status=ExtractionStatus.failed,
        strategy_used="generic",
        error_message="Gemini API error: model unavailable",
        raw_gemini_response="error text",
    )


class TestRecordToBqRow:
    def test_decimal_fields_serialized_as_strings(self, success_record):
        row = _record_to_bq_row(success_record)
        assert isinstance(row["result"]["overall_total"], str)
        assert row["result"]["overall_total"] == "100.00" or row["result"]["overall_total"] == "110.00"

    def test_overall_total_is_string(self, success_record):
        row = _record_to_bq_row(success_record)
        assert row["result"]["overall_total"] == "110.00"

    def test_line_item_total_is_string(self, success_record):
        row = _record_to_bq_row(success_record)
        line_items = row["result"]["line_items"]
        assert len(line_items) == 1
        assert line_items[0]["total"] == "100.00"
        assert isinstance(line_items[0]["total"], str)

    def test_line_item_unit_price_is_string(self, success_record):
        row = _record_to_bq_row(success_record)
        assert row["result"]["line_items"][0]["unit_price"] == "50.00"

    def test_tax_rate_is_string(self, success_record):
        row = _record_to_bq_row(success_record)
        assert row["result"]["taxes"][0]["rate"] == "10.000000000"

    def test_tax_amount_is_string(self, success_record):
        row = _record_to_bq_row(success_record)
        assert row["result"]["taxes"][0]["amount"] == "10.00"

    def test_line_item_quantity_is_float(self, success_record):
        row = _record_to_bq_row(success_record)
        assert row["result"]["line_items"][0]["quantity"] == 2.0
        assert isinstance(row["result"]["line_items"][0]["quantity"], float)

    def test_document_type_is_string_value(self, success_record):
        row = _record_to_bq_row(success_record)
        assert row["result"]["document_type"] == "Invoice"

    def test_status_is_string_value(self, success_record):
        row = _record_to_bq_row(success_record)
        assert row["status"] == "success"

    def test_extracted_at_is_string(self, success_record):
        row = _record_to_bq_row(success_record)
        assert isinstance(row["extracted_at"], str)

    def test_issuer_struct(self, success_record):
        row = _record_to_bq_row(success_record)
        assert row["result"]["issuer"]["name"] == "Acme Corp"
        assert row["result"]["issuer"]["tax_id"] == "12-345"


class TestFailedRecord:
    def test_failed_status(self, failed_record):
        row = _record_to_bq_row(failed_record)
        assert row["status"] == "failed"

    def test_result_is_none(self, failed_record):
        row = _record_to_bq_row(failed_record)
        assert row["result"] is None

    def test_error_message_populated(self, failed_record):
        row = _record_to_bq_row(failed_record)
        assert row["error_message"] == "Gemini API error: model unavailable"


class TestBigQueryWriter:
    def test_write_record_calls_insert(self, success_record):
        with patch("pdf_data_extraction_agent.pipeline.store.bigquery.Client") as MockClient:
            mock_client = MagicMock()
            MockClient.return_value = mock_client
            mock_client.project = "test-project"
            mock_client.insert_rows_json.return_value = []

            writer = BigQueryWriter(dataset="expense_tracking", table="extractions")
            writer.write_record(success_record)

            mock_client.insert_rows_json.assert_called_once()
            call_args = mock_client.insert_rows_json.call_args
            table_ref = call_args[0][0]
            assert "expense_tracking" in table_ref
            assert "extractions" in table_ref

    def test_write_record_raises_on_bq_errors(self, success_record):
        with patch("pdf_data_extraction_agent.pipeline.store.bigquery.Client") as MockClient:
            mock_client = MagicMock()
            MockClient.return_value = mock_client
            mock_client.project = "test-project"
            mock_client.insert_rows_json.return_value = [{"errors": ["insert failed"]}]

            writer = BigQueryWriter(dataset="expense_tracking", table="extractions")
            with pytest.raises(RuntimeError, match="BigQuery insert errors"):
                writer.write_record(success_record)
