variable "region" {
  description = "OCI region identifier (e.g., us-ashburn-1)."
  type        = string
}

variable "compartment_ocid" {
  description = "OCID of the compartment that will own the instance."
  type        = string
}

variable "subnet_ocid" {
  description = "OCID of the subnet the VNIC should attach to (regional or AD-specific)."
  type        = string
}

variable "availability_domain" {
  description = "Availability domain name, e.g., kIdk:US-ASHBURN-AD-1."
  type        = string
}

variable "fault_domain" {
  description = "Optional fault domain label; leave empty to let OCI choose."
  type        = string
  default     = null
}

variable "shape" {
  description = "Compute shape. Default is the Ampere free-tier shape."
  type        = string
  default     = "VM.Standard.A1.Flex"
}

variable "ocpus" {
  description = "Number of OCPUs to allocate (1–4 in free tier)."
  type        = number
  default     = 4
}

variable "memory_in_gbs" {
  description = "RAM size in gigabytes (2–24 in free tier)."
  type        = number
  default     = 24
}

variable "image_ocid" {
  description = "OCID of the OS image to boot (must be ARM-compatible)."
  type        = string
}

variable "ssh_public_key" {
  description = "Public SSH key text to place in ~/.ssh/authorized_keys."
  type        = string
}

variable "cloud_init_user_data" {
  description = "Optional cloud-init user data (base64-encoded or plain)."
  type        = string
  default     = ""
}

variable "instance_name" {
  description = "Display name/hostname prefix for the instance."
  type        = string
  default     = "a1-flex-tf"
}

variable "hostname_label" {
  description = "Optional hostname label for the VNIC. Leave blank to skip."
  type        = string
  default     = ""
}

variable "assign_public_ip" {
  description = "Whether to assign a public IPv4 address."
  type        = bool
  default     = true
}

variable "assign_private_dns_record" {
  description = "Whether OCI should register a private DNS record for the VNIC."
  type        = bool
  default     = true
}

variable "assign_ipv6_ip" {
  description = "Whether to allocate an IPv6 address on the VNIC."
  type        = bool
  default     = false
}

variable "enable_network_security_group" {
  description = "Create a dedicated NSG and attach it to the instance VNIC."
  type        = bool
  default     = true
}

variable "allowed_ssh_cidrs" {
  description = "CIDR ranges allowed to reach SSH over the public interface (defaults to Tailscale CGNAT range)."
  type        = list(string)
  default     = ["100.64.0.0/10"]
}

variable "allowed_tailscale_udp_cidrs" {
  description = "CIDR ranges allowed to hit the Tailscale UDP port (set to 0.0.0.0/0 for NAT traversal)."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "capacity_reservation_id" {
  description = "Existing capacity reservation OCID (optional)."
  type        = string
  default     = ""
}

variable "boot_volume_size_in_gbs" {
  description = "Optional boot volume size override (GB)."
  type        = number
  default     = null
}

variable "boot_volume_vpus_per_gb" {
  description = "Optional boot volume VPUs per GB override."
  type        = number
  default     = null
}

variable "is_pv_encryption_in_transit_enabled" {
  description = "Enable paravirtualized volume encryption in transit."
  type        = bool
  default     = true
}

variable "defined_tags" {
  description = "Optional defined tags map."
  type        = map(string)
  default     = {}
}

variable "freeform_tags" {
  description = "Optional freeform tags map."
  type        = map(string)
  default     = {}
}

variable "enable_tailscale" {
  description = "Render a secure cloud-init profile that installs and enrolls Tailscale."
  type        = bool
  default     = false
}

variable "tailscale_auth_key" {
  description = "Ephemeral auth key created via https://login.tailscale.com/admin/settings/keys."
  type        = string
  default     = ""
  sensitive   = true
}

variable "tailscale_tags" {
  description = "Optional Tailscale ACL tags to advertise on the node."
  type        = list(string)
  default     = []
}

variable "tailscale_advertise_routes" {
  description = "CIDR routes (if any) this node should advertise to the tailnet."
  type        = list(string)
  default     = []
}

variable "tailscale_ssh" {
  description = "Enable Tailscale SSH for this node."
  type        = bool
  default     = true
}
