# ARKiin v2.0 — Terraform Infrastructure
# Provisions GCP event-driven backbone for europe-west3 region
# Run: terraform init && terraform apply

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
  backend "gcs" {
    bucket = "arkiin-tfstate"
    prefix = "terraform/state"
  }
}

provider "google" {
  project = "arkiin"
  region  = "europe-west3"
}

# ============================================================
# ENABLE REQUIRED APIS
# ============================================================
locals {
  apis = [
    "run.googleapis.com",
    "pubsub.googleapis.com",
    "firestore.googleapis.com",
    "aiplatform.googleapis.com",
    "cloudtasks.googleapis.com",
    "documentai.googleapis.com",
    "bigquery.googleapis.com",
    "storage.googleapis.com",
    "artifactregistry.googleapis.com",
    "cloudbuild.googleapis.com",
    "logging.googleapis.com",
    "monitoring.googleapis.com"
  ]
  pubsub_steps = [
    "taste_updated",
    "spatial_analyzed",
    "layout_generated",
    "render_generated",
    "procurement_optimized",
    "pack_generated"
  ]
}

resource "google_project_service" "apis" {
  for_each           = toset(local.apis)
  service            = each.key
  disable_on_destroy = false
}

# ============================================================
# FIRESTORE DATABASE
# ============================================================
resource "google_firestore_database" "default" {
  name        = "(default)"
  location_id = "eur3"  # Multi-region EU
  type        = "FIRESTORE_NATIVE"
  depends_on  = [google_project_service.apis]
}

# ============================================================
# CLOUD STORAGE — Floor plan uploads
# ============================================================
resource "google_storage_bucket" "floor_plans" {
  name          = "arkiin-floor-plans"
  location      = "EU"
  force_destroy = false
  uniform_bucket_level_access = true
  versioning { enabled = true }
  lifecycle_rule {
    action { type = "Delete" }
    condition { age = 365 }
  }
}

# ============================================================
# PUB/SUB ORCHESTRATION with Dead Letter Queue
# ============================================================
resource "google_pubsub_topic" "dead_letter" {
  name = "arkiin-dlq"
}

resource "google_pubsub_topic" "events" {
  for_each = toset(local.pubsub_steps)
  name     = "arkiin-${each.key}"
}

resource "google_pubsub_subscription" "event_subs" {
  for_each = toset(local.pubsub_steps)
  name     = "arkiin-${each.key}-sub"
  topic    = google_pubsub_topic.events[each.key].name

  push_config {
    push_endpoint = "${google_cloud_run_v2_service.api.uri}/events/${each.key}"
    oidc_token {
      service_account_email = google_service_account.cloud_run_sa.email
    }
  }

  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.dead_letter.id
    max_delivery_attempts = 5
  }

  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }

  expiration_policy { ttl = "" }  # Never expire
}

# ============================================================
# BIGQUERY — Materials Catalog
# ============================================================
resource "google_bigquery_dataset" "materials" {
  dataset_id  = "arkiin_materials"
  location    = "EU"
  description = "EU supplier and material catalog for procurement optimization"
}

resource "google_bigquery_table" "eu_catalog" {
  dataset_id = google_bigquery_dataset.materials.dataset_id
  table_id   = "eu_catalog"
  schema = jsonencode([
    { name = "sku",                   type = "STRING",  mode = "REQUIRED" },
    { name = "description",          type = "STRING",  mode = "REQUIRED" },
    { name = "unit_cost",            type = "FLOAT64", mode = "REQUIRED" },
    { name = "supplier",             type = "STRING",  mode = "REQUIRED" },
    { name = "carbon_score",         type = "FLOAT64", mode = "REQUIRED" },
    { name = "lead_time_days",       type = "INT64",   mode = "REQUIRED" },
    { name = "availability_region",  type = "STRING",  mode = "REQUIRED" },
    { name = "style_tags",           type = "STRING",  mode = "REPEATED" }
  ])
}

# ============================================================
# ARTIFACT REGISTRY
# ============================================================
resource "google_artifact_registry_repository" "docker" {
  location      = "europe-west3"
  repository_id = "arkiin"
  description   = "ARKiin Docker images"
  format        = "DOCKER"
}

# ============================================================
# SERVICE ACCOUNT
# ============================================================
resource "google_service_account" "cloud_run_sa" {
  account_id   = "arkiin-api-sa"
  display_name = "ARKiin API Cloud Run Service Account"
}

resource "google_project_iam_member" "sa_roles" {
  for_each = toset([
    "roles/datastore.user",
    "roles/bigquery.dataViewer",
    "roles/bigquery.jobUser",
    "roles/storage.objectAdmin",
    "roles/pubsub.publisher",
    "roles/pubsub.subscriber",
    "roles/logging.logWriter",
    "roles/aiplatform.user"
  ])
  project = "arkiin"
  role    = each.key
  member  = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

# ============================================================
# CLOUD RUN API SERVICE
# ============================================================
resource "google_cloud_run_v2_service" "api" {
  name     = "arkiin-api"
  location = "europe-west3"

  template {
    service_account = google_service_account.cloud_run_sa.email
    scaling { max_instance_count = 10 }

    containers {
      image = "europe-west3-docker.pkg.dev/arkiin/arkiin/arkiin-api:latest"

      resources {
        limits = { cpu = "2", memory = "2Gi" }
      }

      env {
        name  = "GOOGLE_CLOUD_PROJECT"
        value = "arkiin"
      }
    }
  }

  depends_on = [google_project_service.apis]
}
