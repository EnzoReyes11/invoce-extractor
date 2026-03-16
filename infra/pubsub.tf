resource "google_pubsub_topic" "pipeline_events" {
  name = "expense-pipeline-events"

  message_retention_duration = "86600s"
}

data "google_project" "project" {
  project_id = var.project_id
}

resource "google_pubsub_subscription" "pipeline_push" {
  name  = "expense-pipeline-push"
  topic = google_pubsub_topic.pipeline_events.id

  push_config {
    push_endpoint = "https://${var.cloud_run_service_name}-${data.google_project.project.number}.${var.region}.run.app/pubsub"

    oidc_token {
      service_account_email = google_service_account.pipeline.email
    }
  }

  ack_deadline_seconds = 60

  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "300s"
  }

  expiration_policy {
    ttl = ""
  }
}
