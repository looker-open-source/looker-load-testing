provider "aws" {
  region = var.aws_region
  shared_credentials_file = "~/.aws/credentials"
  profile = var.aws_profile
  version = "~> 2.0"
}

data "terraform_remote_state" "gke_cluster" {
  backend = "local"

  config = {
    path = "../gke_loadtest_cluster/terraform.tfstate"
  }
}

data "aws_route53_zone" "zone" {
  name = "${var.domain}."
  private_zone = false
}

resource "aws_route53_record" "gke-ingress-lb" {
  zone_id = data.aws_route53_zone.zone.zone_id
  name = "*.${var.subdomain}.${var.domain}"
  type = "A"
  ttl = "300"
  records = ["${data.terraform_remote_state.gke_cluster.outputs.loadtest_cluster_lb_ip}"]
}

output "loadtest_dns_domain" {
  value = "${var.subdomain}.${var.domain}"
}
