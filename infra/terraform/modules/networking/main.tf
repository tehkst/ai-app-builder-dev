resource "google_compute_network" "network" {
  project                 = var.project_id
  name                    = var.network_name
  auto_create_subnetworks = false
  routing_mode            = "REGIONAL"
}

resource "google_compute_subnetwork" "subnet" {
  project                  = var.project_id
  name                     = var.subnet_name
  ip_cidr_range            = var.subnet_cidr
  region                   = var.region
  network                  = google_compute_network.network.id
  private_ip_google_access = true
}

resource "google_compute_global_address" "service_range" {
  project       = var.project_id
  name          = var.service_range_name
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = var.service_range_prefix_length
  network       = google_compute_network.network.id
}

resource "google_service_networking_connection" "private_services" {
  network                 = google_compute_network.network.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.service_range.name]
}

resource "google_vpc_access_connector" "serverless" {
  project       = var.project_id
  name          = var.connector_name
  region        = var.region
  network       = google_compute_network.network.name
  ip_cidr_range = var.connector_cidr
}

resource "google_compute_router" "router" {
  project = var.project_id
  name    = var.router_name
  region  = var.region
  network = google_compute_network.network.id
}

resource "google_compute_router_nat" "nat" {
  project                            = var.project_id
  name                               = var.nat_name
  router                             = google_compute_router.router.name
  region                             = var.region
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"
}
