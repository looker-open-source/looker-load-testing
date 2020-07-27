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
  initial_node_count = var.node_count

  node_version = "1.16.9-gke.6"
  min_master_version = "1.16.9-gke.6"

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

data "google_compute_instance_group" "cluster_group" {
  self_link = google_container_cluster.gke_load_test.instance_group_urls[0]
}

data "google_compute_instance" "cluster_instance" {
  count = var.node_count
  self_link = tolist(data.google_compute_instance_group.cluster_group.instances)[count.index]
}

output "cluster_instance_ips" {
  value = formatlist("%s%s", data.google_compute_instance.cluster_instance.*.network_interface.0.access_config.0.nat_ip, "/32")
}
