terraform {
  required_version = ">= 1.6.0"

  required_providers {
    oci = {
      source  = "oracle/oci"
      version = "~> 5.0"
    }
  }
}

provider "oci" {
  region = var.region
}

data "oci_core_subnet" "selected" {
  subnet_id = var.subnet_ocid
}

locals {
  enable_tailscale = var.enable_tailscale && var.tailscale_auth_key != ""
  tailscale_hostname = var.hostname_label != "" ? var.hostname_label : var.instance_name
  tailscale_tag_arg = length(var.tailscale_tags) > 0 ? "--advertise-tags=${join(",", var.tailscale_tags)}" : ""
  tailscale_routes_arg = length(var.tailscale_advertise_routes) > 0 ? "--advertise-routes=${join(",", var.tailscale_advertise_routes)}" : ""
  tailscale_accept_routes = length(var.tailscale_advertise_routes) > 0 ? "true" : "false"
  tailscale_ssh_flag = var.tailscale_ssh ? "true" : "false"
  rendered_default_cloud_init = local.enable_tailscale ? templatefile("${path.module}/cloud-init/secure-host.yaml", {
    tailscale_auth_key     = var.tailscale_auth_key
    tailscale_hostname     = local.tailscale_hostname
    tailscale_tag_arg      = local.tailscale_tag_arg
    tailscale_routes_arg   = local.tailscale_routes_arg
    tailscale_accept_routes = local.tailscale_accept_routes
    tailscale_ssh_flag     = local.tailscale_ssh_flag
    allowed_ssh_cidrs      = var.allowed_ssh_cidrs
  }) : ""
  rendered_cloud_init = var.cloud_init_user_data != "" ? var.cloud_init_user_data : (local.rendered_default_cloud_init != "" ? base64encode(local.rendered_default_cloud_init) : "")
  cloud_init_metadata = local.rendered_cloud_init != "" ? { user_data = local.rendered_cloud_init } : {}
  nsg_ids = var.enable_network_security_group ? oci_core_network_security_group.automation[*].id : []
}

resource "oci_core_network_security_group" "automation" {
  count          = var.enable_network_security_group ? 1 : 0
  compartment_id = var.compartment_ocid
  display_name   = "${var.instance_name}-nsg"
  vcn_id         = data.oci_core_subnet.selected.vcn_id
}

resource "oci_core_network_security_group_security_rule" "egress_all" {
  count                     = var.enable_network_security_group ? 1 : 0
  network_security_group_id = oci_core_network_security_group.automation[0].id
  direction                 = "EGRESS"
  protocol                  = "all"
  destination               = "0.0.0.0/0"
  destination_type          = "CIDR_BLOCK"
}

resource "oci_core_network_security_group_security_rule" "ssh" {
  for_each                  = var.enable_network_security_group ? { for cidr in var.allowed_ssh_cidrs : cidr => cidr } : {}
  network_security_group_id = oci_core_network_security_group.automation[0].id
  direction                 = "INGRESS"
  protocol                  = "6"

  tcp_options {
    destination_port_range {
      min = 22
      max = 22
    }
  }

  source      = each.value
  source_type = "CIDR_BLOCK"
}

resource "oci_core_network_security_group_security_rule" "tailscale_udp" {
  for_each                  = var.enable_network_security_group ? { for cidr in var.allowed_tailscale_udp_cidrs : cidr => cidr } : {}
  network_security_group_id = oci_core_network_security_group.automation[0].id
  direction                 = "INGRESS"
  protocol                  = "17"

  udp_options {
    destination_port_range {
      min = 41641
      max = 41641
    }
  }

  source      = each.value
  source_type = "CIDR_BLOCK"
}

resource "oci_core_instance" "ampere" {
  availability_domain = var.availability_domain
  compartment_id      = var.compartment_ocid
  display_name        = var.instance_name
  shape               = var.shape
  preserve_boot_volume = false
  is_pv_encryption_in_transit_enabled = var.is_pv_encryption_in_transit_enabled

  shape_config {
    memory_in_gbs = var.memory_in_gbs
    ocpus         = var.ocpus
  }

  create_vnic_details {
    subnet_id              = var.subnet_ocid
    assign_public_ip       = var.assign_public_ip
    assign_private_dns_record = var.assign_private_dns_record
    assign_ipv6ip          = var.assign_ipv6_ip
    display_name           = "${var.instance_name}-primary"
    hostname_label         = var.hostname_label
    skip_source_dest_check = false
    nsg_ids                = local.nsg_ids
  }

  metadata = merge({
    ssh_authorized_keys = var.ssh_public_key
  }, local.cloud_init_metadata)

  source_details {
    source_type            = "image"
    source_id              = var.image_ocid
    boot_volume_size_in_gbs = var.boot_volume_size_in_gbs
    boot_volume_vpus_per_gb = var.boot_volume_vpus_per_gb
  }

  fault_domain           = var.fault_domain
  capacity_reservation_id = var.capacity_reservation_id == "" ? null : var.capacity_reservation_id
  defined_tags            = var.defined_tags
  freeform_tags           = var.freeform_tags
}

# Grab networking info for outputs
data "oci_core_vnic_attachments" "primary" {
  compartment_id = var.compartment_ocid
  instance_id    = oci_core_instance.ampere.id
}

data "oci_core_vnic" "primary" {
  vnic_id = data.oci_core_vnic_attachments.primary.vnic_attachments[0].vnic_id
}
