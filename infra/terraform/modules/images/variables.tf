variable "project_id" {
  description = "GCP project ID."
  type        = string
}

variable "region" {
  description = "Repository region."
  type        = string
}

variable "repository_id" {
  description = "Image repository ID."
  type        = string
}

variable "description" {
  description = "Repository description."
  type        = string
  default     = "AI Software Factory container images"
}

variable "labels" {
  description = "Common resource labels."
  type        = map(string)
  default     = {}
}
