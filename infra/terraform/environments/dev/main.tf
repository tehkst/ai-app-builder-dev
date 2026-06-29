locals {
  environment = "dev"
  labels = {
    platform    = "ai-software-factory"
    environment = local.environment
    managed_by  = "terraform"
  }
}

# P1.1 foundation root. Service modules are wired in later production PRs.
