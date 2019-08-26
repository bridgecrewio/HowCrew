output "audit-trail-subscription" {
  value = "${google_pubsub_subscription.audit-trail-subscription.name}"
}