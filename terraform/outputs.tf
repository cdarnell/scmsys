output "instance_id" {
  description = "OCID of the created instance."
  value       = oci_core_instance.ampere.id
}

output "private_ip" {
  description = "Primary private IPv4 address."
  value       = data.oci_core_vnic.primary.private_ip_address
}

output "public_ip" {
  description = "Primary public IPv4 address (if assigned)."
  value       = data.oci_core_vnic.primary.public_ip_address
}
