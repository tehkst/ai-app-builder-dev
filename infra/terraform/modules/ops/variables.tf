variable "project_id" {
  description = "GCP project ID."
  type        = string
}

variable "environment" {
  description = "Deployment environment."
  type        = string
}

variable "contact_email" {
  description = "Optional contact email."
  type        = string
  default     = null
}

variable "error_threshold" {
  description = "Error threshold."
  type        = number
  default     = 0
}
