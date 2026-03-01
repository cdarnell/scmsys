output "zeroclaw_runtime_role_id" {
  description = "Role ID for the zeroclaw-runtime AppRole."
  value       = vault_approle_auth_backend_role.zeroclaw_runtime.role_id
  sensitive   = true
}

output "automation_terraform_role_id" {
  description = "Role ID for the automation-terraform AppRole."
  value       = vault_approle_auth_backend_role.automation_terraform.role_id
  sensitive   = true
}

output "kv_mount_path" {
  description = "Actual KV v2 mount path."
  value       = vault_mount.kv.path
}
