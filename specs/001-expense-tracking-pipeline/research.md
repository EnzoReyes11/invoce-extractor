# Research: Expense Tracking Pipeline

**Feature**: 001-expense-tracking-pipeline
**Date**: 2026-03-14

---

## Decision 1: GCS Event Trigger & Pipeline Entry Point

**Decision**: Eventarc + Pub/Sub + Cloud Run

**Rationale**: GCS bucket emits a `google.cloud.storage.object.v1.finalized` event via Eventarc,
which routes through Pub/Sub to a Cloud Run service. The Cloud Run service acts as the event
handler: it receives the Pub/Sub push message, extracts GCS file metadata, downloads the file,
runs extraction, and writes the result to BigQuery. This pattern provides at-least-once delivery
with automatic retries, decouples ingestion from processing, and fits inside Cloud Run's request
lifecycle.

**Alternatives considered**:
- Cloud Functions: simpler, but harder to manage complex ADK agent lifecycle and 9-minute limit.
- Direct GCS → Cloud Functions notification: limited to 10 concurrent subscriptions per bucket.
- Cloud Scheduler polling: not event-driven, adds latency.

---

## Decision 2: ADK Agent Invocation

**Decision**: Programmatic in-process invocation via the ADK `Runner` API

**Rationale**: For the MVP pipeline (Cloud Run service receiving a GCS event), the ADK agent
is invoked directly in the same process using `google.adk.runners.Runner`. The Cloud Run handler
instantiates the agent's `Runner`, creates a `Session`, sends the file as a message, and reads
the response. This avoids a network hop to a separate ADK server and keeps the deployment simple
(one Cloud Run service, not two). The ADK REST server (`adk web` / `adk api_server`) is used
for interactive development and deferred review-UI use cases, not for the automated pipeline.

**Alternatives considered**:
- HTTP POST to a separately deployed ADK API server: adds a network hop, a second service, and
  extra latency for a fully automated pipeline where no human interaction is needed.
- `adk run` CLI subprocess: not suitable for production invocation from code.

---

## Decision 3: BigQuery Schema for Nested Pydantic Models

**Decision**: Native STRUCT/RECORD columns with ARRAY<STRUCT> for repeated fields

**Rationale**: The `ExtractionResult` Pydantic model has nested `BaseModel` fields (Issuer,
BillTo, PaymentMethod, BillingPeriod) and array fields (list[LineItem], list[Tax]). BigQuery
STRUCT columns map directly to these and remain fully queryable — e.g.,
`WHERE issuer.name = 'Claro'` or `SELECT SUM(li.total) FROM UNNEST(line_items) li`. Storing
as a flat JSON STRING column would lose all query capability. Pydantic's `.model_dump()` output
maps directly to BigQuery's row insert format when the table schema matches the model structure.

**Schema summary**:
- Top-level scalar fields → standard BQ columns (STRING, FLOAT64, DATE, etc.)
- Nested BaseModel fields (Issuer, BillTo, etc.) → STRUCT<...>
- `list[LineItem]` → ARRAY<STRUCT<...>> (REPEATED mode)
- `list[Tax]` → ARRAY<STRUCT<...>> (REPEATED mode)
- Nullable fields → NULLABLE mode; required fields → REQUIRED mode

**Alternatives considered**:
- JSON STRING column: simplest to insert, but not queryable without JSON_EXTRACT.
- Flat/denormalized columns: loses nested structure, painful for optional nested objects.
- Separate normalized tables (Issuer table, LineItem table): over-engineered for single-user
  analytics workload; adds join complexity with no benefit at this scale.

---

## Decision 4: Pytest Black-Box Testing Strategy

**Decision**: Mock Gemini API responses with `unittest.mock`; test full tool function flow with
fixture files; mark real-API tests as `@pytest.mark.integration`

**Rationale**: ADK agent tools are async Python functions that call the Gemini API. Unit tests
mock the `google.genai.Client` using `unittest.mock.patch` and return controlled JSON responses.
Black-box tests call the full tool function chain (load artifact → call Gemini → validate Pydantic
model → return result) with a real fixture PDF, but with Gemini mocked. Integration tests (marked
`@pytest.mark.integration`, skipped by default in CI) call the real Gemini API against known
fixture documents and assert field-level accuracy.

**Test categories**:
1. **Unit**: Individual functions (Pydantic validation, strategy registry lookup, BQ schema gen)
2. **Black-box**: Full tool invocation with fixture files + mocked Gemini; assert output shape
3. **Integration** (optional, `--integration` flag): Real Gemini call; assert key field values

**Required packages**: `pytest`, `pytest-asyncio`, `pytest-mock`

**Alternatives considered**:
- Snapshot testing (store expected JSON, compare): fragile as model evolves.
- llmock server: more realistic HTTP testing, but heavier setup for MVP.
- Real Gemini in all tests: expensive, non-deterministic, slow CI.

---

## Decision 5: Issuer Strategy Registration

**Decision**: Python module with a typed registry dict; partial/case-insensitive matching at
lookup time

**Rationale**: For MVP, a Python dict mapping issuer name patterns to `ExtractionStrategy`
objects (prompt override string) is the simplest approach. The registry lives in
`pdf_data_extraction_agent/extractors/registry.py`. Lookup checks each registered pattern
against the detected issuer name using case-insensitive substring matching. New strategies are
added by editing the registry module — no external config files needed until the number of
issuers justifies it.

**Alternatives considered**:
- YAML config file: more user-editable, but adds a parsing layer and no tooling benefit in MVP.
- Database-backed registry: overkill; strategies are code-level configuration, not runtime data.
- Regex-based matching: more powerful than substring, but substring is sufficient for known
  issuers like "Claro".
