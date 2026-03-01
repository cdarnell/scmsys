variable "vault_addr" {
  description = "Vault HTTP address. Leave empty to use VAULT_ADDR."
  type        = string
  default     = ""
}

variable "vault_token" {
  description = "Admin token used for provisioning. Leave empty to use VAULT_TOKEN."
  type        = string
  default     = ""
  sensitive   = true
}

variable "kv_mount_path" {
  description = "Mount path for the KV v2 secrets engine."
  type        = string
  default     = "kv"
}

variable "zeroclaw_secret_path" {
  description = "KV path that stores runtime secrets consumed by Docker Compose."
  type        = string
  default     = "zeroclaw"
}

variable "automation_secret_path" {
  description = "KV path that stores automation secrets (for Terraform, etc.)."
  type        = string
  default     = "automation"
}

variable "approle_path" {
  description = "Auth backend path for the AppRole engine."
  type        = string
  default     = "approle"
}
