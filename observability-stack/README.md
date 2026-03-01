# Docker Observability Stack

A standalone Prometheus + Grafana bundle you can drop next to any Docker-based workload. It currently ships with scrape jobs tuned for the ZeroClaw secure stack, but you can point it at any publisher that exposes Prometheus metrics.

- `docker-compose.yml` – launches Prometheus (9090), Grafana (3001), Loki (3100), and the Vector collector (9598 / 6000) on Docker Desktop.
- `vector/vector.toml` – Vector aggregator pipeline that ingests Docker logs, receives remote Windows metrics, and exports Prometheus + Loki data.
- `loki/config.yml` – single-binary Loki config with 7-day on-disk retention for local log queries.
- `prometheus/prometheus.yml` – starter scrape config that watches the ZeroClaw gateway, planner, executor, memory, Traefik proxy, and the Vector exporter.
- `grafana/provisioning` – auto-provisions Prometheus + Loki datasources and loads dashboards on boot.
- `grafana/dashboards/**` – curated dashboards for ZeroClaw runtime, Docker hosts, Vector log health, Windows systems, and a log/metric correlation board.

## Getting Started
1. Make sure the target workloads are already running and that this stack can join their Docker network. By default we expect an external network named `secure-stack_zeroclaw_internal`; adjust `docker-compose.yml` if you want a different network.
2. Start the observability stack:
   ```powershell
   cd c:\Users\charl\projects\observability-stack
   docker compose up -d
   ```
3. Open Grafana at http://localhost:3001 (admin / admin) and look for the **ZeroClaw Performance**, **Vector Log Health**, **ZeroClaw Log Correlation**, and **Docker Host Overview** dashboards. Prometheus is reachable at http://localhost:9090, Loki at http://localhost:3100, and Vector exposes its own Prometheus exporter at http://localhost:9598/metrics (container DNS `observability-vector:9598`).

### Log correlation with Loki
1. Vector now ships every container log line (minus Grafana/Prometheus/Vector itself) into Loki with `job=zeroclaw`, `container`, `image`, and `level` labels. The ingest runs on the same Docker network, so no additional credentials are required.
2. Grafana provisions a **Loki** datasource automatically and the **ZeroClaw Log Correlation** dashboard combines Prometheus counters (error spikes, per-container rates) with live Loki logs. Click any metric series to jump straight into Explore with the corresponding container filter applied.
3. For ad-hoc hunts, use Grafana → Explore → Loki and run queries such as `{job="zeroclaw", level="error"} |= "panic"`. Use the `$container` and `$level` template variables inside the dashboard to keep metrics and logs filtered in lockstep.

### Windows desktop metrics (Vector agent on OMEN 3090)
1. From an elevated PowerShell prompt on the Windows desktop run:
   ```powershell
   cd c:\Users\charl\projects\observability-stack\windows-omen3090
   ./install-vector-agent.ps1 -Hostname "omen3090" -AggregatorHost "host.docker.internal" -AggregatorPort 6000
   ```
   The script installs the Vector Windows service, writes a host-specific config under `C:\ProgramData\Vector\config\windows-agent.toml`, and streams host metrics + Windows event counts to the Docker Vector collector.
2. Confirm `Get-Service vector` reports `Running` and inspect `C:\ProgramData\Vector\logs\vector.log` if you need troubleshooting data. Inside Docker, run `docker compose logs -f vector` to see inbound connections.
3. Visit http://localhost:9090/targets and ensure the `vector_aggregator` job is `UP`. The exporter combines Windows host metrics with Docker log-derived counters, so Grafana dashboards under *Windows Hosts* and *ZeroClaw* folders will light up automatically.

## Customizing for Other Publishers
- **Network name:** change the `metrics_backplane` external network in `docker-compose.yml` to match the Docker network used by the services you want to scrape.
- **Targets:** edit `prometheus/prometheus.yml` to add or remove jobs. For non-ZeroClaw services, swap in their container DNS names and metrics ports.
- **Dashboards:** drop additional JSON dashboards into `grafana/dashboards/` and they will be provisioned automatically.
- **Credentials:** override `GF_SECURITY_ADMIN_USER`/`GF_SECURITY_ADMIN_PASSWORD` env vars in `docker-compose.yml` before deploying to a shared environment.

This keeps observability portable: ZeroClaw can be one of many publishers, but any team can reuse the stack by pointing Prometheus at their own metrics endpoints.
