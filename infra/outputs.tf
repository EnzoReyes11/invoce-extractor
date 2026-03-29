output "bucket_name" {
  description = "GCS bucket name for document ingestion."
  value       = google_storage_bucket.documents.name
}

output "bq_dataset_id" {
  description = "BigQuery dataset ID."
  value       = google_bigquery_dataset.expense_tracking.dataset_id
}

output "pubsub_topic" {
  description = "Pub/Sub topic name for pipeline events."
  value       = google_pubsub_topic.pipeline_events.name
}

output "service_account_email" {
  description = "Service account email for the pipeline."
  value       = google_service_account.pipeline.email
}
