# Tasks: Expense Tracking Pipeline

**Input**: Design documents from `/specs/001-expense-tracking-pipeline/`
**Prerequisites**: plan.md ✅ spec.md ✅ research.md ✅ data-model.md ✅ contracts/ ✅ quickstart.md ✅

**MVP Scope**: P1 (Document Data Extraction) + P2 (Storage to BigQuery) + P3 (Adaptive Extraction)
**Deferred**: US4–US7 (cleaning pipeline, reports, review UI, email ingestion)

---

## Phase 1: Setup

**Purpose**: Repository structure, tooling, and configuration before any feature code.

- [ ] T001 Create directory structure: `pdf_data_extraction_agent/pipeline/`, `pdf_data_extraction_agent/extractors/`, `tests/unit/`, `tests/blackbox/fixtures/`, `infra/`
- [ ] T002 [P] Add pytest, pytest-asyncio, pytest-mock to dev dependencies in `pdf_data_extraction_agent/pyproject.toml` via `uv add --dev pytest pytest-asyncio pytest-mock`
- [ ] T003 [P] Create `tests/conftest.py` with shared fixtures: mock Gemini response factory, sample file paths
- [ ] T004 [P] Create `tests/unit/__init__.py` and `tests/blackbox/__init__.py`
- [ ] T005 [P] Add `pytest.ini` or `[tool.pytest.ini_options]` section to `pyproject.toml` (asyncio_mode=auto, markers: integration)
- [ ] T006 Copy a real PDF invoice and a Claro invoice into `tests/blackbox/fixtures/` as `sample_invoice.pdf` and `claro_factura.pdf`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure all user stories depend on. No user story work begins until this phase is complete.

**⚠️ CRITICAL**: Complete and verify this phase before starting Phase 3.

### Decimal Fields (model.py)

- [ ] T007 In `pdf_data_extraction_agent/model.py`, define all monetary fields as `Decimal` (not `float`): `overall_total`, `overall_subtotal`, `overall_discount`, `overall_tax`, `overall_amount_paid`, `outstanding_balance`, `LineItem.unit_price`, `LineItem.discount`, `LineItem.total`, `Tax.rate`, `Tax.amount`; quantity fields (`LineItem.quantity`) remain `float`
- [ ] T008 Add `model_config = ConfigDict(arbitrary_types_allowed=True)` to `ExtractionResult`, `LineItem`, and `Tax` in `pdf_data_extraction_agent/model.py`
- [ ] T009 [P] Write unit tests in `tests/unit/test_model.py`: validate Decimal fields parse from string and numeric literals, confirm `DocumentType` enum preserves locale values (Factura, Boleta, Recibo)

### ExtractionRecord Model

- [ ] T010 Create `pdf_data_extraction_agent/pipeline/__init__.py` (empty)
- [ ] T011 Create `ExtractionStatus` enum and `ExtractionRecord` Pydantic model in `pdf_data_extraction_agent/pipeline/models.py` (fields: id, source_file_uri, source_format, status, strategy_used, result, error_message, raw_gemini_response, extracted_at)

### Terraform Infrastructure

- [ ] T012 Create `infra/main.tf`: Terraform provider block (google), backend config (GCS), required_version constraint (latest stable)
- [ ] T013 Create `infra/variables.tf`: variables for project_id, region, environment, bucket_name, bq_dataset
- [ ] T014 Create `infra/outputs.tf`: output values for bucket_name, bq_dataset_id, pubsub_topic, cloud_run_url
- [ ] T015 Create `infra/gcs.tf`: GCS bucket `expense-tracking-documents` with versioning, lifecycle rules; Pub/Sub notification on OBJECT_FINALIZE
- [ ] T016 Create `infra/pubsub.tf`: Pub/Sub topic `expense-pipeline-events` and push subscription pointing to Cloud Run service URL
- [ ] T017 Create `infra/bigquery.tf`: dataset `expense_tracking`; table `extractions` with full schema from `data-model.md` — all monetary fields as NUMERIC, line_items and taxes as REPEATED RECORD
- [ ] T018 Create `infra/iam.tf`: service account `expense-pipeline`; IAM bindings for GCS object viewer, BigQuery data editor, Vertex AI user
- [ ] T019 Run `terraform init` and `terraform validate` in `infra/` to confirm no syntax errors

**Checkpoint**: Foundation complete — model.py has Decimal fields, ExtractionRecord exists, Terraform validates. User story phases can now begin.

---

## Phase 3: User Story 1 — Document Data Extraction (P1)

**Goal**: Upload a document → ADK agent extracts structured data → result is available as an ExtractionRecord.

**Independent Test**: Call `extract.run_extraction(gcs_uri, source_format)` with a mocked Gemini response. Assert the returned ExtractionRecord has the correct status, strategy_used="generic", and result fields match the mock.

### Black-box Tests for US1

- [ ] T020 [P] [US1] Write black-box test in `tests/blackbox/test_extraction.py`: mock `google.genai.Client` to return a valid invoice JSON; call full extraction flow; assert ExtractionRecord.status == "success" and result.document_type is preserved as locale value
- [ ] T021 [P] [US1] Write black-box test for partial extraction: mock Gemini returning valid JSON with some null fields; assert status == "partial" and record is not failed
- [ ] T022 [P] [US1] Write black-box test for Gemini error / invalid JSON: assert status == "failed", error_message populated, raw_gemini_response stored

### Implementation for US1

- [ ] T023 [US1] Create `pdf_data_extraction_agent/extractors/__init__.py` and `pdf_data_extraction_agent/extractors/base.py`: `ExtractionStrategy` dataclass with fields `name`, `issuer_pattern`, `prompt_override`
- [ ] T024 [US1] Create `pdf_data_extraction_agent/extractors/generic.py`: `GenericExtractor` — builds the extraction prompt from `ExtractionResult` schema and calls ADK agent tools (`get_pdf_from_artifact`, `generate_data_from_pdf_and_schema`)
- [ ] T025 [US1] Create `pdf_data_extraction_agent/pipeline/extract.py`: `run_extraction(source_file_uri: str, source_format: str, strategy: ExtractionStrategy) -> ExtractionRecord` — downloads file from GCS, invokes ADK Runner, validates Pydantic response, returns ExtractionRecord (success/partial/failed)
- [ ] T026 [US1] Add error handling in `pdf_data_extraction_agent/pipeline/extract.py`: catch Pydantic ValidationError → status=failed; catch Gemini API error → status=failed; always return ExtractionRecord, never raise
- [ ] T027 [P] [US1] Write unit tests in `tests/unit/test_extract.py`: test status assignment logic, error path returns correct ExtractionRecord shape

**Checkpoint**: US1 independently testable — `uv run pytest tests/blackbox/test_extraction.py -v` passes with mocked Gemini.

---

## Phase 4: User Story 2 — Extracted Data Storage (P2)

**Goal**: ExtractionRecord written to BigQuery; technical user can query results.

**Independent Test**: Call `store.write_record(record)` with a sample ExtractionRecord (success and failed). Query BigQuery (or assert the mock insert call) and verify the row contains the correct NUMERIC values and STRUCT layout.

### Black-box Tests for US2

- [ ] T028 [P] [US2] Write unit test in `tests/unit/test_store.py`: serialize a success ExtractionRecord to BQ row dict; assert Decimal fields are converted to strings (BQ NUMERIC wire format), STRUCT fields are nested dicts, ARRAY fields are lists of dicts
- [ ] T029 [P] [US2] Write unit test for failed ExtractionRecord: assert row has status="failed", result=None or null, error_message populated
- [ ] T030 [P] [US2] Write black-box test in `tests/blackbox/test_storage.py`: mock `bigquery.Client.insert_rows_json`; call full pipeline (extract → store); assert insert was called once with correct table reference

### Implementation for US2

- [ ] T031 [US2] Create `pdf_data_extraction_agent/pipeline/store.py`: `BigQueryWriter` class — accepts dataset and table config from env; `write_record(record: ExtractionRecord) -> None`; serializes Decimal to string for NUMERIC wire format; handles nested Pydantic models to dict
- [ ] T032 [US2] Add Decimal → string serialization helper in `pdf_data_extraction_agent/pipeline/store.py`: recursively convert all `Decimal` values to strings before BQ insert (BigQuery NUMERIC accepts string format)
- [ ] T033 [US2] Create `pdf_data_extraction_agent/pipeline/handler.py`: Cloud Run Pub/Sub push handler — parses Pub/Sub envelope, extracts GCS bucket/name, validates MIME type, calls `run_extraction()` then `write_record()`, returns HTTP 200 on success or stored failure, 400 on unsupported format, 500 on transient error
- [ ] T034 [US2] Add environment variable loading in `pdf_data_extraction_agent/pipeline/handler.py`: `BQ_DATASET`, `BQ_TABLE`, `GCS_BUCKET` from env; raise clear error on missing required vars at startup

**Checkpoint**: US1 + US2 independently testable — `uv run pytest tests/ -v` passes; `terraform apply` creates infrastructure; uploading a file to GCS bucket produces a BigQuery row.

---

## Phase 5: User Story 3 — Adaptive Extraction (P3)

**Goal**: Documents from known issuers (e.g. Claro) automatically use a custom extraction strategy; strategy name is recorded in BigQuery.

**Independent Test**: Register a "claro" strategy. Call `registry.get_strategy("Claro Argentina")`. Assert returns the Claro strategy (not generic). Run extraction on `claro_factura.pdf` fixture with mocked Gemini; assert `strategy_used == "claro"` in the ExtractionRecord.

### Tests for US3

- [ ] T035 [P] [US3] Write unit tests in `tests/unit/test_registry.py`: exact match, case-insensitive match ("CLARO" → "claro"), partial match ("Claro Argentina" → "claro"), no match → generic fallback, empty issuer name → generic fallback
- [ ] T036 [P] [US3] Write black-box test in `tests/blackbox/test_extraction.py`: use claro_factura.pdf fixture with mocked Gemini; assert ExtractionRecord.strategy_used == "claro"

### Implementation for US3

- [ ] T037 [US3] Create `pdf_data_extraction_agent/extractors/registry.py`: `STRATEGY_REGISTRY: dict[str, ExtractionStrategy]` — initial entry for "claro"; `get_strategy(issuer_name: str | None) -> ExtractionStrategy` — case-insensitive substring lookup with generic fallback
- [ ] T038 [US3] Create `pdf_data_extraction_agent/extractors/claro.py`: Claro-specific `ExtractionStrategy` with `issuer_pattern="claro"` and a prompt override that instructs the model to treat each service/product line as a separate `LineItem`
- [ ] T039 [US3] Update `pdf_data_extraction_agent/pipeline/extract.py`: after a first-pass extraction determines the issuer name, look up the strategy via `get_strategy(issuer_name)` and re-run extraction with the issuer-specific strategy if it differs from generic
- [ ] T040 [US3] Ensure `strategy_used` field in ExtractionRecord is set to the strategy name (not "generic") when a custom strategy is applied in `pdf_data_extraction_agent/pipeline/extract.py`

**Checkpoint**: All three user stories testable independently — `uv run pytest tests/ -v` passes. Upload a Claro invoice to GCS and verify `strategy_used = 'claro'` appears in BigQuery.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final hardening, documentation, and end-to-end validation.

- [ ] T041 [P] Add `__version__` and package metadata to `pdf_data_extraction_agent/__init__.py`
- [ ] T042 [P] Create or update `pdf_data_extraction_agent/.env.example` with all required env vars: `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`, `MODEL_ID`, `GOOGLE_GENAI_USE_VERTEXAI`, `BQ_DATASET`, `BQ_TABLE`, `GCS_BUCKET`
- [ ] T043 [P] Update `README.md` with MVP architecture overview, quickstart reference, and link to `specs/001-expense-tracking-pipeline/quickstart.md`
- [ ] T044 Run full end-to-end validation per `specs/001-expense-tracking-pipeline/quickstart.md`: terraform apply → deploy → upload sample_invoice.pdf → verify BigQuery row
- [ ] T045 Run full end-to-end validation with Claro fixture: verify `strategy_used = 'claro'` in BigQuery
- [ ] T046 [P] Add `Dockerfile` or Cloud Run build configuration if not handled by `gcloud run deploy --source`
- [ ] T047 Record session findings (accuracy observations, any extraction edge cases) in `pdf_data_extraction_agent/WORKLOG.md` with date 2026-03-14

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 — **BLOCKS all user stories**
- **Phase 3 (US1)**: Depends on Phase 2 (ExtractionRecord model, Decimal fields)
- **Phase 4 (US2)**: Depends on Phase 3 (needs ExtractionRecord from extraction)
- **Phase 5 (US3)**: Depends on Phase 3 (extends extraction flow; independent of Phase 4)
- **Phase 6 (Polish)**: Depends on Phase 4 + Phase 5

### User Story Dependencies

- **US1**: Depends on Foundational (T007–T011 complete)
- **US2**: Depends on US1 (writes ExtractionRecord produced by extraction)
- **US3**: Depends on US1 (extends extraction with strategy selection); can run in parallel with US2

### Within Each User Story

- Tests before implementation (T020–T022 before T023–T027)
- Models/base before services (T023–T024 before T025–T026)
- Extraction before storage (Phase 3 before Phase 4)

### Parallel Opportunities

- All Phase 1 tasks marked [P] can run in parallel
- T009 (model tests), T010–T011 (ExtractionRecord), T012–T018 (Terraform) can all run in parallel within Phase 2
- T020, T021, T022 (US1 tests) can run in parallel
- T028, T029, T030 (US2 tests) can run in parallel
- T035, T036 (US3 tests) can run in parallel
- US3 (Phase 5) can start as soon as US1 (Phase 3) is complete, in parallel with US2 (Phase 4)

---

## Parallel Execution Examples

### Phase 2: Foundational

```
Parallel group A (can all start simultaneously):
  T007–T009: Decimal migration + model tests
  T010–T011: ExtractionRecord model
  T012–T019: Terraform infrastructure

Sequence within Terraform: T012 → T013 → T014 → T015 → T016 → T017 → T018 → T019
```

### Phase 3: US1

```
Parallel group A (tests first):
  T020: black-box test — success path
  T021: black-box test — partial path
  T022: black-box test — error path

Then sequential implementation:
  T023 (base) → T024 (generic extractor) → T025 (extract.py) → T026 (error handling)
  T027: unit tests can run in parallel with T025–T026
```

### Phase 4 + Phase 5 (run in parallel after Phase 3)

```
Phase 4 (US2): T028–T029–T030 (parallel tests) → T031 → T032 → T033 → T034
Phase 5 (US3): T035–T036 (parallel tests) → T037 → T038 → T039 → T040
```

---

## Implementation Strategy

### MVP First (US1 only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks everything)
3. Complete Phase 3: US1
4. **STOP and VALIDATE**: `uv run pytest tests/blackbox/test_extraction.py -v` passes
5. Manual test via `uv run adk web`

### Incremental Delivery

1. Setup + Foundational → commit
2. US1 (extraction) → test → commit
3. US2 (storage) → `terraform apply` → upload test file → verify BigQuery → commit
4. US3 (adaptive) → test with Claro fixture → verify BigQuery `strategy_used` → commit
5. Polish → end-to-end quickstart validation → commit

---

## Notes

- `[P]` = different files, no incomplete dependencies — safe to parallelize
- `[USn]` maps each task to the user story it delivers
- All monetary Decimal fields require string conversion before BigQuery insert
- `strategy_used` must always be set — never null in BigQuery
- WORKLOG.md must be updated at end of each session (Phase 6, T047)
- Integration tests (real Gemini API): run with `uv run pytest --integration -v`
