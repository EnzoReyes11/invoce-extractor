# Feature Specification: Expense Tracking Pipeline

**Feature Branch**: `001-expense-tracking-pipeline`
**Created**: 2026-03-14
**Status**: Draft — MVP scope (P1–P3 active; P4–P7 deferred)

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Document Data Extraction (Priority: P1 — Active MVP)

The user provides a document (PDF or image of an invoice, receipt, or similar) to the system.
The system analyzes the document visually and extracts all relevant financial data from it,
presenting the structured result to the user so they can verify the extraction was successful.

**Why this priority**: This is the core value of the product — turning an unstructured document
into clean, structured data. Everything else depends on this working reliably.

**Independent Test**: Provide a sample invoice PDF. Verify that the system returns a structured
record containing the issuer name, document type (in its original locale, e.g. "Factura" not
"Invoice"), date, currency, line items, and total amount.

**Acceptance Scenarios**:

1. **Given** a valid PDF invoice is provided to the system, **When** extraction runs, **Then**
   the system returns a structured record with all available fields populated (issuer, document
   type, date, currency, line items, totals) and missing fields represented as null.
2. **Given** an image file (JPEG/PNG) of a receipt is provided, **When** extraction runs,
   **Then** the system produces a structured record using the same model as for PDFs.
3. **Given** a document identified by the extractor as a "Factura", **When** the result is
   produced, **Then** the document type field retains the value "Factura" and is not relabeled
   as "Invoice" or any other English equivalent.
4. **Given** a document from which extraction partially succeeds (some fields unreadable),
   **When** the result is produced, **Then** successfully extracted fields are present and
   unextractable fields are null — the extraction does not fail entirely.
5. **Given** an unsupported file format (e.g., `.xlsx`), **When** extraction is attempted,
   **Then** the system returns a clear error and does not produce a partial or corrupt record.

---

### User Story 2 — Extracted Data Storage for Analysis (Priority: P2 — Active MVP)

Once a document is extracted, the structured result is stored in a cloud storage location and
in the analytical data warehouse. The technical user can then query and analyze the extracted
data directly.

**Why this priority**: Storing results in a queryable location transforms single extractions
into an ongoing expense record. Duplicate or incorrect records can be identified and removed
manually by the technical user in this initial version.

**Independent Test**: Run extraction on three documents. Verify that three corresponding records
appear in the data warehouse and can be queried (e.g., filter by issuer, sum totals by month).

**Acceptance Scenarios**:

1. **Given** a successful extraction result, **When** storage runs, **Then** the structured
   record is written to the designated storage location and becomes queryable in the data
   warehouse within 60 seconds.
2. **Given** multiple extraction results accumulated over time, **When** the technical user
   queries the data warehouse, **Then** records are filterable by document date, issuer,
   currency, and document type.
3. **Given** a storage failure after successful extraction, **When** the failure occurs,
   **Then** the extracted data is not silently lost — the failure is logged with enough context
   to retry the storage step.
4. **Given** a duplicate record exists (same document extracted twice), **When** the technical
   user identifies it via direct query, **Then** they can remove the duplicate record manually
   from the data warehouse without affecting other records.

---

### User Story 3 — Adaptive Extraction for Non-Standard Documents (Priority: P3 — Active MVP)

When the pipeline encounters a document from an issuer known to produce poor extraction results
(e.g., Claro invoices with complex line-item formats), the system uses a tailored extraction
strategy — such as an issuer-specific prompt — to improve accuracy before storing the result.

**Why this priority**: Some real documents produce reliably wrong extractions with the generic
approach. Having a mechanism to register issuer-specific overrides is necessary to make the
stored data trustworthy enough to analyze, even in the MVP.

**Independent Test**: Upload a Claro invoice. Verify the system identifies the issuer, applies
the Claro-specific extraction strategy, and the resulting line items are correctly separated
compared to running the same document through the generic extractor.

**Acceptance Scenarios**:

1. **Given** a document from an issuer with a registered custom extraction strategy, **When**
   extraction runs, **Then** the custom strategy is selected automatically based on the detected
   issuer name.
2. **Given** a custom extraction strategy produces a result, **When** the record is stored,
   **Then** the metadata includes which strategy was used (generic vs. issuer-specific).
3. **Given** no custom strategy exists for a detected issuer, **When** extraction runs, **Then**
   the system falls back to the generic extractor without failure.
4. **Given** issuer name matching is attempted, **When** names differ by case or contain
   partial matches (e.g., "Claro" vs "Claro Argentina"), **Then** the matching is
   case-insensitive and supports partial matches.

---

## Deferred User Stories *(future releases — kept for planning reference)*

The following stories are out of scope for the current release. They will be prioritized after
the MVP (P1–P3) has been validated as useful.

---

### User Story 4 — Data Cleaning, Deduplication & Reconciliation *(Deferred)*

A cleaning pipeline processes raw extraction records to merge duplicates (e.g., email body +
attachment for the same invoice), reconcile issuer names ("Claro" vs "Claro Argentina"),
categorize documents and line items independently, and flag records requiring manual review.

**Deferred rationale**: The technical user can manage duplicates manually in BigQuery during
the MVP phase. Automated reconciliation logic requires real data patterns to design well.

**Acceptance Scenarios** (for future implementation):

1. **Given** two raw records from the same email representing the same transaction, **When**
   the cleaning pipeline runs, **Then** one canonical record is produced by merging both.
2. **Given** records from "Claro" and "Claro Argentina", **When** reconciliation runs,
   **Then** both are linked to the same canonical issuer identity.
3. **Given** each line item on a document, **When** categorization runs, **Then** each line
   item receives its own category independently from the document-level category.
4. **Given** an issuer name that cannot be automatically reconciled, **When** the pipeline
   runs, **Then** the record is flagged for manual issuer review.

---

### User Story 5 — Monthly Expense Summary & Budget Tracking *(Deferred)*

The user views a monthly summary of expenses grouped by category to understand spending patterns
and support budget planning. Reports are per-currency; the user reconciles cross-currency totals
manually.

**Deferred rationale**: Requires clean, categorized data (US4) and sufficient extraction history
to be meaningful. Will be built once the extraction + storage pipeline is proven.

**Acceptance Scenarios** (for future implementation):

1. **Given** approved records for a month, **When** the user requests a summary, **Then**
   total spend per category is returned, grouped by currency.
2. **Given** no records for a requested month, **When** queried, **Then** an empty result
   with a clear message is returned, not an error.

---

### User Story 6 — User Review & Approval of Extractions *(Deferred)*

The user reviews extracted records via a lightweight web interface, approves correct ones,
rejects incorrect ones with free-text feedback, and only approved records feed into reports.
Unmatched categories are flagged for manual assignment; users can add new categories.

**Deferred rationale**: For the MVP, the technical user inspects results directly in the data
warehouse. A review UI becomes necessary once non-technical users need access or volume makes
manual review impractical.

**Acceptance Scenarios** (for future implementation):

1. **Given** a pending extraction, **When** reviewed, **Then** the user can approve or reject
   it with optional feedback.
2. **Given** a rejection with feedback, **When** stored, **Then** feedback is associated with
   the issuer for future strategy improvements.
3. **Given** an extraction whose category cannot be matched from the predefined taxonomy,
   **When** stored, **Then** the record is flagged and the user is notified to assign a category
   manually or add a new one to the taxonomy.

---

### User Story 7 — Email-Based Document Ingestion *(Deferred)*

The system scans the connected email inbox and processes invoice/receipt data from: file
attachments (PDF/image), inline images in the email body, and structured HTML/text in the body.
Each source is treated as an independent extraction job. Link-based attachment downloads are a
further future iteration requiring a specialized agent.

**Deferred rationale**: GCS-based ingestion is sufficient to validate the pipeline. Email
ingestion adds complexity (auth, body parsing, source deduplication) that is not needed until
the core pipeline is proven.

**Acceptance Scenarios** (for future implementation):

1. **Given** an email with a PDF attachment, **When** scanned, **Then** the attachment is
   processed through the same extraction pipeline as a manually uploaded file.
2. **Given** an email body containing an inline image of a receipt, **When** scanned, **Then**
   the image is submitted as an independent extraction job.
3. **Given** an email body with structured HTML invoice content, **When** scanned, **Then**
   the body content is submitted as an independent extraction job.
4. **Given** an email containing only a download link for the invoice, this case is explicitly
   deferred to a specialized agent in a further future release.

---

### Edge Cases *(MVP scope)*

- A document is submitted twice. Both extractions are stored independently; the technical user
  identifies and removes the duplicate directly in the data warehouse.
- The AI extraction returns a result that fails model validation. The record is stored as
  `failed` with the raw response logged; the pipeline does not crash.
- A storage write fails after a successful extraction. The failure is logged with full context
  so the storage step can be retried without re-running extraction.
- A document in a language other than English or Spanish is submitted. The AI model is expected
  to handle multilingual content; no language selection is required by the user.
- An issuer name partially matches a registered custom strategy (e.g., "Claro Argentina" matches
  "Claro"). The matching MUST be case-insensitive and support partial/prefix matches.

---

## Requirements *(mandatory)*

### Functional Requirements

**Extraction (P1)**

- **FR-001**: System MUST accept PDF and image files (JPEG, PNG) as valid input documents.
- **FR-002**: System MUST extract structured data from each document using the canonical data
  model (issuer, document type, date, currency, line items, totals, and all nested fields).
- **FR-003**: Document types MUST be preserved in their locale-specific form as identified by
  the extractor (e.g., "Factura", "Boleta de Venta", "Recibo"). The system MUST NOT remap
  locale-specific document types to English-language equivalents.
- **FR-004**: Missing or unreadable fields MUST be stored as null values. A partial extraction
  MUST NOT be treated as a total failure.
- **FR-005**: Unsupported file formats MUST produce a clear error record and MUST NOT cause
  partial or corrupt extraction output.

**Storage & Pipeline (P2)**

- **FR-006**: Every extraction result (success, partial, or failed) MUST be written to a
  designated cloud storage location and to the analytical data warehouse.
- **FR-007**: Each stored record MUST include: a unique identifier, the source file reference,
  all extracted fields, the extraction timestamp, and the extraction status
  (`success`, `partial`, `failed`).
- **FR-008**: Stored records MUST be queryable by document date, issuer name, currency, and
  document type.
- **FR-009**: Storage failures MUST be logged with enough context (extraction result, error
  reason) to enable manual retry without repeating the extraction step.
- **FR-010**: Individual records MUST be removable by a technical user without affecting other
  records (to support manual duplicate cleanup).

**Adaptive Extraction (P3)**

- **FR-011**: System MUST support registration of issuer-specific extraction strategies
  (custom prompts) identified by issuer name pattern.
- **FR-012**: When a document's issuer matches a registered strategy, that strategy MUST be
  used automatically in place of the generic extractor.
- **FR-013**: Issuer name matching MUST be case-insensitive and support partial/prefix matches
  (e.g., "Claro" matches "Claro Argentina").
- **FR-014**: Each stored record MUST include metadata identifying which extraction strategy
  was applied (generic or the name of the issuer-specific strategy).
- **FR-015**: When no custom strategy matches, the system MUST fall back to the generic
  extractor without error.

### Key Entities

- **ExtractionRecord**: One processed document. Attributes: unique ID, source file reference,
  extraction status (`success`, `partial`, `failed`), extracted data, extraction strategy used,
  extraction timestamp.
- **ExtractionResult**: Structured data from a document: document type (locale-specific),
  issuer, bill-to, line items, totals, taxes, currency, dates, and all nested fields.
- **ExtractionStrategy**: A named configuration for extracting data from a specific issuer.
  Attributes: issuer name pattern, custom prompt override.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes — MVP (P1–P3)

- **SC-001**: A document is fully extracted and its structured record is queryable in the data
  warehouse within 60 seconds of submission.
- **SC-002**: At least 80% of standard invoice and receipt formats produce a correct extraction
  on the first attempt (all required fields present and accurate) using the generic extractor.
- **SC-003**: For issuers with a registered custom strategy, extraction accuracy improves to at
  least 95% correct results (correct line items, amounts, and dates).
- **SC-004**: Locale-specific document types (Factura, Boleta, Recibo, etc.) are preserved
  correctly in 100% of extractions — no English remapping in any stored record.
- **SC-005**: No extraction failure causes data loss — all failed records retain the source
  file reference and error reason to enable retry.
- **SC-006**: The technical user can query all stored records by date range, issuer, and
  document type to produce a manual expense summary.

---

## Assumptions

- The user is the only user of this system (single-tenant); no access control is required in
  the initial version.
- Document languages are primarily Spanish and English; multilingual content is handled by the
  AI model without extra configuration.
- Duplicate records in the MVP are identified and removed manually by the technical user
  directly in the data warehouse.
- All deferred user stories (US4–US7) remain in this spec for planning reference and will be
  prioritized after MVP validation.
- Credit card and bank statement processing is out of scope for this feature.