terraform {
  required_version = ">= 1.10.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 7.23.0"
    }
  }

  backend "gcs" {
    # Configure via: terraform init -backend-config="bucket=YOUR_TF_STATE_BUCKET"
    prefix = "expense-tracking-pipeline/state"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}
