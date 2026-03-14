# Data Model: Expense Tracking Pipeline

**Feature**: 001-expense-tracking-pipeline
**Date**: 2026-03-14

---

## Note on Financial Precision

All monetary amounts and tax rates MUST use `Decimal` in Python (Pydantic fields) and `NUMERIC`
in BigQuery. `float` is not acceptable for financial values due to IEEE 754 rounding errors.

- **Python / Pydantic**: `Decimal` (from `decimal` stdlib)
- **BigQuery**: `NUMERIC` (29 digits precision, 9 decimal places — sufficient for any currency)
- **Quantity fields** (e.g., `line_items.quantity`) use `float` / `FLOAT64` as they represent
  physical measurements (liters, kg, hours), not monetary values.
- **Tax rate** (`taxes.rate`) uses `NUMERIC` because it feeds into monetary calculations.

---

## Existing Models (pdf_data_extraction_agent/model.py)

These models are the canonical extraction schema. The `float` → `Decimal` migration for
monetary fields is a required task for this feature.

### ExtractionResult (root output model)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| document_type | DocumentType (enum) | ✅ | Locale-specific: Factura, Invoice, Receipt, etc. |
| document_number | str \| None | — | Invoice/receipt number |
| date_issued | str \| None | — | ISO 8601 date |
| date_due | str \| None | — | Payment due date |
| date_paid | str \| None | — | Payment date |
| billing_period | BillingPeriod \| None | — | Subscription/utility period |
| currency | str | ✅ | ISO 4217 code (USD, ARS, EUR) |
| issuer | Issuer | ✅ | Entity issuing the document |
| bill_to | BillTo \| None | — | Billed entity |
| shipping_information | ShippingInformation \| None | — | Shipping details |
| payment_method | PaymentMethod \| None | — | Payment info |
| line_items | list[LineItem] | ✅ | Individual charges |
| taxes | list[Tax] \| None | — | Tax breakdown |
| overall_subtotal | **Decimal** \| None | — | Pre-tax total |
| overall_discount | **Decimal** \| None | — | Total discount |
| overall_tax | **Decimal** \| None | — | Total tax |
| overall_total | **Decimal** | ✅ | Final total |
| overall_amount_paid | **Decimal** \| None | — | Amount paid |
| outstanding_balance | **Decimal** \| None | — | Remaining due |
| tags | list[str] \| None | — | Inferred hints |
| notes | str \| None | — | Additional remarks |

### LineItem (nested in ExtractionResult)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| description | str | ✅ | Item description |
| sku | str \| None | — | Product code |
| quantity | float \| None | — | Physical quantity — float intentional |
| unit | str \| None | — | Unit of measure (kg, L, hours) |
| unit_price | **Decimal** \| None | — | Price per unit |
| discount | **Decimal** \| None | — | Discount amount |
| total | **Decimal** | ✅ | Line total |
| notes | str \| None | — | Notes |

### Tax (nested in ExtractionResult)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| name | str | ✅ | Tax name (VAT 21%, IVA, GST) |
| rate | **Decimal** \| None | — | Rate as percentage (e.g. 21.0) |
| amount | **Decimal** | ✅ | Tax amount |

---

## New Models (pipeline layer)

### ExtractionStatus

```
success   — all required fields extracted and valid
partial   — some optional fields null; Pydantic model valid
failed    — Pydantic validation failed or Gemini error
```

### ExtractionRecord

Envelope wrapping one extraction result for storage and tracking.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | str (UUID) | ✅ | Unique record identifier |
| source_file_uri | str | ✅ | GCS URI of the source document |
| source_format | str | ✅ | MIME type: application/pdf, image/jpeg, etc. |
| status | ExtractionStatus | ✅ | success / partial / failed |
| strategy_used | str | ✅ | "generic" or issuer name (e.g. "claro") |
| result | ExtractionResult \| None | — | Null only when status = failed |
| error_message | str \| None | — | Human-readable error |
| raw_gemini_response | str \| None | — | Raw response for debugging (truncated 10KB) |
| extracted_at | datetime | ✅ | UTC timestamp |

### ExtractionStrategy

| Field | Type | Description |
|-------|------|-------------|
| name | str | Strategy identifier (e.g. "claro") |
| issuer_pattern | str | Case-insensitive substring matched against issuer name |
| prompt_override | str | Replacement or appended prompt for this issuer |

---

## BigQuery Schema

**Dataset**: `expense_tracking`
**Table**: `extractions`

| Column | BQ Type | Mode | Notes |
|--------|---------|------|-------|
| id | STRING | REQUIRED | UUID |
| source_file_uri | STRING | REQUIRED | gs://bucket/path |
| source_format | STRING | REQUIRED | MIME type |
| status | STRING | REQUIRED | success/partial/failed |
| strategy_used | STRING | REQUIRED | |
| extracted_at | TIMESTAMP | REQUIRED | UTC |
| error_message | STRING | NULLABLE | |
| raw_gemini_response | STRING | NULLABLE | Truncated to 10KB |
| result | RECORD | NULLABLE | |
| result.document_type | STRING | NULLABLE | Locale-specific value preserved |
| result.document_number | STRING | NULLABLE | |
| result.date_issued | DATE | NULLABLE | |
| result.date_due | DATE | NULLABLE | |
| result.date_paid | DATE | NULLABLE | |
| result.currency | STRING | NULLABLE | ISO 4217 |
| result.overall_total | **NUMERIC** | NULLABLE | |
| result.overall_subtotal | **NUMERIC** | NULLABLE | |
| result.overall_discount | **NUMERIC** | NULLABLE | |
| result.overall_tax | **NUMERIC** | NULLABLE | |
| result.overall_amount_paid | **NUMERIC** | NULLABLE | |
| result.outstanding_balance | **NUMERIC** | NULLABLE | |
| result.tags | STRING | REPEATED | |
| result.notes | STRING | NULLABLE | |
| result.issuer | RECORD | NULLABLE | |
| result.issuer.name | STRING | NULLABLE | |
| result.issuer.tax_id | STRING | NULLABLE | |
| result.issuer.address | STRING | NULLABLE | |
| result.issuer.email | STRING | NULLABLE | |
| result.issuer.phone | STRING | NULLABLE | |
| result.issuer.website | STRING | NULLABLE | |
| result.bill_to | RECORD | NULLABLE | |
| result.bill_to.name | STRING | NULLABLE | |
| result.bill_to.tax_id | STRING | NULLABLE | |
| result.bill_to.address | STRING | NULLABLE | |
| result.bill_to.email | STRING | NULLABLE | |
| result.bill_to.account_number | STRING | NULLABLE | |
| result.line_items | RECORD | REPEATED | |
| result.line_items.description | STRING | NULLABLE | |
| result.line_items.sku | STRING | NULLABLE | |
| result.line_items.quantity | FLOAT64 | NULLABLE | Physical qty — not monetary |
| result.line_items.unit | STRING | NULLABLE | |
| result.line_items.unit_price | **NUMERIC** | NULLABLE | |
| result.line_items.discount | **NUMERIC** | NULLABLE | |
| result.line_items.total | **NUMERIC** | NULLABLE | |
| result.line_items.notes | STRING | NULLABLE | |
| result.taxes | RECORD | REPEATED | |
| result.taxes.name | STRING | NULLABLE | |
| result.taxes.rate | **NUMERIC** | NULLABLE | Percentage e.g. 21.000000000 |
| result.taxes.amount | **NUMERIC** | NULLABLE | |
| result.payment_method | RECORD | NULLABLE | |
| result.payment_method.method | STRING | NULLABLE | PaymentMethodType value |
| result.payment_method.name | STRING | NULLABLE | |
| result.payment_method.card_last_four | STRING | NULLABLE | |
| result.payment_method.card_brand | STRING | NULLABLE | |
| result.payment_method.transaction_id | STRING | NULLABLE | |
| result.billing_period | RECORD | NULLABLE | |
| result.billing_period.start | DATE | NULLABLE | |
| result.billing_period.end | DATE | NULLABLE | |

---

## State Transitions

```
[file uploaded to GCS]
        ↓
  GCS event → Cloud Run handler receives Pub/Sub message
        ↓
  ExtractionRecord (transient) created with status pending
        ↓
  ADK Runner invoked → Gemini extraction runs
        ↓
  ┌───────────────────────────────────────────────┐
  │ Pydantic validation passes, all required ✅   │ → status: success
  │ Pydantic validation passes, some null    ⚠️   │ → status: partial
  │ Pydantic validation fails / Gemini error ❌   │ → status: failed
  └───────────────────────────────────────────────┘
        ↓
  ExtractionRecord written to BigQuery (always, even on failure)
```

---

## Issuer Strategy Registry

```
registry: dict[str, ExtractionStrategy]
  key: issuer_pattern (lowercase)
  value: ExtractionStrategy

Lookup:
  detected = result.issuer.name.lower() if result and result.issuer else ""
  for pattern, strategy in registry.items():
    if pattern in detected:
      return strategy
  return GENERIC_STRATEGY

Initial registry:
  "claro" → ExtractionStrategy(name="claro", issuer_pattern="claro", prompt_override="...")
```
