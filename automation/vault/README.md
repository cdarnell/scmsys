# Vault Scaffold

This folder runs a single-node HashiCorp Vault instance for local development and wires policies/AppRoles that the rest of the SCMSYS stack can consume.

> This setup disables TLS and mlock for simplicity. Keep it on a trusted network only. For production, move to HCP Vault or a hardened cluster.

## 1. Launch Vault

```powershell
cd automation/vault
mkdir data 2>$null
# Optional: persist env vars
setx VAULT_ADDR "http://127.0.0.1:8200"
# Start the server
docker compose up -d
```

Inspect the container:

```powershell
docker compose logs -f
```

## 2. Initialize and unseal (run once)

```powershell
$env:VAULT_ADDR = "http://127.0.0.1:8200"
vault operator init -key-shares=3 -key-threshold=2 > init.txt
```

Secure the generated unseal keys and root token (never commit `init.txt`). Unseal using any 2 keys:

```powershell
vault operator unseal
vault operator unseal
vault login <root-token>
```

Vault stores its data under `automation/vault/data`, so secrets survive container restarts.

## 3. Provision policies and AppRoles with Terraform

```powershell
cd automation/vault/terraform
$env:VAULT_ADDR = "http://127.0.0.1:8200"
$env:VAULT_TOKEN = <root-token-or-admin-token>
terraform init
terraform apply
```

The module enables the KV v2 engine at `kv/`, creates two policies, and registers AppRoles:

- `zeroclaw-runtime` → read-only access to `kv/data/zeroclaw` (Docker Compose envs)
- `automation-terraform` → read-only access to `kv/data/automation` (Terraform inputs such as Tailscale keys)

After `apply`, capture the role IDs and generate matching secret IDs:

```powershell
cd automation/vault
mkdir .approle 2>$null
vault read -field=role_id auth/approle/role/zeroclaw-runtime/role-id > .approle/zeroclaw-runtime-role-id
vault read -field=role_id auth/approle/role/automation-terraform/role-id > .approle/automation-terraform-role-id
vault write -f -field=secret_id auth/approle/role/zeroclaw-runtime/secret-id > .approle/zeroclaw-runtime-secret-id
vault write -f -field=secret_id auth/approle/role/automation-terraform/secret-id > .approle/automation-terraform-secret-id
```

`.approle/` is gitignored so you can safely park these files locally.

## 4. Load secrets into KV v2

Populate the mounts once (rotate whenever needed):

```powershell
vault kv put kv/zeroclaw `
  TELEGRAM_BOT_TOKEN="1234567890:ABCDEF" `
  CLOUDFLARED_TUNNEL_TOKEN="eyJhIjoi" `
  ZC_API_KEY="zeroclaw-local"

vault kv put kv/automation `
  tailscale_auth_key="tskey-ephemeral-XXX" `
  openai_api_key="sk-live-XXX"    # optional placeholder
```

Add additional keys at will; the sync script writes all key/value pairs into the `.env` file.

## 5. Use the secrets everywhere

Run the helper script before starting Docker Compose or Terraform:

```powershell
cd automation
pwsh ./scripts/sync-vault-secrets.ps1 -UseAppRole \
  -RoleIdFile ./vault/.approle/zeroclaw-runtime-role-id \
  -SecretIdFile ./vault/.approle/zeroclaw-runtime-secret-id \
  -UseAutomationAppRole \
  -AutomationRoleIdFile ./vault/.approle/automation-terraform-role-id \
  -AutomationSecretIdFile ./vault/.approle/automation-terraform-secret-id
```

- Writes `zeroclaw/deploy/secure-stack/.env` using `kv/zeroclaw`
- Fetches `tailscale_auth_key` (and any other automation keys) from `kv/automation`
- Optionally runs Terraform if you append `-TerraformArgs @('plan')`

Repeat the command whenever secrets change (for example, after rotating a Telegram bot token).
