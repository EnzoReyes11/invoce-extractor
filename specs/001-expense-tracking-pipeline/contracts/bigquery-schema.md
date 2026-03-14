# Contract: BigQuery Output Schema

**Direction**: Pipeline → BigQuery
**Dataset**: `expense_tracking`
**Table**: `extractions`

---

## Write Contract

**When**: After every extraction attempt (success, partial, or failed).
**Method**: `google-cloud-bigquery` streaming insert (`insert_rows_json`).
**Guarantee**: Every processed file MUST produce exactly one row in BigQuery.
  Failures MUST be recorded — rows with `status = failed` are valid writes.

## Row Shape

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "source_file_uri": "gs://expense-tracking-documents/invoices/claro_march.pdf",
  "source_format": "application/pdf",
  "status": "success",
  "strategy_used": "claro",
  "extracted_at": "2026-03-14T10:22:05Z",
  "error_message": null,
  "raw_gemini_response": null,
  "result": {
    "document_type": "Factura",
    "document_number": "0001-00045123",
    "date_issued": "2026-03-01",
    "currency": "ARS",
    "overall_total": "15230.50",
    "issuer": {
      "name": "Claro Argentina",
      "tax_id": "30-12345678-9"
    },
    "line_items": [
      {
        "description": "Plan Claro Control 500",
        "quantity": 1.0,
        "unit_price": "12000.00",
        "total": "12000.00"
      }
    ],
    "taxes": [
      {
        "name": "IVA 21%",
        "rate": "21.000000000",
        "amount": "2520.00"
      }
    ]
  }
}
```

## Type Mapping

| Pydantic Type | BigQuery Type | Notes |
|---------------|---------------|-------|
| str | STRING | |
| Decimal (monetary) | NUMERIC | All monetary amounts and tax rates |
| float (quantity) | FLOAT64 | Physical measurements only |
| datetime | TIMESTAMP | UTC, ISO 8601 |
| date str (ISO) | DATE | Stored as DATE column |
| Enum value | STRING | The `.value` string, e.g. "Factura" |
| BaseModel | RECORD | STRUCT |
| list[BaseModel] | RECORD REPEATED | ARRAY<STRUCT> |
| None / missing | null | All nullable fields |

## Query Examples

```sql
-- Monthly expense total by currency
SELECT
  DATE_TRUNC(result.date_issued, MONTH) AS month,
  result.currency,
  SUM(result.overall_total) AS total
FROM `expense_tracking.extractions`
WHERE status IN ('success', 'partial')
GROUP BY 1, 2
ORDER BY 1 DESC;

-- All line items for a specific issuer
SELECT
  id,
  result.issuer.name,
  li.description,
  li.total
FROM `expense_tracking.extractions`,
  UNNEST(result.line_items) AS li
WHERE LOWER(result.issuer.name) LIKE '%claro%';

-- Failed extractions for retry
SELECT id, source_file_uri, error_message, extracted_at
FROM `expense_tracking.extractions`
WHERE status = 'failed'
ORDER BY extracted_at DESC;
```