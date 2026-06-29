variable "project_id" {
  description = "GCP project ID."
  type        = string
}

variable "region" {
  description = "GCP region."
  type        = string
}

variable "network_name" {
  description = "VPC network name."
  type        = string
}

variable "subnet_name" {
  description = "Subnet name."
  type        = string
}

variable "subnet_cidr" {
  description = "Subnet CIDR range."
  type        = string
}

variable "service_range_name" {
  description = "Private service range name."
  type        = string
}

variable "service_range_prefix_length" {
  description = "Private service range prefix length."
  type        = number
  default     = 16
}

variable "connector_name" {
  description = "Serverless connector name."
  type        = string
}

variable "connector_cidr" {
  description = "Serverless connector CIDR range."
  type        = string
}

variable "router_name" {
  description = "Cloud Router name."
  type        = string
}

variable "nat_name" {
  description = "Cloud NAT name."
  type        = string
}
