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
  }

  metadata = {
    ssh_authorized_keys = var.ssh_public_key
    user_data           = var.cloud_init_user_data
  }

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
