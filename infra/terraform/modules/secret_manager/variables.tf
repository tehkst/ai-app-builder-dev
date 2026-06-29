variable "project_id" {
  description = "GCP project ID."
  type        = string
}

variable "secrets" {
  description = "Secret names to create. Values are metadata only; secret payloads are never committed."
  type        = set(string)
  default     = []
}

variable "runtime_secret_access" {
  description = "Map of secret name to IAM member granted runtime access."
  type        = map(string)
  default     = {}
}

variable "labels" {
  description = "Common resource labels."
  type        = map(string)
  default     = {}
}
