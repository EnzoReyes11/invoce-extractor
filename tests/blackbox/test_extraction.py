from __future__ import annotations

import json
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from pdf_data_extraction_agent.model import DocumentType
from pdf_data_extraction_agent.pipeline.extract import run_extraction
from pdf_data_extraction_agent.pipeline.models import ExtractionRecord, ExtractionStatus


def _make_mock_response(data: dict) -> MagicMock:
    mock_response = MagicMock()
    mock_response.text = json.dumps(data)
    return mock_response


@pytest.fixture
def mock_gcs_download():
    with patch("pdf_data_extraction_agent.pipeline.extract._download_from_gcs") as mock:
        mock.return_value = b"%PDF-1.4 fake pdf content"
        yield mock


class TestSuccessPath:
    def test_success_record_returned(self, mock_gcs_download, generic_invoice_data):
        mock_response = _make_mock_response(generic_invoice_data)
        with patch("pdf_data_extraction_agent.pipeline.extract._get_genai_client") as mock_client_factory:
            mock_client = MagicMock()
            mock_client_factory.return_value = mock_client
            mock_client.models.generate_content.return_value = mock_response

            record = run_extraction("gs://bucket/invoice.pdf", "application/pdf")

        assert isinstance(record, ExtractionRecord)
        assert record.status in (ExtractionStatus.success, ExtractionStatus.partial)
        assert record.result is not None
        assert record.result.document_type == DocumentType.Invoice
        assert record.strategy_used == "generic"

    def test_document_type_locale_preserved(self, mock_gcs_download, claro_invoice_data):
        mock_response = _make_mock_response(claro_invoice_data)
        with patch("pdf_data_extraction_agent.pipeline.extract._get_genai_client") as mock_client_factory:
            mock_client = MagicMock()
            mock_client_factory.return_value = mock_client
            mock_client.models.generate_content.return_value = mock_response

            record = run_extraction("gs://bucket/claro.pdf", "application/pdf")

        assert record.result.document_type == DocumentType.Factura
        assert record.result.document_type.value == "Factura"

    def test_overall_total_is_decimal(self, mock_gcs_download, generic_invoice_data):
        mock_response = _make_mock_response(generic_invoice_data)
        with patch("pdf_data_extraction_agent.pipeline.extract._get_genai_client") as mock_client_factory:
            mock_client = MagicMock()
            mock_client_factory.return_value = mock_client
            mock_client.models.generate_content.return_value = mock_response

            record = run_extraction("gs://bucket/invoice.pdf", "application/pdf")

        assert isinstance(record.result.overall_total, Decimal)


class TestPartialPath:
    def test_partial_status_when_optional_fields_null(self, mock_gcs_download, generic_invoice_data):
        # Remove some optional monetary fields to trigger partial status
        partial_data = {**generic_invoice_data, "overall_subtotal": None, "overall_tax": None}
        mock_response = _make_mock_response(partial_data)

        with patch("pdf_data_extraction_agent.pipeline.extract._get_genai_client") as mock_client_factory:
            mock_client = MagicMock()
            mock_client_factory.return_value = mock_client
            mock_client.models.generate_content.return_value = mock_response

            record = run_extraction("gs://bucket/invoice.pdf", "application/pdf")

        assert record.status == ExtractionStatus.partial
        assert record.result is not None


class TestFailedPath:
    def test_gemini_api_error_returns_failed_record(self, mock_gcs_download):
        with patch("pdf_data_extraction_agent.pipeline.extract._get_genai_client") as mock_client_factory:
            mock_client = MagicMock()
            mock_client_factory.return_value = mock_client
            mock_client.models.generate_content.side_effect = Exception("API quota exceeded")

            record = run_extraction("gs://bucket/invoice.pdf", "application/pdf")

        assert record.status == ExtractionStatus.failed
        assert record.error_message is not None
        assert "API quota exceeded" in record.error_message
        assert record.result is None

    def test_invalid_json_returns_failed_record(self, mock_gcs_download):
        mock_response = MagicMock()
        mock_response.text = "not valid json at all"

        with patch("pdf_data_extraction_agent.pipeline.extract._get_genai_client") as mock_client_factory:
            mock_client = MagicMock()
            mock_client_factory.return_value = mock_client
            mock_client.models.generate_content.return_value = mock_response

            record = run_extraction("gs://bucket/invoice.pdf", "application/pdf")

        assert record.status == ExtractionStatus.failed
        assert record.error_message is not None
        assert record.result is None

    def test_gcs_download_failure_returns_failed_record(self):
        with patch("pdf_data_extraction_agent.pipeline.extract._download_from_gcs") as mock_dl:
            mock_dl.side_effect = Exception("bucket not found")
            record = run_extraction("gs://bad-bucket/invoice.pdf", "application/pdf")

        assert record.status == ExtractionStatus.failed
        assert "GCS download failed" in record.error_message

    def test_failed_record_never_raises(self, mock_gcs_download):
        with patch("pdf_data_extraction_agent.pipeline.extract._get_genai_client") as mock_client_factory:
            mock_client = MagicMock()
            mock_client_factory.return_value = mock_client
            mock_client.models.generate_content.side_effect = RuntimeError("catastrophic failure")

            record = run_extraction("gs://bucket/invoice.pdf", "application/pdf")

        assert isinstance(record, ExtractionRecord)


class TestAdaptiveExtraction:
    def test_claro_strategy_used_for_claro_issuer(self, mock_gcs_download, claro_invoice_data):
        mock_response = _make_mock_response(claro_invoice_data)

        with patch("pdf_data_extraction_agent.pipeline.extract._get_genai_client") as mock_client_factory:
            mock_client = MagicMock()
            mock_client_factory.return_value = mock_client
            # Both calls (first pass + re-run) return the same Claro data
            mock_client.models.generate_content.return_value = mock_response

            record = run_extraction("gs://bucket/claro.pdf", "application/pdf")

        assert record.strategy_used == "claro"

    def test_generic_strategy_for_unknown_issuer(self, mock_gcs_download, generic_invoice_data):
        mock_response = _make_mock_response(generic_invoice_data)

        with patch("pdf_data_extraction_agent.pipeline.extract._get_genai_client") as mock_client_factory:
            mock_client = MagicMock()
            mock_client_factory.return_value = mock_client
            mock_client.models.generate_content.return_value = mock_response

            record = run_extraction("gs://bucket/invoice.pdf", "application/pdf")

        assert record.strategy_used == "generic"
