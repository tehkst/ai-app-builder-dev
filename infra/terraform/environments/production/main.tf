variable "project_id" {
  type = string
}

variable "region" {
  type    = string
  default = "asia-southeast1"
}

variable "container_image" {
  type = string
}

variable "runtime_service_account_email" {
  type = string
}

locals {
  environment = "production"
  labels = {
    platform    = "ai-software-factory"
    environment = local.environment
    managed_by  = "terraform"
  }
}

module "cloud_run" {
  source = "../../modules/cloud_run"

  project_id            = var.project_id
  region                = var.region
  service_name          = "ai-software-factory-production"
  image                 = var.container_image
  service_account_email = var.runtime_service_account_email
  labels                = local.labels
  min_instances         = 1
  max_instances         = 20
  cpu                   = "2"
  memory                = "1Gi"
  environment_variables = {
    ENVIRONMENT = local.environment
  }
}
