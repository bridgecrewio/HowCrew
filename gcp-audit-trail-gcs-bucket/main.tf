terraform {
  required_version = ">= 0.11.11"
}

resource "google_kms_crypto_key" "gcs-audit-trail-bucket-key" {
  name = "${var.tag}-gcs-audit-trail-key"
  key_ring = "${google_kms_key_ring.gcs-audittrail.self_link}"
  rotation_period = "86401s"
}

resource "google_kms_key_ring" "gcs-audittrail" {
  name = "${var.tag}-gcs-audit-trail-key"
  location = "global"
}


provider "google" {
  project = "${var.gcp_project}"
  region = "${var.gcp_region}"
}

resource "google_storage_bucket" "audit-trail-bucket" {
  name = "${var.tag}-${var.gcp_project}-audit-trail"
  location = "${var.gcp_bucket_location}"
  storage_class = "${var.gcp_bucket_storage_class}"
  versioning {
    enabled = "${var.gcp_bucket_versioning_enabled}"
  }
}

resource "google_logging_project_sink" "audit-trail-sink" {
  name = "${var.tag}-${var.gcp_project}-audit-trail-sink"

  destination = "storage.googleapis.com/${google_storage_bucket.audit-trail-bucket.name}"

  filter = "protoPayload.@type=type.googleapis.com/google.cloud.audit.AuditLog AND NOT protoPayload.methodName:'storage.objects.'"

  unique_writer_identity = true
}

resource "google_project_iam_binding" "audit-trail-writer" {
  role = "roles/storage.objectCreator"

  members = [
    "${google_logging_project_sink.audit-trail-sink.writer_identity}",
  ]
}

resource "google_pubsub_topic" "audit-trail-topic" {
  name = "${var.tag}-${var.gcp_project}-audit-trail-topic"
}

resource "google_pubsub_subscription" "audit-trail-subscription" {
  name = "${var.tag}-${var.gcp_project}-audit-trail-subscription"
  topic = "${google_pubsub_topic.audit-trail-topic.name}"

  ack_deadline_seconds = 300
}

resource "google_storage_notification" "audit-trail-notification" {
  bucket = "${google_storage_bucket.audit-trail-bucket.name}"
  payload_format = "JSON_API_V1"
  topic = "${google_pubsub_topic.audit-trail-topic.id}"
  event_types = [
    "OBJECT_FINALIZE"]
  depends_on = [
    "google_pubsub_topic_iam_binding.audit-trail-publisher-binding"]

}
data "google_storage_project_service_account" "audit-trail-notification-account" {
  account_id = "${var.tag}-auditpublish"
  display_name = "${var.tag} audit trail publisher"
}

resource "google_pubsub_topic_iam_binding" "audit-trail-publisher-binding" {
  topic = "${google_pubsub_topic.audit-trail-topic.name}"
  role = "roles/pubsub.publisher"
  members = [
    "serviceAccount:${data.google_storage_project_service_account.audit-trail-notification-account.email_address}"]
}

resource "google_service_account" "audit-trail-viewer" {
  account_id = "${var.tag}-auditviewer"
  display_name = "${var.tag} audit trail viewer"
}

resource "google_storage_bucket_iam_binding" "audit-trail-iam-binding" {
  bucket = "${google_storage_bucket.audit-trail-bucket.name}"
  role = "roles/storage.objectViewer"

  members = [
    "serviceAccount:${google_service_account.audit-trail-viewer.email}",
  ]
}

resource "google_pubsub_subscription_iam_binding" "audi-trail-pubsub-iam-binding" {
  subscription = "${google_pubsub_subscription.audit-trail-subscription.name}"
  role = "roles/pubsub.subscriber"
  members = [
    "serviceAccount:${google_service_account.audit-trail-viewer.email}",
  ]
}