# Docker Observability Stack

A standalone Prometheus + Grafana bundle you can drop next to any Docker-based workload. It currently ships with scrape jobs tuned for the ZeroClaw secure stack, but you can point it at any publisher that exposes Prometheus metrics.

## Contents
- `docker-compose.yml` – launches Prometheus (9090) and Grafana (3001) on Docker Desktop.
- `prometheus/prometheus.yml` – starter scrape config that watches the ZeroClaw gateway, planner, executor, memory, and Traefik proxy.
- `grafana/provisioning` – auto-provisions a Prometheus datasource and loads dashboards on boot.
- `grafana/dashboards/zeroclaw-overview.json` – sample dashboard with Traefik latency, request rate, and scrape status cards.

## Getting Started
1. Make sure the target workloads are already running and that this stack can join their Docker network. By default we expect an external network named `secure-stack_zeroclaw_internal`; adjust `docker-compose.yml` if you want a different network.
2. Start the observability stack:
   ```powershell
   cd c:\Users\charl\projects\observability-stack
   docker compose up -d
   ```
3. Open Grafana at http://localhost:3001 (admin / admin) and look for the **ZeroClaw Performance** dashboard under the *ZeroClaw* folder. Prometheus is reachable at http://localhost:9090.

### Windows desktop metrics (OMEN 3090)
1. From an elevated PowerShell prompt on the Windows desktop run:
   ```powershell
   cd c:\Users\charl\projects\observability-stack\windows-omen3090
   ./install-windows-exporter.ps1
   ```
   This installs the Prometheus `windows_exporter` service on port 9182 and opens the firewall rule automatically.
2. Confirm http://localhost:9182/metrics returns data, then reload Prometheus targets at http://localhost:9090/targets. The `windows_omen3090` job should be `UP`.
3. Grafana now exposes an **OMEN 3090 Windows Overview** dashboard under the *Windows Hosts* folder with CPU, memory, disk, service, and network visualizations for the desktop.

## Customizing for Other Publishers
- **Network name:** change the `metrics_backplane` external network in `docker-compose.yml` to match the Docker network used by the services you want to scrape.
- **Targets:** edit `prometheus/prometheus.yml` to add or remove jobs. For non-ZeroClaw services, swap in their container DNS names and metrics ports.
- **Dashboards:** drop additional JSON dashboards into `grafana/dashboards/` and they will be provisioned automatically.
- **Credentials:** override `GF_SECURITY_ADMIN_USER`/`GF_SECURITY_ADMIN_PASSWORD` env vars in `docker-compose.yml` before deploying to a shared environment.

This keeps observability portable: ZeroClaw can be one of many publishers, but any team can reuse the stack by pointing Prometheus at their own metrics endpoints.
