from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from pdf_data_extraction_agent.extractors.generic import GENERIC_STRATEGY
from pdf_data_extraction_agent.pipeline.extract import _determine_status, run_extraction
from pdf_data_extraction_agent.pipeline.models import ExtractionRecord, ExtractionStatus
from pdf_data_extraction_agent.model import DocumentType, ExtractionResult, Issuer, LineItem


@pytest.fixture
def minimal_result():
    return ExtractionResult(
        document_type=DocumentType.Invoice,
        currency="USD",
        issuer=Issuer(name="Acme"),
        line_items=[LineItem(description="Item", total="100.00")],
        overall_total="100.00",
    )


@pytest.fixture
def full_result():
    return ExtractionResult(
        document_type=DocumentType.Invoice,
        currency="USD",
        issuer=Issuer(name="Acme"),
        line_items=[LineItem(description="Item", total="100.00")],
        overall_total="110.00",
        overall_subtotal="100.00",
        overall_tax="10.00",
        overall_discount="0.00",
        overall_amount_paid="110.00",
        outstanding_balance="0.00",
    )


class TestDetermineStatus:
    def test_partial_when_optional_fields_missing(self, minimal_result):
        # minimal_result has no subtotal, discount, tax, etc.
        assert _determine_status(minimal_result) == ExtractionStatus.partial

    def test_success_when_all_monetary_fields_present(self, full_result):
        assert _determine_status(full_result) == ExtractionStatus.success


class TestRunExtraction:
    def test_returns_extraction_record(self, generic_invoice_data):
        mock_response = MagicMock()
        mock_response.text = json.dumps(generic_invoice_data)

        with (
            patch("pdf_data_extraction_agent.pipeline.extract._download_from_gcs") as mock_dl,
            patch("pdf_data_extraction_agent.pipeline.extract._get_genai_client") as mock_client_factory,
        ):
            mock_dl.return_value = b"pdf bytes"
            mock_client = MagicMock()
            mock_client_factory.return_value = mock_client
            mock_client.models.generate_content.return_value = mock_response

            record = run_extraction("gs://b/f.pdf", "application/pdf")

        assert isinstance(record, ExtractionRecord)

    def test_strategy_used_set_to_generic(self, generic_invoice_data):
        mock_response = MagicMock()
        mock_response.text = json.dumps(generic_invoice_data)

        with (
            patch("pdf_data_extraction_agent.pipeline.extract._download_from_gcs") as mock_dl,
            patch("pdf_data_extraction_agent.pipeline.extract._get_genai_client") as mock_client_factory,
        ):
            mock_dl.return_value = b"pdf bytes"
            mock_client = MagicMock()
            mock_client_factory.return_value = mock_client
            mock_client.models.generate_content.return_value = mock_response

            record = run_extraction("gs://b/f.pdf", "application/pdf")

        assert record.strategy_used == "generic"

    def test_source_file_uri_preserved(self, generic_invoice_data):
        mock_response = MagicMock()
        mock_response.text = json.dumps(generic_invoice_data)

        with (
            patch("pdf_data_extraction_agent.pipeline.extract._download_from_gcs") as mock_dl,
            patch("pdf_data_extraction_agent.pipeline.extract._get_genai_client") as mock_client_factory,
        ):
            mock_dl.return_value = b"pdf bytes"
            mock_client = MagicMock()
            mock_client_factory.return_value = mock_client
            mock_client.models.generate_content.return_value = mock_response

            record = run_extraction("gs://bucket/my-invoice.pdf", "application/pdf")

        assert record.source_file_uri == "gs://bucket/my-invoice.pdf"

    def test_gcs_error_returns_failed_record(self):
        with patch("pdf_data_extraction_agent.pipeline.extract._download_from_gcs") as mock_dl:
            mock_dl.side_effect = Exception("permission denied")
            record = run_extraction("gs://b/f.pdf", "application/pdf")

        assert record.status == ExtractionStatus.failed
        assert record.result is None
        assert "GCS download failed" in record.error_message

    def test_never_raises(self):
        with patch("pdf_data_extraction_agent.pipeline.extract._download_from_gcs") as mock_dl:
            mock_dl.side_effect = RuntimeError("critical failure")
            record = run_extraction("gs://b/f.pdf", "application/pdf")

        assert isinstance(record, ExtractionRecord)
