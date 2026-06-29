variable "project_id" {
  description = "GCP project ID."
  type        = string
}

variable "region" {
  description = "Cloud Run region."
  type        = string
}

variable "service_name" {
  description = "Cloud Run service name."
  type        = string
}

variable "image" {
  description = "Container image URI."
  type        = string
}

variable "service_account_email" {
  description = "Runtime service account email."
  type        = string
}

variable "container_port" {
  description = "Container port exposed by the application."
  type        = number
  default     = 8080
}

variable "cpu" {
  description = "CPU limit."
  type        = string
  default     = "1"
}

variable "memory" {
  description = "Memory limit."
  type        = string
  default     = "512Mi"
}

variable "min_instances" {
  description = "Minimum instances."
  type        = number
  default     = 0
}

variable "max_instances" {
  description = "Maximum instances."
  type        = number
  default     = 10
}

variable "health_path" {
  description = "Health check path."
  type        = string
  default     = "/health"
}

variable "environment_variables" {
  description = "Plain environment variables. Secrets are wired in later PRs."
  type        = map(string)
  default     = {}
}

variable "labels" {
  description = "Common resource labels."
  type        = map(string)
  default     = {}
}
