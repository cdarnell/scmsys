# Secure ZeroClaw Stack

This directory contains a hardened, TLS-terminated ZeroClaw deployment that splits the platform into four containers (gateway plus planner/executor/memory zerobots) behind a Traefik reverse proxy. Use this guide to supply secrets, provision certificates, and run the stack.

## Directory Layout

- `docker-compose.yml` – orchestrates the ZeroClaw services and Traefik proxy.
- `configs/` – agent configs plus Traefik static/dynamic configuration.
- `state/` – bind-mounted working directories for each service (created automatically on first run).
- `certs/` – place TLS keys, server certificates, and CA bundle here (never commit private keys).

## Prerequisites

1. Docker Engine + Compose Plugin (v2.20+ recommended).
2. ZeroClaw build dependencies (handled automatically by the multi-stage `Dockerfile`).
3. A running Ollama instance on the Docker host (defaults now talk to `http://host.docker.internal:11434`), or swap the configs to any other provider you prefer.
4. A mutually trusted PKI chain:
   - Offline `root-ca.pem` + `root-ca.key` (e.g., `Zeroclaw Root CA`).
   - Online `issuing-ca.pem` + `issuing-ca.key` (e.g., `Zeroclaw Issuing CA 01`).
   - Per-service leaf certificates signed by the issuing CA (e.g., `gateway.localhost`).
   - Client certificates for every caller (CLI, dashboards, automations) signed by the same issuing CA.

## Configure Secrets and Workspace

1. **Populate API keys** – by default each agent already points at `http://host.docker.internal:11434` with `default_provider = "ollama"`. Update those values under `configs/*/config.toml` (or via Docker secrets) if your Ollama endpoint lives elsewhere or if you later decide to re-enable a hosted provider. All configs reuse `/zeroclaw-data/workspace`; feel free to swap in dedicated workspaces per bot if desired.
2. **Optional environment overrides** – copy `.env.example` to `.env` to centralize settings such as alternative image tags or network names.
3. **Bootstrap workspaces** – drop any starter scripts, templates, or knowledge bases into the corresponding folder under `state/<service>/workspace` before launching. Containers run as UID/GID 65534, so keep permissions world-readable.

## Expose Ollama to the Stack

1. Install Ollama on the Docker host and run `ollama serve` (or the Windows/macOS tray app) with your chosen models pulled ahead of time, e.g. `ollama pull llama3.2`.
2. Ensure Docker Desktop is allowed to reach the host loopback; inside the containers the hostname `host.docker.internal` resolves back to the host, so the configs point at `http://host.docker.internal:11434` by default.
3. If your Ollama runtime lives elsewhere, change the `api_key` field (it doubles as the base URL for the Ollama driver) or export an override via `.env` and environment expansion.
4. To switch back to a hosted LLM, simply edit the same config fields with the remote provider token and model slug.

## Enable the Telegram Channel

1. **Create bot credentials** – Talk to [@BotFather](https://t.me/botfather) in Telegram, run `/newbot`, then copy the `bot_token` that BotFather prints. Use `@userinfobot` (or `Settings → Privacy & Security → Devices`) to note your numeric Telegram user ID.
2. **Populate secrets** – Optionally drop the token and allowlist ID into `.env` so you remember what to set (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_ALLOWED_USERS`). These values are documentation only—the actual runtime reads them from the TOML file.
3. **Fill in the channel config** – Edit `configs/telegram/config.toml` and replace `SET_TELEGRAM_BOT_TOKEN` and `YOUR_TELEGRAM_USER_ID` with the real values. All other defaults (Ollama provider, workspace path, throttles) already align with the rest of the stack. See [docs/channels-reference.md](docs/channels-reference.md) for every supported Telegram field (allowed users, streaming, mention_only, interrupts, etc.).
4. **Bring up the channel worker** – A dedicated `zeroclaw-telegram` service now exists in `docker-compose.yml`. After updating the config, run `docker compose up -d telegram-channel` (or `docker compose up -d` to restart the whole stack). The container executes `zeroclaw channel start`, reads your config, and opens the polling loop against Telegram’s Bot API on the internal network.
5. **Validate** – Tail `docker compose logs -f zeroclaw-telegram` to ensure `channel doctor` passes and the poller starts without errors. Send a test DM to your bot; you should see request/response logs, and the planner/executor pair will process the prompt via the shared workspace.
6. **Harden allowlists** – During initial testing you can temporarily set `allowed_users = ["*"]`, but narrow it to explicit IDs before exposing the bot to other users or groups. Optional extras like `mention_only = true` or `stream_mode = "partial"` can be toggled without restarts; the channel watcher hot-applies config edits.

## Provision Mutual TLS

1. Generate the CA hierarchy (root → issuing) and keep the root private key offline.
2. Create server keys/certs for each host Traefik will answer (e.g., `gateway.localhost`, `planner.localhost`).
3. Concatenate the server leaf plus issuing certificate into `gateway-fullchain.pem`, then copy it and the private key into `certs/`:
   ```powershell
   cp gateway-fullchain.pem certs/
   cp gateway.key certs/
   ```
4. Place `root-ca.pem` and `issuing-ca.pem` inside `certs/`. The Traefik static config already references these files and enforces `RequireAndVerifyClientCert` for every router.
5. Issue client certificates (e.g., `zeroclaw-admin`) and distribute `client-fullchain.pem` + `client.key` to each caller. Configure your HTTPS clients to send those credentials and to trust `root-ca.pem`.

## Build and Run

From the repository root:

```powershell
cd deploy/secure-stack
# Optional: build image with current sources
docker compose build
# Launch everything in the background
docker compose up -d
# Check health
docker compose ps
```

Traefik listens on `443` and forwards to the gateway/zerobots over the internal network. Point DNS (or your hosts file) for `gateway.localhost`, `planner.localhost`, etc. to the machine running the stack so certificates validate.

## Test the Gateway

Once the stack is live, you can hit the gateway through Traefik with any HTTPS client that trusts your root CA and presents a valid client certificate. For a quick smoke test:

```powershell
curl https://gateway.localhost/health \
   --cacert certs/root-ca.pem \
   --cert certs/client-fullchain.pem \
   --key certs/client.key
```

Replace the certificate paths with the actual locations on your workstation. A `200 OK` response means Traefik validated both sides of the TLS exchange and the gateway is reachable; from there you can begin issuing Zeroclaw tasks via the REST API or the `zeroclaw` CLI.
