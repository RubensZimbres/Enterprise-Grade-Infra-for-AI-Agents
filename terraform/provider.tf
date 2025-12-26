terraform {
  required_version = ">= 1.5"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 5.0"
    }
  }

  # STOP: You must create this bucket manually in the console first.
  # Terraform cannot create the bucket it uses to store its own memory.
  backend "gcs" {
    bucket = "terraform-state-prod-rubens-ai-platform" # CHANGE THIS
    prefix = "terraform/state"
  }
}

provider "google" {
  project = var.project_id # CHANGE THIS
  region  = "us-central1"         # CHANGE THIS
}

provider "google-beta" {
  project = var.project_id # CHANGE THIS
  region  = "us-central1"         # CHANGE THIS
}