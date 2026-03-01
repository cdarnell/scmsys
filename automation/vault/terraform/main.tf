provider "vault" {
  address = var.vault_addr != "" ? var.vault_addr : null
  token   = var.vault_token != "" ? var.vault_token : null
}

resource "vault_mount" "kv" {
  path        = var.kv_mount_path
  type        = "kv"
  description = "SCMSYS shared secrets"
  options = {
    version = "2"
  }
}

resource "vault_auth_backend" "approle" {
  type = "approle"
  path = var.approle_path
}

locals {
  runtime_data_path    = "${vault_mount.kv.path}/data/${var.zeroclaw_secret_path}"
  automation_data_path = "${vault_mount.kv.path}/data/${var.automation_secret_path}"
}

resource "vault_policy" "zeroclaw_runtime" {
  name   = "zeroclaw-runtime"
  policy = <<EOT
path "${local.runtime_data_path}" {
  capabilities = ["read"]
}
EOT
}

resource "vault_policy" "automation_terraform" {
  name   = "automation-terraform"
  policy = <<EOT
path "${local.automation_data_path}" {
  capabilities = ["read"]
}
EOT
}

resource "vault_approle_auth_backend_role" "zeroclaw_runtime" {
  backend              = vault_auth_backend.approle.path
  role_name            = "zeroclaw-runtime"
  token_policies       = [vault_policy.zeroclaw_runtime.name]
  token_ttl            = 3600
  token_max_ttl        = 86400
  secret_id_num_uses   = 0
  secret_id_ttl        = 0
  depends_on           = [vault_policy.zeroclaw_runtime]
}

resource "vault_approle_auth_backend_role" "automation_terraform" {
  backend              = vault_auth_backend.approle.path
  role_name            = "automation-terraform"
  token_policies       = [vault_policy.automation_terraform.name]
  token_ttl            = 3600
  token_max_ttl        = 86400
  secret_id_num_uses   = 0
  secret_id_ttl        = 0
  depends_on           = [vault_policy.automation_terraform]
}
