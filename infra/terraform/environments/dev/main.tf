locals {
  environment = "dev"
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
  service_name          = "ai-software-factory-dev"
  image                 = var.container_image
  service_account_email = var.runtime_service_account_email
  labels                = local.labels
  min_instances         = 0
  max_instances         = 3
  environment_variables = {
    ENVIRONMENT = local.environment
  }
}
