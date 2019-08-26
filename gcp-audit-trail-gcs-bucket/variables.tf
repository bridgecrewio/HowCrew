variable "gcp_region" {
  description = "GCP region, e.g. us-east1"
  default = "us-central1"
}

variable "gcp_bucket_location" {
  description = "GCP bucket location"
  default = "US"
}

variable "gcp_bucket_versioning_enabled" {
  description = "GCP bucket versioining enabled"
  default = "true"
}

variable "gcp_bucket_storage_class" {
  description = "GCP bucket storage class"
  default = "MULTI_REGIONAL"
}

variable "gcp_project" {
  description = "GCP project name"
}

variable "tag" {
  description = "Project Tag Name"
}