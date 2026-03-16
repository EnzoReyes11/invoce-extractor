variable "project_id" {
  description = "GCP project ID where all resources will be created."
  type        = string
}

variable "region" {
  description = "GCP region for all regional resources."
  type        = string
  default     = "us-central1"
}

variable "environment" {
  description = "Deployment environment: dev, staging, or prod."
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment must be one of: dev, staging, prod."
  }
}

variable "bucket_name" {
  description = "Name of the GCS bucket for ingested documents."
  type        = string
  default     = "expense-tracking-documents"
}

variable "bq_dataset" {
  description = "BigQuery dataset ID for extraction results."
  type        = string
  default     = "expense_tracking"
}

variable "cloud_run_service_name" {
  description = "Name of the Cloud Run service for the pipeline handler."
  type        = string
  default     = "expense-pipeline"
}
