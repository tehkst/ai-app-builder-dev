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
  runtime_service_account_member = "serviceAccount:${var.runtime_service_account_email}"
}

module "secret_manager" {
  source = "../../modules/secret_manager"

  project_id = var.project_id
  labels     = local.labels
  secrets = [
    "ai-software-factory-production-database-url",
    "ai-software-factory-production-app-secret",
  ]
  runtime_secret_access = {
    "ai-software-factory-production-database-url" = local.runtime_service_account_member
    "ai-software-factory-production-app-secret"   = local.runtime_service_account_member
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
  secret_environment_variables = {
    DATABASE_URL = {
      secret_name = module.secret_manager.secret_ids["ai-software-factory-production-database-url"]
      version     = "latest"
    }
    APP_SECRET = {
      secret_name = module.secret_manager.secret_ids["ai-software-factory-production-app-secret"]
      version     = "latest"
    }
  }
}
