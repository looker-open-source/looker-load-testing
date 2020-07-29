provider "aws" {
  region = var.aws_region
  shared_credentials_file = "~/.aws/credentials"
  profile = var.aws_profile
  version = "~> 2.0"
}

provider random {
  version = "~> 2.0"
}

provider tls {
  version = "~> 2.0"
}

data "terraform_remote_state" "gke_cluster" {
  backend = "local"

  config = {
    path = "../gke_loadtest_cluster/terraform.tfstate"
  }
}

# Get the latest ubuntu ami for the above region
data "aws_ami" "ubuntu" {
    most_recent = true

    filter {
        name   = "name"
        values = ["ubuntu/images/hvm-ssd/ubuntu-bionic-18.04-amd64-server-*"]
    }

    filter {
        name   = "virtualization-type"
        values = ["hvm"]
    }

    owners = ["099720109477"] # Canonical
}


# Create a virtual private cloud to contain all these resources
resource "aws_vpc" "looker-env" {
  cidr_block = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support = true
  tags = {
    owner = var.tag_email
  }
}

# Create elastic IP addresses for our ec2 instances
resource "aws_eip" "ip-looker-env" {
  depends_on = [data.aws_instances.looker-instance-select]
  count      = var.instances
  instance   = data.aws_instances.looker-instance-select.ids[count.index]
  vpc        = true
  tags = {
    owner = var.tag_email
  }
}

# Get a list of all availability zones in this region, we need it to create subnets
data "aws_availability_zones" "available" {}

# Create subnets within each availability zone
resource "aws_subnet" "subnet-looker" {
  count                   = length(data.aws_availability_zones.available.names)
  vpc_id                  = aws_vpc.looker-env.id
  cidr_block              = "10.0.${length(data.aws_availability_zones.available.names) + count.index}.0/24"
  map_public_ip_on_launch = true
  availability_zone       = element(data.aws_availability_zones.available.names, count.index)
  tags = {
    owner = var.tag_email
  }
}


# Create the inbound security rules
resource "aws_security_group" "ingress-all-looker" {
  name = "allow-all-sg"
  vpc_id = aws_vpc.looker-env.id
  tags = {
    owner = var.tag_email
  }

  # Looker cluster communication
  ingress {
    cidr_blocks = [
      "10.0.0.0/16" # (private to subnet)
    ]
    from_port = 61616
    to_port = 61616
    protocol = "tcp"
  }

  # Looker cluster communication
  ingress {
    cidr_blocks = [
      "10.0.0.0/16" # (private to subnet)
    ]
    from_port = 1551
    to_port = 1551
    protocol = "tcp"
  }

  # Looker NFS communication
  ingress {
    cidr_blocks = [
      "10.0.0.0/16" # (private to subnet)
    ]
    from_port = 2049
    to_port = 2049
    protocol = "tcp"
  }

  # MySQL
  ingress {
    cidr_blocks = [
      "10.0.0.0/16" # (private to subnet)
    ]
    from_port = 3306
    to_port = 3306
    protocol = "tcp"
  }

  # SSH
  ingress {
    cidr_blocks = [
      "0.0.0.0/0" # (open to the world)
    ]
    from_port = 22
    to_port = 22
    protocol = "tcp"
  }

  # API
  ingress {
    cidr_blocks = [
      "0.0.0.0/0" # (open to the world)
    ]
    from_port = 19999
    to_port = 19999
    protocol = "tcp"
  }

  # Monitoring
  ingress {
    cidr_blocks = data.terraform_remote_state.gke_cluster.outputs.cluster_instance_ips
    from_port = 9810
    to_port = 9810
    protocol = "tcp"
  }

  # HTTP to reach single nodes
  ingress {
    cidr_blocks = [
      "0.0.0.0/0" # (open to the world)
    ]
    from_port = 9999
    to_port = 9999
    protocol = "tcp"
  }

  # HTTPS
  ingress {
    cidr_blocks = [
      "0.0.0.0/0" # (open to the world)
    ]
    from_port = 443
    to_port = 443
    protocol = "tcp"
  }

  egress {
    from_port = 0
    to_port = 0
    protocol = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# Conditionally create db resources
resource "aws_db_subnet_group" "subnet-group-looker" {
  name        = "looker-subnet-group"
  subnet_ids  = aws_subnet.subnet-looker.*.id
  count       = var.external_db == 1 || var.instances > 1 ? 1 : 0
  tags = {
    owner = var.tag_email
  }
}

resource "aws_db_parameter_group" "looker_db_parameters" {

  name = "customer-internal-57-utf8mb4"
  family = "mysql5.7"
  count = var.external_db == 1 || var.instances > 1 ? 1 : 0
  tags = {
    owner = var.tag_email
  }

  parameter {
    name  = "character_set_client"
    value = "utf8mb4"
  }

  parameter {
    name  = "character_set_connection"
    value = "utf8mb4"
  }

  parameter {
    name  = "character_set_database"
    value = "utf8mb4"
  }

  parameter {
    name  = "character_set_results"
    value = "utf8mb4"
  }

  parameter {
    name  = "character_set_server"
    value = "utf8mb4"
  }

  parameter {
    name  = "collation_connection"
    value = "utf8mb4_general_ci"
  }

  parameter {
    name  = "collation_server"
    value = "utf8mb4_general_ci"
  }

  parameter {
    name  = "default_password_lifetime"
    value = "0"
  }

  parameter {
    name  = "innodb_log_file_size"
    value = "536870912"
    apply_method = "pending-reboot"
  }

  parameter {
    name  = "innodb_purge_threads"
    value = "1"
    apply_method = "pending-reboot"
  }

  parameter {
    name  = "log_bin_trust_function_creators"
    value = "1"
  }

  parameter {
    name  = "max_allowed_packet"
    value = "1073741824"
  }
}

# Create the RDS instance for the Looker application database
resource "aws_db_instance" "looker-app-db" {
  allocated_storage    = 100 # values less than 100GB will result in degraded IOPS performance
  storage_type         = "gp2"
  engine               = "mysql"
  engine_version       = "5.7"
  instance_class       = var.db_instance_type
  name                 = "looker"
  username             = "looker"
  password             = "abc_${random_string.password.result}"
  db_subnet_group_name   = aws_db_subnet_group.subnet-group-looker[0].name
  parameter_group_name = aws_db_parameter_group.looker_db_parameters[0].name
  vpc_security_group_ids = ["${aws_security_group.ingress-all-looker.id}"]
  backup_retention_period = 5
  skip_final_snapshot = var.final_snapshot_skip
  identifier_prefix = var.env
  count = var.external_db == 1 || var.instances > 1 ? 1 : 0
  tags = {
    owner = var.tag_email
  }
}


# Choose an existing public/private key pair to use for authentication
resource "aws_key_pair" "key" {
  key_name   = "key${aws_vpc.looker-env.id}"
  public_key = file("~/.ssh/${var.key}.pub") # this file must be an existing public key!
  tags = {
    owner = var.tag_email
  }
}


# Conditionally create a shared NFS file system and mount target
resource "aws_efs_file_system" "looker-efs-fs" {
  count            = var.instances > 1 ? 1: 0
  creation_token   = "looker-efs-token"
  performance_mode = "generalPurpose"
  encrypted        = "false"
  tags = {
    owner = var.tag_email
    Name = "${var.env}_efs"
  }
}

resource "aws_efs_mount_target" "efs-mount" {
  count            = var.instances > 1 ? 1: 0
  file_system_id  = aws_efs_file_system.looker-efs-fs[0].id
  subnet_id       = aws_subnet.subnet-looker.0.id
  security_groups = ["${aws_security_group.ingress-all-looker.id}"]
}

# Create ec2 instances for the Looker application servers. There are three versions of this
# based on the instance count and whether we're using an external db.

# Create a local variable for the instance name
locals {
  instance_name = "looker-dev-sandbox"
}

# Version1: One instance and no external db
resource "aws_instance" "looker-instance" {
  count         = var.instances == 1 && var.external_db == 0 ? 1 : 0
  ami           = data.aws_ami.ubuntu.id
  instance_type = var.ec2_instance_type
  vpc_security_group_ids = ["${aws_security_group.ingress-all-looker.id}"]
  subnet_id = aws_subnet.subnet-looker.0.id
  associate_public_ip_address = true
  key_name = aws_key_pair.key.key_name
  tags = {
    owner = var.tag_email
    name = local.instance_name
  }

  root_block_device {
    volume_type           = "gp2"
    volume_size           = "30"
    delete_on_termination = "true"
  }

  ebs_block_device {
    device_name           = "/dev/sdg"
    volume_type           = "gp2"
    volume_size           = "30"
  }

  connection {
    host = self.public_dns
    type = "ssh"
    user = "ubuntu"
    private_key = file("~/.ssh/${var.key}")
    timeout = "1m"
    agent = true
  }

  provisioner "file" {
    source      = var.provisioning_script
    destination = "/tmp/${var.provisioning_script}"
  }
  provisioner "remote-exec" {
    inline = [
      "sleep 10",

      "export LOOKER_LICENSE_KEY=${var.looker_license_key}",
      "export LOOKER_TECHNICAL_CONTACT_EMAIL=${var.technical_contact_email}",
      "export LOOKER_PASSWORD=abc_${random_string.password.result}",
      "export HOST_URL=${self.public_dns}",

      "export EXTERNAL_DB=no",

      "export CLUSTERED=no",
      "export NODE_COUNT=${count.index}",

      "chmod +x /tmp/${var.provisioning_script}",
      "/bin/bash /tmp/${var.provisioning_script}",
    ]
  }
}

# Version2: One instance and external db
resource "aws_instance" "looker-instance-mysql" {
  count         = var.instances == 1 && var.external_db == 1 ? 1 : 0
  ami           = data.aws_ami.ubuntu.id
  instance_type = var.ec2_instance_type
  vpc_security_group_ids = ["${aws_security_group.ingress-all-looker.id}"]
  subnet_id = aws_subnet.subnet-looker.0.id
  associate_public_ip_address = true
  key_name = aws_key_pair.key.key_name
  tags = {
    owner = var.tag_email
    name = local.instance_name
  }

  root_block_device {
    volume_type           = "gp2"
    volume_size           = "30"
    delete_on_termination = "true"
  }

  ebs_block_device {
    device_name           = "/dev/sdg"
    volume_type           = "gp2"
    volume_size           = "30"
  }

  connection {
    host = self.public_dns
    type = "ssh"
    user = "ubuntu"
    private_key = file("~/.ssh/${var.key}")
    timeout = "1m"
    agent = true
  }

  provisioner "file" {
    source      = var.provisioning_script
    destination = "/tmp/${var.provisioning_script}"
  }
  provisioner "remote-exec" {
    inline = [
      "sleep 10",

      "export LOOKER_LICENSE_KEY=${var.looker_license_key}",
      "export LOOKER_TECHNICAL_CONTACT_EMAIL=${var.technical_contact_email}",
      "export LOOKER_PASSWORD=abc_${random_string.password.result}",
      "export HOST_URL=${self.public_dns}",

      "export EXTERNAL_DB=yes",
      "export DB_SERVER=${aws_db_instance.looker-app-db[0].address}",
      "export DB_USER=looker",
      "export DB_PASSWORD=\"abc_${random_string.password.result}\"",

      "export CLUSTERED=no",
      "export NODE_COUNT=${count.index}",

      "chmod +x /tmp/${var.provisioning_script}",
      "/bin/bash /tmp/${var.provisioning_script}",
    ]
  }
}

# Version3: Multiple instances and external db
resource "aws_instance" "looker-instance-cluster" {
  count         = var.instances > 1 ? var.instances : 0
  ami           = data.aws_ami.ubuntu.id
  instance_type = var.ec2_instance_type
  vpc_security_group_ids = ["${aws_security_group.ingress-all-looker.id}"]
  subnet_id = aws_subnet.subnet-looker.0.id
  associate_public_ip_address = true
  key_name = aws_key_pair.key.key_name
  tags = {
    owner = var.tag_email
    name = local.instance_name
  }

  root_block_device {
    volume_type           = "gp2"
    volume_size           = "30"
    delete_on_termination = "true"
  }

  ebs_block_device {
    device_name           = "/dev/sdg"
    volume_type           = "gp2"
    volume_size           = "30"
  }

  connection {
    host = self.public_dns
    type = "ssh"
    user = "ubuntu"
    private_key = file("~/.ssh/${var.key}")
    timeout = "1m"
    agent = true
  }

  provisioner "file" {
    source      = var.provisioning_script
    destination = "/tmp/${var.provisioning_script}"
  }
  provisioner "remote-exec" {
    inline = [
      "sleep 10",

      "export LOOKER_LICENSE_KEY=${var.looker_license_key}",
      "export LOOKER_TECHNICAL_CONTACT_EMAIL=${var.technical_contact_email}",
      "export LOOKER_PASSWORD=abc_${random_string.password.result}",
      "export HOST_URL=${self.public_dns}",

      "export EXTERNAL_DB=yes",
      "export DB_SERVER=${aws_db_instance.looker-app-db[0].address}",
      "export DB_USER=looker",
      "export DB_PASSWORD=\"abc_${random_string.password.result}\"",

      "export CLUSTERED=yes",
      "export NODE_COUNT=${count.index}",
      "export SHARED_STORAGE_SERVER=${aws_efs_mount_target.efs-mount[0].dns_name}",

      "chmod +x /tmp/${var.provisioning_script}",
      "/bin/bash /tmp/${var.provisioning_script}",
    ]
  }
}

# Create a data point so elb can use the same variable for each possible instance
data "aws_instances" "looker-instance-select" {
  instance_tags = {
    owner = var.tag_email
    name = local.instance_name
  }
  depends_on = [aws_instance.looker-instance, aws_instance.looker-instance-mysql, aws_instance.looker-instance-cluster]
}

# Create an internet gateway, a routing table, and route associations
resource "aws_internet_gateway" "looker-env-gw" {
  vpc_id = aws_vpc.looker-env.id
  tags = {
    owner = var.tag_email
  }
}

resource "aws_route_table" "route-table-looker-env" {
  vpc_id = aws_vpc.looker-env.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.looker-env-gw.id
  }
  tags = {
    owner = var.tag_email
  }
}

resource "aws_route_table_association" "subnet-association" {
  subnet_id      = aws_subnet.subnet-looker.0.id
  route_table_id = aws_route_table.route-table-looker-env.id
}

data "aws_route53_zone" "zone" {
  name = "${var.domain}."
  private_zone = false
}

resource "aws_acm_certificate" "dev-cert" {
  domain_name = "${var.env}.${var.domain}"
  validation_method = "DNS"
  tags = {
    owner = var.tag_email
  }
  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_route53_record" "dev-cert_validation" {
  name = aws_acm_certificate.dev-cert.domain_validation_options.0.resource_record_name
  type = aws_acm_certificate.dev-cert.domain_validation_options.0.resource_record_type
  zone_id = data.aws_route53_zone.zone.zone_id
  records = ["${aws_acm_certificate.dev-cert.domain_validation_options.0.resource_record_value}"]
  ttl = 60
}

resource "aws_acm_certificate_validation" "dev-cert" {
  certificate_arn = aws_acm_certificate.dev-cert.arn
  validation_record_fqdns = ["${aws_route53_record.dev-cert_validation.fqdn}"]
}

# Create a load balancer to route traffic to the instances
resource "aws_elb" "dev-looker-elb" {
  name                        = "${var.env}-elb"
  subnets                     = ["${aws_subnet.subnet-looker.0.id}"]
  internal                    = "false"
  security_groups             = ["${aws_security_group.ingress-all-looker.id}"]
  instances                   = data.aws_instances.looker-instance-select.ids
  cross_zone_load_balancing   = true
  idle_timeout                = 3600
  connection_draining         = false
  connection_draining_timeout = 300
  tags = {
    owner = var.tag_email
  }

  listener {
    instance_port      = "9999"
    instance_protocol  = "https"
    lb_port            = "443"
    lb_protocol        = "https"
    ssl_certificate_id = aws_acm_certificate.dev-cert.arn
  }

  listener {
    instance_port      = "19999"
    instance_protocol  = "https"
    lb_port            = "19999"
    lb_protocol        = "https"
    ssl_certificate_id = aws_acm_certificate.dev-cert.arn
  }

  health_check {
    target              = "https:9999/alive"
    interval            = 30
    healthy_threshold   = 2
    unhealthy_threshold = 2
    timeout             = 5
  }
}

resource "aws_route53_record" "dev-looker-dns" {
  zone_id = data.aws_route53_zone.zone.zone_id
  name = "${var.env}.${var.domain}"
  type = "A"

  alias {
    name = aws_elb.dev-looker-elb.dns_name
    zone_id = aws_elb.dev-looker-elb.zone_id
    evaluate_target_health = false
  }
}

# Generate a random Looker password
resource "random_string" "password" {
  length = 10
  special = true
  number = true
  min_numeric = 1
  min_special = 1
  min_upper = 1
  override_special = "#%^*-="
}

output "user" {
  value = var.technical_contact_email
}

output "pass" {
  value = "abc_${random_string.password.result}"
}

output "host_url" {
  value = "https://${var.env}.${var.domain}"
}

output "looker_hosts" {
  value = aws_eip.ip-looker-env.*.public_dns
}

output "nfs_flag" {
  value = var.instances > 1 ? 1 : 0
}

output "key" {
  value = var.key
}

output "elb_name" {
  value = aws_elb.dev-looker-elb.name
}

output "db_identifier" {
  value = aws_db_instance.looker-app-db.*.identifier
}

output "efs_id" {
  value = aws_efs_file_system.looker-efs-fs.*.id
}

output "aws_region" {
  value = var.aws_region
}

output "aws_profile" {
  value = var.aws_profile
}
