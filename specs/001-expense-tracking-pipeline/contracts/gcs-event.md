# Contract: GCS Ingestion Event

**Direction**: GCS → Pub/Sub → Cloud Run pipeline handler
**Trigger**: Object finalized in the ingestion bucket

---

## Event Payload (Pub/Sub message data, base64-decoded)

```json
{
  "name": "invoices/2026-03/claro_factura.pdf",
  "bucket": "expense-tracking-documents",
  "contentType": "application/pdf",
  "size": "245123",
  "timeCreated": "2026-03-14T10:22:00.000Z",
  "updated": "2026-03-14T10:22:00.000Z"
}
```

**Source**: `google.cloud.storage.object.v1.finalized` Eventarc event

## Pipeline Handler Contract

**Input**: Pub/Sub push message (HTTP POST to Cloud Run `/` endpoint)

**Processing**:
1. Decode Pub/Sub envelope → extract `bucket` and `name`
2. Build GCS URI: `gs://{bucket}/{name}`
3. Validate MIME type is supported (application/pdf, image/jpeg, image/png)
4. Invoke ADK Runner with file reference
5. Write ExtractionRecord to BigQuery

**Responses**:

| HTTP Status | Meaning |
|-------------|---------|
| 200 | Message processed (extraction succeeded or was recorded as failed) |
| 400 | Unsupported file type — message acknowledged to prevent redelivery |
| 500 | Transient error — Pub/Sub will retry (at-least-once delivery) |

**Idempotency**: If the same GCS URI is processed twice, a duplicate ExtractionRecord is
written to BigQuery. Deduplication is handled manually by the technical user in the MVP.

## Supported File Types

| MIME Type | Extension | Supported |
|-----------|-----------|-----------|
| application/pdf | .pdf | ✅ |
| image/jpeg | .jpg, .jpeg | ✅ |
| image/png | .png | ✅ |
| image/webp | .webp | ✅ |
| Other | — | ❌ — 400 returned, message acked |