variable "project_id" {
  description = "GCP project ID."
  type        = string
}

variable "region" {
  description = "Cloud SQL region."
  type        = string
}

variable "instance_name" {
  description = "Cloud SQL instance name."
  type        = string
}

variable "database_name" {
  description = "Application database name."
  type        = string
  default     = "ai_software_factory"
}

variable "database_version" {
  description = "Cloud SQL database engine version."
  type        = string
  default     = "POSTGRES_15"
}

variable "tier" {
  description = "Cloud SQL machine tier."
  type        = string
  default     = "db-custom-1-3840"
}

variable "availability_type" {
  description = "Cloud SQL availability type."
  type        = string
  default     = "ZONAL"
}

variable "disk_type" {
  description = "Cloud SQL disk type."
  type        = string
  default     = "PD_SSD"
}

variable "disk_size_gb" {
  description = "Initial disk size in GB."
  type        = number
  default     = 20
}

variable "deletion_protection" {
  description = "Enable deletion protection."
  type        = bool
  default     = true
}

variable "backup_start_time" {
  description = "UTC backup start time."
  type        = string
  default     = "18:00"
}

variable "transaction_log_retention_days" {
  description = "PITR transaction log retention days."
  type        = number
  default     = 7
}

variable "public_ipv4_enabled" {
  description = "Whether public IPv4 is enabled."
  type        = bool
  default     = false
}

variable "private_network" {
  description = "Private VPC network self link. Empty until networking PR is merged."
  type        = string
  default     = null
}

variable "maintenance_day" {
  description = "Maintenance day, 1-7."
  type        = number
  default     = 7
}

variable "maintenance_hour" {
  description = "Maintenance hour UTC."
  type        = number
  default     = 18
}

variable "labels" {
  description = "Common resource labels."
  type        = map(string)
  default     = {}
}
