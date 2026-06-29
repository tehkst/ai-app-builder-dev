variable "project_id" {
  description = "GCP project ID."
  type        = string
}

variable "github_repository" {
  description = "GitHub repository in owner/name form."
  type        = string
  default     = "tehkst/ai-app-builder-dev"
}

variable "deploy_service_account_id" {
  description = "Deployment service account ID."
  type        = string
  default     = "ai-software-factory-deploy"
}

variable "pool_id" {
  description = "Workload Identity Pool ID."
  type        = string
  default     = "github-actions"
}

variable "provider_id" {
  description = "Workload Identity Provider ID."
  type        = string
  default     = "github"
}
