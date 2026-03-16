from __future__ import annotations

from decimal import Decimal

import pytest

from pdf_data_extraction_agent.model import (
    DocumentType,
    ExtractionResult,
    Issuer,
    LineItem,
    Tax,
)


class TestDecimalFields:
    def test_tax_amount_from_string(self):
        tax = Tax(name="VAT", amount="10.50")
        assert tax.amount == Decimal("10.50")
        assert isinstance(tax.amount, Decimal)

    def test_tax_rate_from_string(self):
        tax = Tax(name="VAT", rate="21.000000000", amount="10.50")
        assert tax.rate == Decimal("21.000000000")
        assert isinstance(tax.rate, Decimal)

    def test_tax_rate_none(self):
        tax = Tax(name="VAT", amount="10.50")
        assert tax.rate is None

    def test_line_item_total_from_string(self):
        item = LineItem(description="Widget", total="100.00")
        assert item.total == Decimal("100.00")
        assert isinstance(item.total, Decimal)

    def test_line_item_unit_price_from_string(self):
        item = LineItem(description="Widget", unit_price="50.00", total="100.00")
        assert item.unit_price == Decimal("50.00")

    def test_line_item_discount_from_string(self):
        item = LineItem(description="Widget", discount="5.00", total="95.00")
        assert item.discount == Decimal("5.00")

    def test_line_item_quantity_is_float(self):
        item = LineItem(description="Widget", quantity=2.5, total="100.00")
        assert isinstance(item.quantity, float)
        assert item.quantity == 2.5

    def test_extraction_result_overall_total_from_string(self):
        result = ExtractionResult(
            document_type=DocumentType.Invoice,
            currency="USD",
            issuer=Issuer(name="Acme"),
            line_items=[LineItem(description="Widget", total="100.00")],
            overall_total="110.00",
        )
        assert result.overall_total == Decimal("110.00")
        assert isinstance(result.overall_total, Decimal)

    def test_extraction_result_monetary_fields_from_numeric(self):
        result = ExtractionResult(
            document_type=DocumentType.Invoice,
            currency="USD",
            issuer=Issuer(name="Acme"),
            line_items=[LineItem(description="Widget", total=100)],
            overall_total=110,
            overall_subtotal=100,
            overall_tax=10,
        )
        assert result.overall_total == Decimal("110")
        assert result.overall_subtotal == Decimal("100")
        assert result.overall_tax == Decimal("10")

    def test_extraction_result_optional_monetary_fields_none(self):
        result = ExtractionResult(
            document_type=DocumentType.Invoice,
            currency="USD",
            issuer=Issuer(name="Acme"),
            line_items=[LineItem(description="Widget", total="100.00")],
            overall_total="100.00",
        )
        assert result.overall_subtotal is None
        assert result.overall_discount is None
        assert result.overall_tax is None
        assert result.overall_amount_paid is None
        assert result.outstanding_balance is None


class TestDocumentTypeEnum:
    def test_locale_values_preserved(self):
        assert DocumentType.Factura.value == "Factura"
        assert DocumentType.Boleta.value == "Boleta de Venta"
        assert DocumentType.Recibo.value == "Recibo"

    def test_english_values_preserved(self):
        assert DocumentType.Invoice.value == "Invoice"
        assert DocumentType.Receipt.value == "Receipt"

    def test_parse_from_string(self):
        result = ExtractionResult(
            document_type="Factura",
            currency="ARS",
            issuer=Issuer(name="Acme"),
            line_items=[LineItem(description="Item", total="100.00")],
            overall_total="100.00",
        )
        assert result.document_type == DocumentType.Factura
        assert result.document_type.value == "Factura"
