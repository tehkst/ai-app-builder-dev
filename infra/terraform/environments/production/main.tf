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

module "cloud_sql" {
  source = "../../modules/cloud_sql"

  project_id          = var.project_id
  region              = var.region
  instance_name       = "ai-software-factory-production-db"
  deletion_protection = true
  tier                = "db-custom-2-7680"
  disk_size_gb        = 100
  labels              = local.labels
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
    ENVIRONMENT               = local.environment
    CLOUD_SQL_CONNECTION_NAME = module.cloud_sql.connection_name
  }
}
