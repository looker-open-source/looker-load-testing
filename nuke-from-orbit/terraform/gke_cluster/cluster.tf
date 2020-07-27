provider "google" {
  project = var.project
  region = var.region
  zone = var.zone
  version = "~> 3.31"
}

resource "google_container_cluster" "gke_load_test" {
  name = "gke-load-test"
  location = var.zone
  remove_default_node_pool = true
  initial_node_count = 1
}

resource "google_container_node_pool" "primary_nodes" {
  name = "gke_load_test_node_pool"
  location = var.zone
  cluster = google_container_cluster.gke_load_test.name
  node_count = var.node_count
  version = "1.16.9-gke.6"

  node_config {
    machine_type = var.machine_type
    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform"
    ]
    metadata = {
      disable-legacy-endpoints = "true"
    }
  }

}
