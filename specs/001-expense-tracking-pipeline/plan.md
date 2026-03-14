# Implementation Plan: Expense Tracking Pipeline

**Branch**: `001-expense-tracking-pipeline` | **Date**: 2026-03-14 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-expense-tracking-pipeline/spec.md`

---

## Summary

Build the MVP expense tracking pipeline: (P1) extract structured financial data from PDF/image
documents using the existing ADK/Gemini agent; (P2) store results in GCS + BigQuery for direct
querying; (P3) support issuer-specific extraction strategies (e.g. Claro) selected automatically
by issuer name. The pipeline is triggered by GCS file uploads via Eventarc + Pub/Sub → Cloud Run.
All monetary values use `Decimal`/NUMERIC. Infrastructure is managed via Terraform.

---

## Technical Context

**Language/Version**: Python 3.14 (latest stable)
**Primary Dependencies**: google-adk, pydantic>=2, google-cloud-bigquery, google-cloud-storage,
  pytest, pytest-asyncio, pytest-mock
**Storage**: GCS (document input), BigQuery (extraction results — dataset `expense_tracking`,
  table `extractions`)
**Testing**: pytest — unit tests + black-box tests with mocked Gemini; integration tests behind
  `--integration` flag
**Target Platform**: Cloud Run (Linux, amd64), triggered via Eventarc + Pub/Sub
**Project Type**: Event-driven pipeline service
**Performance Goals**: Extraction + storage completed within 60 seconds of GCS upload (SC-001)
**Constraints**: Single-tenant; no HTTP API in MVP (FastAPI deferred to US6 review UI);
  no access control in MVP
**Scale/Scope**: Personal use; ~50 documents/day maximum

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | Gate | Status |
|-----------|------|--------|
| I. Schema-First Extraction | Pydantic models defined before pipeline code | ✅ `model.py` exists; monetary fields defined as `Decimal` from the start |
| II. Structured Output Only | No raw dict in pipeline; Gemini returns validated Pydantic | ✅ Controlled generation with `response_schema` |
| III. Cloud-Native by Design | GCS trigger, BigQuery output, Vertex AI inference | ✅ All three present in design |
| IV. Fault Tolerance | Failed extractions stored with error context; no crashes | ✅ `status=failed` records written; pipeline returns 200 to Pub/Sub |
| V. Simplicity First | No premature abstractions; no review UI yet | ✅ No FastAPI in MVP; strategy registry is a plain dict |
| VI. Testing Discipline | pytest unit + black-box tests required | ✅ Test structure defined; `tests/unit/` and `tests/blackbox/` |
| VII. Infrastructure as Code | All GCP resources in Terraform | ✅ `infra/` module covers GCS, BigQuery, Pub/Sub, Eventarc, IAM |

**Violations requiring justification**: None.

---

## Project Structure

### Documentation (this feature)

```text
specs/001-expense-tracking-pipeline/
├── plan.md              ← this file
├── research.md          ← Phase 0: design decisions
├── data-model.md        ← Phase 1: entity definitions + BQ schema
├── quickstart.md        ← Phase 1: validation guide
├── contracts/
│   ├── gcs-event.md     ← GCS ingestion trigger contract
│   └── bigquery-schema.md ← BigQuery write contract + query examples
└── tasks.md             ← Phase 2 (/speckit.tasks — not yet created)
```

### Source Code (repository root)

```text
pdf_data_extraction_agent/
├── __init__.py
├── agent.py                  # existing ADK agent definition
├── model.py                  # existing Pydantic models — Decimal migration required
├── pipeline/                 # NEW
│   ├── __init__.py
│   ├── handler.py            # Cloud Run entry point: receives Pub/Sub, orchestrates pipeline
│   ├── extract.py            # invokes ADK Runner programmatically
│   └── store.py              # BigQuery writer (ExtractionRecord → BQ row)
├── extractors/               # NEW
│   ├── __init__.py
│   ├── base.py               # ExtractionStrategy dataclass
│   ├── generic.py            # default extraction strategy
│   └── registry.py           # issuer name pattern → ExtractionStrategy dict
└── .env / .env.example

tests/
├── conftest.py               # shared fixtures (sample files, mock Gemini responses)
├── unit/
│   ├── test_model.py         # Decimal field validation, enum values, null handling
│   ├── test_registry.py      # strategy lookup: exact match, partial, case-insensitive, fallback
│   └── test_store.py         # BQ row serialization: Decimal → NUMERIC string, STRUCT layout
└── blackbox/
    ├── fixtures/
    │   ├── sample_invoice.pdf       # generic invoice fixture
    │   └── claro_factura.pdf        # Claro-specific fixture for P3
    └── test_extraction.py           # full tool call with mocked Gemini; assert output shape

infra/
├── main.tf                   # provider + backend config
├── variables.tf              # project_id, region, environment
├── outputs.tf                # bucket name, BQ dataset, service URL
├── gcs.tf                    # ingestion bucket + Pub/Sub notification
├── bigquery.tf               # expense_tracking dataset + extractions table (NUMERIC schema)
├── pubsub.tf                 # topic + push subscription to Cloud Run
├── eventarc.tf               # GCS → Pub/Sub trigger
└── iam.tf                    # service account + least-privilege bindings
```

**Structure Decision**: Single-project layout extending the existing ADK agent package.
New code is organized into `pipeline/` (orchestration + storage) and `extractors/`
(strategy pattern). Infrastructure is isolated in `infra/` as a standalone Terraform root module.

---

## Complexity Tracking

No constitution violations requiring justification.

---

## Phase 0: Research Summary

See [research.md](research.md) for full details. Key decisions:

| Decision | Choice |
|----------|--------|
| GCS trigger | Eventarc + Pub/Sub + Cloud Run |
| ADK invocation | In-process `Runner` API (not HTTP server) |
| BigQuery schema | STRUCT/RECORD + ARRAY<STRUCT>; monetary fields = NUMERIC |
| pytest strategy | Mock Gemini with `unittest.mock`; black-box tests with fixture files |
| Strategy registry | Plain Python dict with case-insensitive substring matching |

---

## Phase 1: Design Artifacts

- [data-model.md](data-model.md) — entity definitions, `Decimal` migration notes, BQ schema
- [contracts/gcs-event.md](contracts/gcs-event.md) — Pub/Sub event contract, supported types
- [contracts/bigquery-schema.md](contracts/bigquery-schema.md) — write contract, row shape, queries
- [quickstart.md](quickstart.md) — end-to-end validation guide (infra → deploy → verify)

---

## Post-Design Constitution Check

All principles remain satisfied after design. Monetary fields in `model.py` are defined as
`Decimal` from the outset — no migration needed.