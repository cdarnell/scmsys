automation/
# Automation

Align home stack and claws. This repo glues together the ZeroClaw runtime, the observability stack, and the Oracle Cloud automation helpers so the entire environment can be reproduced (and secured) on demand.

## Repo Layout

```
SCMSYS/
├── automation/                # You are here
│   ├── README.md
│   ├── observability-stack/
│   ├── terraform/
│   └── scripts/
└── zeroclaw/                  # Full ZeroClaw runtime snapshot (sibling project)
```

## Components at a Glance

- **ZeroClaw** – Canonical source tree now lives in the sibling folder `SCMSYS/zeroclaw` so the upstream runtime is versioned independently while still kept in this repo.
- **Observability Stack** – Docker Compose bundle with Prometheus, Grafana, dashboards for ZeroClaw/Ollama/Windows exporters, and provisioning rules baked in.
- **OCI Automation Helpers** – Terraform + cloud-init + a retry loop that keep nudging OCI until free-tier Ampere capacity appears, hardened with NSGs and optional Tailscale bootstrap.
- **Gateway Utilities** – `scripts/auto-pair-gateway.ps1` inspects the secure stack gateway, fetches the most recent pairing code, and automatically pairs a client (returning the bearer token for you).

## OCI Automation Helpers

This mini-project keeps a repeatable Terraform plan plus a bash loop that repeatedly applies the plan until Oracle Cloud Infrastructure (OCI) finally has enough Ampere A1 capacity. The workflow is designed to run inside OCI Cloud Shell so you do not need to keep your Windows workstation awake while OCI is "out of capacity".

### Prerequisites

1. **Terraform 1.6+** (already installed in OCI Cloud Shell).
2. **OCI credentials**: Cloud Shell inherits them. If running locally, configure `oci` CLI or provide a config file/instance principal.
3. **Values for:**
   - Compartment OCID
   - Subnet OCID (regional or AD-specific)
   - Availability Domain name (e.g., `kIdk:US-ASHBURN-AD-1`)
   - Image OCID for your preferred ARM build (Oracle Linux 8/9 ARM or Ubuntu 22.04 ARM)
   - SSH public key text
4. **Optional**: Capacity Reservation OCID if you successfully pre-reserved the A1 cores.

### Quick Start (Cloud Shell)

```bash
# 1) Clone or upload the automation folder
mkdir -p ~/projects && cd ~/projects
scp -r charl@windows:~/projects/automation ./   # or zip and upload via OCI console
cd automation/terraform

# 2) Copy the example tfvars and fill in your values
cat <<'EOF' > oci.auto.tfvars
region              = "us-ashburn-1"
compartment_ocid    = "ocid1.compartment.oc1..example"
subnet_ocid         = "ocid1.subnet.oc1..example"
availability_domain = "kIdk:US-ASHBURN-AD-1"
image_ocid          = "ocid1.image.oc1..example"
ssh_public_key      = "ssh-ed25519 AAAA... oracle-cloud"
shape               = "VM.Standard.A1.Flex"
ocpus               = 4
memory_in_gbs       = 24
# optional
# capacity_reservation_id = "ocid1.capacityreservation.oc1..example"
EOF

terraform init
```

Now jump back to the repo root and launch the retry loop:

```bash
cd ~/projects/automation
./scripts/retry-terraform.sh
```

The script will call `terraform apply -auto-approve` every 60 seconds until it succeeds. When OCI finally has spare capacity (or your reservation kicks in), the apply exits 0 and the loop stops.

### Customizing the Loop

`retry-terraform.sh` honors two environment variables:

- `INTERVAL` – seconds between retries (default: 60)
- `MAX_ATTEMPTS` – stop after N tries (default: infinite)

Example:

```bash
INTERVAL=30 MAX_ATTEMPTS=120 ./scripts/retry-terraform.sh
```

## Hardened access (Firewall + Tailscale)

The Terraform plan creates a dedicated Network Security Group (NSG) per instance and ships a hardened cloud-init profile that can auto-enroll the VM into your Tailscale tailnet.

- **NSG defaults**: inbound SSH is restricted to the Tailscale CGNAT range (`100.64.0.0/10`) and UDP/41641 is the only other port exposed publicly (needed for Tailscale DERP/NAT traversal). Override `allowed_ssh_cidrs`/`allowed_tailscale_udp_cidrs` if you need temporary access from a bastion.
- **Cloud-init**: set `enable_tailscale=true` and provide an ephemeral `tailscale_auth_key` (never commit it!). The template installs Tailscale, enables UFW with a deny-all policy, allows only loopback + `tailscale0`, opens SSH for tailnet peers, and turns on `tailscale up --ssh` with your chosen tags/routes.
- **Zero public exposure**: after Tailscale is confirmed you can deploy with `assign_public_ip=false` and reach ZeroClaw/Telegram tooling solely through the tailnet.

### Tailscale quick start

1. Generate an auth key at https://login.tailscale.com/admin/settings/keys (ephemeral, tagged as needed).
2. Extend your `oci.auto.tfvars`:
    ```hcl
    enable_tailscale           = true
    tailscale_auth_key         = "tskey-ephemeral-XXXX"
    tailscale_tags             = ["tag:automation", "tag:zeroclaw"]
    tailscale_advertise_routes = ["10.42.0.0/24"] # optional
    allowed_ssh_cidrs          = ["100.64.0.0/10", "100.115.92.0/23"]
    assign_public_ip           = false
    ```
3. `terraform apply` – cloud-init secures the box before any workloads run.
4. Use `tailscale ssh ubuntu@<tailnet-ip>` (or whichever user you create) and let ZeroClaw reach Telegram/OpenAI over the tunnel.

> **Tip:** Add your workstation’s public IP to `allowed_ssh_cidrs` only when you need a break-glass path; remove it once Tailscale access is verified.

INTERVAL=30 MAX_ATTEMPTS=120 ./scripts/retry-terraform.sh

## Secret management with HashiCorp Vault

All tokens and API keys now live in `automation/vault`. The folder includes a Docker Compose file for a single-node Vault, a hardened config, and Terraform that sets up the KV v2 engine plus AppRoles (`zeroclaw-runtime` and `automation-terraform`).

1. `cd automation/vault && docker compose up -d`
2. `vault operator init` (store the unseal keys/root token safely) and `vault operator unseal` twice
3. `cd automation/vault/terraform && terraform apply` to enable KV + AppRoles
4. `vault kv put kv/zeroclaw TELEGRAM_BOT_TOKEN="..." CLOUDFLARED_TUNNEL_TOKEN="..." ZC_API_KEY="..."`
5. `vault kv put kv/automation tailscale_auth_key="tskey-..."`

### Sync secrets into the workspace

Use the helper script before launching Docker Compose or Terraform:

```powershell
cd automation
pwsh ./scripts/sync-vault-secrets.ps1 `
    -UseAppRole `
    -RoleIdFile ./vault/.approle/zeroclaw-runtime-role-id `
    -SecretIdFile ./vault/.approle/zeroclaw-runtime-secret-id `
    -UseAutomationAppRole `
    -AutomationRoleIdFile ./vault/.approle/automation-terraform-role-id `
    -AutomationSecretIdFile ./vault/.approle/automation-terraform-secret-id
```

Results:

- Writes `zeroclaw/deploy/secure-stack/.env` with every key stored under `kv/zeroclaw`
- Exports `TF_VAR_tailscale_auth_key` from `kv/automation`
- Runs Terraform for you if you append `-TerraformArgs @('plan')`

If you already have a local `vault login`, the script will reuse `~/.vault-token`, so the AppRole files are optional.

## Auto-pair the secure gateway

When the ZeroClaw gateway container restarts it prints a single-use pairing code and expects the first client to `POST /pair` with the `X-Pairing-Code` header. The helper script automates that flow:

```powershell
cd $env:USERPROFILE\projects\automation\SCMSYS\automation
./scripts/auto-pair-gateway.ps1 -ClientName "zeroclaw_cli" -ClientContact "charl@local"
```

What it does:
- Calls the gateway health endpoint (via `docker compose exec gateway curl …`) to see if pairing is still required.
- Scrapes the latest pairing code from `docker compose logs gateway` (looks for `Send: POST /pair with header X-Pairing-Code: <code>`).
- Issues the pairing request from inside the container and prints the returned bearer token (optionally writes it to `-TokenOutFile`).

Use `-StackPath` if your secure stack lives somewhere else, and `-Force` if you intentionally cleared the existing paired tokens and want to re-run the workflow immediately.
