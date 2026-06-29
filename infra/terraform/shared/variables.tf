variable "project_id" {
  description = "GCP project ID."
  type        = string
}

variable "region" {
  description = "Default GCP region."
  type        = string
  default     = "asia-southeast1"
}

variable "environment" {
  description = "Deployment environment."
  type        = string
}

variable "platform_name" {
  description = "Platform name used for resource naming."
  type        = string
  default     = "ai-software-factory"
}

variable "labels" {
  description = "Common resource labels."
  type        = map(string)
  default     = {}
}
