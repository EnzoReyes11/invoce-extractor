from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest


# --- File path fixtures ---


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).parent / "blackbox" / "fixtures"


@pytest.fixture
def sample_invoice_path(fixtures_dir: Path) -> Path:
    return fixtures_dir / "sample_invoice.pdf"


@pytest.fixture
def claro_factura_path(fixtures_dir: Path) -> Path:
    return fixtures_dir / "claro_factura.pdf"


# --- Mock Gemini response factory ---


def make_gemini_response(data: dict) -> MagicMock:
    """Build a mock google.genai model response that returns structured JSON."""
    mock_response = MagicMock()
    mock_response.text = json.dumps(data)
    return mock_response


@pytest.fixture
def generic_invoice_data() -> dict:
    """A valid generic invoice extraction result as a dict."""
    return {
        "document_type": "Invoice",
        "document_number": "INV-001",
        "date_issued": "2026-03-01",
        "date_due": "2026-03-31",
        "date_paid": None,
        "billing_period": None,
        "currency": "USD",
        "issuer": {
            "name": "Acme Corp",
            "tax_id": "12-3456789",
            "address": "123 Main St, Anytown, USA",
            "email": "billing@acme.com",
            "phone": None,
            "website": "https://acme.com",
        },
        "bill_to": {
            "name": "Test Customer",
            "tax_id": None,
            "address": "456 Elm St",
            "email": "customer@example.com",
            "account_number": None,
        },
        "shipping_information": None,
        "payment_method": None,
        "line_items": [
            {
                "description": "Widget A",
                "sku": "WGT-001",
                "quantity": 2.0,
                "unit": "unit",
                "unit_price": "50.00",
                "discount": None,
                "total": "100.00",
                "notes": None,
            }
        ],
        "taxes": [
            {
                "name": "VAT 10%",
                "rate": "10.000000000",
                "amount": "10.00",
            }
        ],
        "overall_subtotal": "100.00",
        "overall_discount": None,
        "overall_tax": "10.00",
        "overall_total": "110.00",
        "overall_amount_paid": None,
        "outstanding_balance": "110.00",
        "tags": ["invoice"],
        "notes": None,
    }


@pytest.fixture
def claro_invoice_data() -> dict:
    """A valid Claro Argentina invoice extraction result as a dict."""
    return {
        "document_type": "Factura",
        "document_number": "0001-00045123",
        "date_issued": "2026-03-01",
        "date_due": None,
        "date_paid": None,
        "billing_period": {
            "start": "2026-02-01",
            "end": "2026-02-28",
        },
        "currency": "ARS",
        "issuer": {
            "name": "Claro Argentina",
            "tax_id": "30-12345678-9",
            "address": None,
            "email": None,
            "phone": None,
            "website": None,
        },
        "bill_to": {
            "name": "Test Usuario",
            "tax_id": None,
            "address": None,
            "email": None,
            "account_number": "ACC-123",
        },
        "shipping_information": None,
        "payment_method": None,
        "line_items": [
            {
                "description": "Plan Claro Control 500",
                "sku": None,
                "quantity": 1.0,
                "unit": None,
                "unit_price": "12000.00",
                "discount": None,
                "total": "12000.00",
                "notes": None,
            },
            {
                "description": "Servicio de Datos 5GB",
                "sku": None,
                "quantity": 1.0,
                "unit": None,
                "unit_price": "710.50",
                "discount": None,
                "total": "710.50",
                "notes": None,
            },
        ],
        "taxes": [
            {
                "name": "IVA 21%",
                "rate": "21.000000000",
                "amount": "2672.21",
            }
        ],
        "overall_subtotal": "12710.50",
        "overall_discount": None,
        "overall_tax": "2672.21",
        "overall_total": "15382.71",
        "overall_amount_paid": None,
        "outstanding_balance": "15382.71",
        "tags": ["telecom", "monthly"],
        "notes": None,
    }
