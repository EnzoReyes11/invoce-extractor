resource "google_bigquery_dataset" "expense_tracking" {
  dataset_id    = var.bq_dataset
  friendly_name = "Expense Tracking"
  description   = "Stores structured extraction results from expense documents."
  location      = var.region

  delete_contents_on_destroy = var.environment != "prod"
}

resource "google_bigquery_table" "extractions" {
  dataset_id          = google_bigquery_dataset.expense_tracking.dataset_id
  table_id            = "extractions"
  deletion_protection = var.environment == "prod"

  schema = jsonencode([
    { name = "id", type = "STRING", mode = "REQUIRED", description = "UUID for this extraction record." },
    { name = "source_file_uri", type = "STRING", mode = "REQUIRED", description = "GCS URI of the source document." },
    { name = "source_format", type = "STRING", mode = "REQUIRED", description = "MIME type of the source document." },
    { name = "status", type = "STRING", mode = "REQUIRED", description = "Extraction status: success, partial, or failed." },
    { name = "strategy_used", type = "STRING", mode = "REQUIRED", description = "Extraction strategy name used." },
    { name = "extracted_at", type = "TIMESTAMP", mode = "REQUIRED", description = "UTC timestamp of extraction." },
    { name = "error_message", type = "STRING", mode = "NULLABLE", description = "Human-readable error message on failure." },
    { name = "raw_gemini_response", type = "STRING", mode = "NULLABLE", description = "Raw Gemini response (truncated to 10KB)." },
    {
      name        = "result"
      type        = "RECORD"
      mode        = "NULLABLE"
      description = "Structured extraction result."
      fields = [
        { name = "document_type", type = "STRING", mode = "NULLABLE" },
        { name = "document_number", type = "STRING", mode = "NULLABLE" },
        { name = "date_issued", type = "DATE", mode = "NULLABLE" },
        { name = "date_due", type = "DATE", mode = "NULLABLE" },
        { name = "date_paid", type = "DATE", mode = "NULLABLE" },
        { name = "currency", type = "STRING", mode = "NULLABLE" },
        { name = "overall_total", type = "NUMERIC", mode = "NULLABLE" },
        { name = "overall_subtotal", type = "NUMERIC", mode = "NULLABLE" },
        { name = "overall_discount", type = "NUMERIC", mode = "NULLABLE" },
        { name = "overall_tax", type = "NUMERIC", mode = "NULLABLE" },
        { name = "overall_amount_paid", type = "NUMERIC", mode = "NULLABLE" },
        { name = "outstanding_balance", type = "NUMERIC", mode = "NULLABLE" },
        { name = "tags", type = "STRING", mode = "REPEATED" },
        { name = "notes", type = "STRING", mode = "NULLABLE" },
        {
          name = "issuer", type = "RECORD", mode = "NULLABLE",
          fields = [
            { name = "name", type = "STRING", mode = "NULLABLE" },
            { name = "tax_id", type = "STRING", mode = "NULLABLE" },
            { name = "address", type = "STRING", mode = "NULLABLE" },
            { name = "email", type = "STRING", mode = "NULLABLE" },
            { name = "phone", type = "STRING", mode = "NULLABLE" },
            { name = "website", type = "STRING", mode = "NULLABLE" }
          ]
        },
        {
          name = "bill_to", type = "RECORD", mode = "NULLABLE",
          fields = [
            { name = "name", type = "STRING", mode = "NULLABLE" },
            { name = "tax_id", type = "STRING", mode = "NULLABLE" },
            { name = "address", type = "STRING", mode = "NULLABLE" },
            { name = "email", type = "STRING", mode = "NULLABLE" },
            { name = "account_number", type = "STRING", mode = "NULLABLE" }
          ]
        },
        {
          name = "billing_period", type = "RECORD", mode = "NULLABLE",
          fields = [
            { name = "start", type = "DATE", mode = "NULLABLE" },
            { name = "end", type = "DATE", mode = "NULLABLE" }
          ]
        },
        {
          name = "payment_method", type = "RECORD", mode = "NULLABLE",
          fields = [
            { name = "method", type = "STRING", mode = "NULLABLE" },
            { name = "name", type = "STRING", mode = "NULLABLE" },
            { name = "card_last_four", type = "STRING", mode = "NULLABLE" },
            { name = "card_brand", type = "STRING", mode = "NULLABLE" },
            { name = "transaction_id", type = "STRING", mode = "NULLABLE" }
          ]
        },
        {
          name        = "line_items"
          type        = "RECORD"
          mode        = "REPEATED"
          description = "Individual line items."
          fields = [
            { name = "description", type = "STRING", mode = "NULLABLE" },
            { name = "sku", type = "STRING", mode = "NULLABLE" },
            { name = "quantity", type = "FLOAT64", mode = "NULLABLE" },
            { name = "unit", type = "STRING", mode = "NULLABLE" },
            { name = "unit_price", type = "NUMERIC", mode = "NULLABLE" },
            { name = "discount", type = "NUMERIC", mode = "NULLABLE" },
            { name = "total", type = "NUMERIC", mode = "NULLABLE" },
            { name = "notes", type = "STRING", mode = "NULLABLE" }
          ]
        },
        {
          name        = "taxes"
          type        = "RECORD"
          mode        = "REPEATED"
          description = "Tax breakdown lines."
          fields = [
            { name = "name", type = "STRING", mode = "NULLABLE" },
            { name = "rate", type = "NUMERIC", mode = "NULLABLE" },
            { name = "amount", type = "NUMERIC", mode = "NULLABLE" }
          ]
        }
      ]
    }
  ])
}
