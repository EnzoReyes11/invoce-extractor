from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class DocumentType(str, Enum):
    Receipt = "Receipt"
    Invoice = "Invoice"
    Credit_Note = "Credit Note"
    Order_Confirmation = "Order Confirmation"
    Subscription = "Subscription"
    Other = "Other"


class PaymentMethodType(str, Enum):
    Cash = "Cash"
    Credit_Card = "Credit Card"
    Debit_Card = "Debit Card"
    Bank_Transfer = "Bank Transfer"
    Digital_Wallet = "Digital Wallet"
    Store_Credit = "Store Credit"
    Gift_Card = "Gift Card"
    Crypto = "Crypto"
    Other = "Other"


class Issuer(BaseModel):
    name: str = Field(..., description="The name of the issuer.")
    tax_id: str | None = Field(None, description="VAT number, CUIT, EIN, or equivalent tax identifier.")
    address: str | None = Field(None, description="The address of the issuer.")
    email: str | None = Field(None, description="The email address of the issuer.")
    phone: str | None = Field(None, description="The phone number of the issuer.")
    website: str | None = Field(None, description="The website of the issuer.")


class BillTo(BaseModel):
    name: str | None = Field(None, description="The name of the entity being billed.")
    tax_id: str | None = Field(None, description="Tax ID of the billed entity.")
    address: str | None = Field(None, description="The billing address.")
    email: str | None = Field(None, description="The email address of the billing entity.")
    account_number: str | None = Field(None, description="Customer or account number at the provider.")


class ShippingInformation(BaseModel):
    recipient: str | None = Field(None, description="The name of the recipient.")
    address: str | None = Field(None, description="The shipping address.")
    method: str | None = Field(None, description="The method of shipping.")
    tracking_number: str | None = Field(None, description="Shipment tracking number.")


class PaymentMethod(BaseModel):
    method: PaymentMethodType | None = Field(None, description="High-level payment method category.")
    name: str | None = Field(None, description="Specific provider or wallet name, e.g., Mercado Pago, Apple Pay, Visa.")
    card_last_four: str | None = Field(None, description="Last 4 digits of the card, used for bank reconciliation.")
    card_brand: str | None = Field(None, description="Card brand: Visa, Mastercard, Amex, etc.")
    transaction_id: str | None = Field(None, description="Transaction or authorization ID.")


class BillingPeriod(BaseModel):
    start: str | None = Field(None, description="Billing period start date, ISO 8601 format (YYYY-MM-DD).")
    end: str | None = Field(None, description="Billing period end date, ISO 8601 format (YYYY-MM-DD).")


class Tax(BaseModel):
    name: str = Field(..., description="Tax name or type, e.g., VAT 21%, GST, IVA.")
    rate: float | None = Field(None, description="Tax rate as a percentage, e.g., 21.0 for 21%.")
    amount: float = Field(..., description="Tax amount in document currency.")


class LineItem(BaseModel):
    description: str = Field(..., description="Description of the item or charge.")
    sku: str | None = Field(None, description="Product code or SKU.")
    quantity: float | None = Field(None, description="Quantity of the item.")
    unit: str | None = Field(None, description="Unit of measure: unit, kg, L, GB, hour, etc.")
    unit_price: float | None = Field(None, description="Price per unit in document currency.")
    discount: float | None = Field(None, description="Discount amount applied to this line item.")
    total: float = Field(..., description="Total amount for this line item in document currency.")
    notes: str | None = Field(None, description="Any notes or comments about this item.")


class ExtractionResult(BaseModel):
    document_type: DocumentType = Field(..., description="The type of document.")
    document_number: str | None = Field(None, description="Unique document identifier: invoice number, receipt number, order ID, etc.")
    date_issued: str | None = Field(None, description="Date the document was issued, ISO 8601 format (YYYY-MM-DD).")
    date_due: str | None = Field(None, description="Payment due date, ISO 8601 format (YYYY-MM-DD). Relevant for invoices.")
    date_paid: str | None = Field(None, description="Date payment was made, ISO 8601 format (YYYY-MM-DD).")
    billing_period: BillingPeriod | None = Field(None, description="Billing period for subscriptions, telco, or utilities.")
    currency: str = Field(..., description="ISO 4217 currency code, e.g., USD, EUR, ARS.")
    issuer: Issuer = Field(..., description="The entity issuing the document.")
    bill_to: BillTo | None = Field(None, description="The entity being billed.")
    shipping_information: ShippingInformation | None = Field(None, description="Shipping details, if applicable.")
    payment_method: PaymentMethod | None = Field(None, description="Payment information.")
    line_items: list[LineItem] = Field(..., description="Individual items or charges on the document.")
    taxes: list[Tax] | None = Field(None, description="Tax breakdown lines.")
    overall_subtotal: float | None = Field(None, description="Pre-tax, pre-discount total.")
    overall_discount: float | None = Field(None, description="Total discount applied.")
    overall_tax: float | None = Field(None, description="Total tax amount.")
    overall_total: float = Field(..., description="Final total after taxes and discounts.")
    overall_amount_paid: float | None = Field(None, description="Amount actually paid.")
    outstanding_balance: float | None = Field(None, description="Remaining amount due, if any.")
    tags: list[str] | None = Field(None, description="Free-form hints inferred from the document, e.g., subscription, monthly, recurring.")
    notes: str | None = Field(None, description="Any additional remarks or terms on the document.")