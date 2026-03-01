# OMEN 3090 Vector Agent

This folder now ships a PowerShell helper that installs [Vector](https://vector.dev) as a Windows service and streams host metrics + Windows event counters directly into the Docker-based Vector collector that is part of the `observability-stack`.

## What You Get
- CPU, memory, disk, network, and process metrics via Vector's `host_metrics` collector.
- Windows event log density (error vs. warning vs. information) summarized as Prometheus counters.
- A secure TCP connection from Windows → Docker (no inbound firewall holes required) over `host.docker.internal:6000`.

## Prerequisites
- Administrator PowerShell session on the Windows desktop you want to monitor (OMEN 3090).
- Internet access to download the Vector MSI from the official release bucket.
- The Docker observability stack running locally so the `observability-vector` service is listening on port 6000.

## Install / Update the agent
```powershell
cd C:\Users\charl\projects\observability-stack\windows-omen3090
# Run as Administrator
./install-vector-agent.ps1 -Hostname "omen3090" -AggregatorHost "host.docker.internal" -AggregatorPort 6000
```

What the script does:
1. Downloads the requested Vector MSI (defaults to v0.42.0) and installs/updates the `vector` Windows service.
2. Writes `C:\ProgramData\Vector\config\windows-agent.toml` with a host-specific config that enables `host_metrics` and `windows_events` collectors.
3. Configures a Vector `vector` sink that streams metrics/log-derived counters to the Docker aggregator.
4. Restarts the Windows service so the new config takes effect immediately.

## Verification
1. Run `Get-Service vector` and confirm the status is `Running`.
2. Check `%ProgramData%\Vector\logs\vector.log` for `Connected` events referencing `host.docker.internal:6000`.
3. In Docker run `docker compose logs -f vector` and watch for `Accepted connection` entries.
4. Browse to http://localhost:9090/targets and ensure the `vector_aggregator` job is `UP`. The Grafana dashboard **OMEN 3090 Vector Overview** (under *Windows Hosts*) should begin plotting live data.

## Tweaking the agent
- Override `-Hostname` if you want the Grafana dashboards to display a different label.
- Pass `-EventChannels` (comma-separated) to monitor additional Event Log channels.
- Update `-VectorVersion` when new releases drop; rerun the script to in-place upgrade.

## Removal
```powershell
Get-Service vector | Stop-Service -Force
msiexec /x {VECTOR-PRODUCT-CODE}
Remove-Item "C:\\ProgramData\\Vector" -Recurse -Force
```
Then delete the Windows host entry from Grafana if desired and remove the `vector_aggregator` scrape job if you no longer need the collector.