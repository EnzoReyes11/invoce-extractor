# Quickstart: Expense Tracking Pipeline (MVP)

**Feature**: 001-expense-tracking-pipeline
**Date**: 2026-03-14

This guide validates the MVP end-to-end: upload a file → extraction runs → record appears in
BigQuery.

---

## Prerequisites

- Python 3.14, `uv` installed
- GCP project with Vertex AI, GCS, BigQuery, Cloud Run, Eventarc APIs enabled
- `gcloud` CLI authenticated (`gcloud auth application-default login`)
- Terraform installed (latest stable)
- Environment variables configured (see `.env.example`)

---

## Step 1: Set Up Infrastructure

```bash
cd infra/
terraform init
terraform plan -var="project_id=YOUR_PROJECT" -var="region=us-central1"
terraform apply
```

This creates:
- GCS bucket `expense-tracking-documents`
- BigQuery dataset `expense_tracking` with table `extractions`
- Pub/Sub topic + subscription
- Eventarc trigger: GCS finalize → Pub/Sub → Cloud Run
- IAM service account with least-privilege bindings

---

## Step 2: Install Dependencies

```bash
cd pdf_data_extraction_agent/
uv sync
```

---

## Step 3: Configure Environment

```bash
cp .env.example .env
# Edit .env:
# GOOGLE_CLOUD_PROJECT=your-project-id
# GOOGLE_CLOUD_LOCATION=us-central1
# MODEL_ID=gemini-2.5-flash
# GOOGLE_GENAI_USE_VERTEXAI=true
# BQ_DATASET=expense_tracking
# BQ_TABLE=extractions
# GCS_BUCKET=expense-tracking-documents
```

---

## Step 4: Run Tests

```bash
uv run pytest tests/ -v
# To also run integration tests (calls real Gemini API):
uv run pytest tests/ -v --integration
```

All tests MUST pass before deploying.

---

## Step 5: Test Extraction Locally

```bash
uv run adk web
```

Open `http://localhost:8000`, upload a sample invoice PDF, and verify the extracted JSON
matches the document. Confirm:
- `document_type` uses locale-specific value (e.g. "Factura", not "Invoice")
- All monetary fields are present as decimal strings
- `issuer.name` is populated

---

## Step 6: Deploy to Cloud Run

```bash
gcloud run deploy expense-pipeline \
  --source . \
  --region us-central1 \
  --service-account expense-pipeline@YOUR_PROJECT.iam.gserviceaccount.com \
  --no-allow-unauthenticated
```

---

## Step 7: Validate End-to-End

Upload a test file to the GCS bucket:

```bash
gsutil cp tests/fixtures/sample_invoice.pdf \
  gs://expense-tracking-documents/invoices/test_$(date +%s).pdf
```

Within 60 seconds, verify the record appears in BigQuery:

```sql
SELECT id, status, result.issuer.name, result.overall_total, extracted_at
FROM `YOUR_PROJECT.expense_tracking.extractions`
ORDER BY extracted_at DESC
LIMIT 5;
```

**Expected**: One new row with `status = success` or `partial`, correct issuer name, and
`overall_total` as a NUMERIC value.

---

## Step 8: Test Adaptive Extraction (P3)

Upload a Claro invoice:

```bash
gsutil cp tests/fixtures/claro_factura.pdf \
  gs://expense-tracking-documents/invoices/claro_test.pdf
```

Verify in BigQuery:
- `strategy_used = 'claro'` (not `'generic'`)
- Line items are correctly separated (not merged into a single item)

---

## Troubleshooting

| Symptom | Check |
|---------|-------|
| No row in BigQuery after upload | Cloud Run logs: `gcloud run logs read expense-pipeline` |
| `status = failed` | Query `error_message` and `raw_gemini_response` columns |
| `strategy_used = generic` for Claro | Check issuer name in `result.issuer.name`; update pattern in registry |
| Terraform apply fails | Check IAM permissions and enabled APIs |