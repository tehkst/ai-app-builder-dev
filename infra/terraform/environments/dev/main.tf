variable "project_id" {
  type = string
}

variable "region" {
  type    = string
  default = "asia-southeast1"
}

variable "container_image" {
  type    = string
  default = null
}

variable "runtime_service_account_email" {
  type = string
}

variable "deploy_service_account_email" {
  type    = string
  default = null
}

locals {
  environment = "dev"
  labels = {
    platform    = "ai-software-factory"
    environment = local.environment
    managed_by  = "terraform"
  }
  runtime_service_account_member = "serviceAccount:${var.runtime_service_account_email}"
}

module "images" {
  source = "../../modules/images"

  project_id    = var.project_id
  region        = var.region
  repository_id = "ai-software-factory-dev"
  labels        = local.labels
}

module "secret_manager" {
  source = "../../modules/secret_manager"

  project_id = var.project_id
  labels     = local.labels
  secrets = [
    "ai-software-factory-dev-database-url",
    "ai-software-factory-dev-app-secret",
  ]
  runtime_secret_access = {
    "ai-software-factory-dev-database-url" = local.runtime_service_account_member
    "ai-software-factory-dev-app-secret"   = local.runtime_service_account_member
  }
}

module "cloud_sql" {
  source = "../../modules/cloud_sql"

  project_id          = var.project_id
  region              = var.region
  instance_name       = "ai-software-factory-dev-db"
  deletion_protection = false
  tier                = "db-f1-micro"
  disk_size_gb        = 10
  labels              = local.labels
}

module "cloud_run" {
  source = "../../modules/cloud_run"

  project_id                   = var.project_id
  region                       = var.region
  service_name                 = "ai-software-factory-dev"
  image                        = coalesce(var.container_image, "${module.images.repository_url}/control-plane:latest")
  service_account_email        = var.runtime_service_account_email
  labels                       = local.labels
  min_instances                = 0
  max_instances                = 3
  deploy_service_account_email = var.deploy_service_account_email
  environment_variables = {
    ENVIRONMENT               = local.environment
    CLOUD_SQL_CONNECTION_NAME = module.cloud_sql.connection_name
  }
  secret_environment_variables = {
    DATABASE_URL = {
      secret_name = module.secret_manager.secret_ids["ai-software-factory-dev-database-url"]
      version     = "latest"
    }
    APP_SECRET = {
      secret_name = module.secret_manager.secret_ids["ai-software-factory-dev-app-secret"]
      version     = "latest"
    }
  }
}
