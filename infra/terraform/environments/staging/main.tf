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
  environment = "staging"
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
    "ai-software-factory-staging-database-url",
    "ai-software-factory-staging-app-secret",
  ]
  runtime_secret_access = {
    "ai-software-factory-staging-database-url" = local.runtime_service_account_member
    "ai-software-factory-staging-app-secret"   = local.runtime_service_account_member
  }
}

module "cloud_sql" {
  source = "../../modules/cloud_sql"

  project_id          = var.project_id
  region              = var.region
  instance_name       = "ai-software-factory-staging-db"
  deletion_protection = false
  tier                = "db-custom-1-3840"
  disk_size_gb        = 20
  labels              = local.labels
}

module "cloud_run" {
  source = "../../modules/cloud_run"

  project_id            = var.project_id
  region                = var.region
  service_name          = "ai-software-factory-staging"
  image                 = var.container_image
  service_account_email = var.runtime_service_account_email
  labels                = local.labels
  min_instances         = 0
  max_instances         = 5
  environment_variables = {
    ENVIRONMENT               = local.environment
    CLOUD_SQL_CONNECTION_NAME = module.cloud_sql.connection_name
  }
  secret_environment_variables = {
    DATABASE_URL = {
      secret_name = module.secret_manager.secret_ids["ai-software-factory-staging-database-url"]
      version     = "latest"
    }
    APP_SECRET = {
      secret_name = module.secret_manager.secret_ids["ai-software-factory-staging-app-secret"]
      version     = "latest"
    }
  }
}
