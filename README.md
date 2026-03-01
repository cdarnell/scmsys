<<<<<<< HEAD
# automation
Align home stack and claws
=======
# OCI Automation Helpers

This mini-project keeps a repeatable Terraform plan plus a bash loop that repeatedly applies the plan until Oracle Cloud Infrastructure (OCI) finally has enough Ampere A1 capacity. The workflow is designed to run inside OCI Cloud Shell so you do not need to keep your Windows workstation awake while OCI is "out of capacity".

## Repo Layout

```
automation/
├── README.md                  # You are here
├── terraform/                 # Terraform config for a single A1 Flex instance
│   ├── main.tf
│   ├── variables.tf
│   └── outputs.tf
└── scripts/
    └── retry-terraform.sh     # Bash loop that keeps running terraform apply
```

## Prerequisites

1. **Terraform 1.6+** (already installed in OCI Cloud Shell).
2. **OCI credentials**: Cloud Shell inherits them. If running locally, configure `oci` CLI or provide a config file/instance principal.
3. **Values for:**
   - Compartment OCID
   - Subnet OCID (regional or AD-specific)
   - Availability Domain name (e.g., `kIdk:US-ASHBURN-AD-1`)
   - Image OCID for your preferred ARM build (Oracle Linux 8/9 ARM or Ubuntu 22.04 ARM)
   - SSH public key text
4. **Optional**: Capacity Reservation OCID if you successfully pre-reserved the A1 cores.

## Quick Start (Cloud Shell)

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

## Customizing the Loop

`retry-terraform.sh` honors two environment variables:

- `INTERVAL` – seconds between retries (default: 60)
- `MAX_ATTEMPTS` – stop after N tries (default: infinite)

Example:

```bash
INTERVAL=30 MAX_ATTEMPTS=120 ./scripts/retry-terraform.sh
```

## Cleanup

When you're done with the VM:

```bash
cd automation/terraform
terraform destroy -auto-approve
```

That tears down the instance (and frees capacity) but keeps the retry tooling for next time.
>>>>>>> 9cbc933 (feat: init)
