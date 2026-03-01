# OMEN 3090 Windows Metrics Bridge

This folder ships a PowerShell helper that installs and configures the Prometheus `windows_exporter` service on your Windows desktop so the `observability-stack` can scrape host CPU, memory, disk, network, and service metrics.

## Prerequisites
- Administrator PowerShell session on the Windows desktop you want to monitor (OMEN 3090 in this case).
- Internet access to download the `windows_exporter` MSI from GitHub.
- The Docker-based observability stack running locally (so Prometheus can reach `host.docker.internal:9182`).

## Install / Update the exporter
```powershell
cd C:\Users\charl\projects\observability-stack\windows-omen3090
# Run as Administrator
./install-windows-exporter.ps1
```

What the script does:
1. Downloads the specified `windows_exporter` release (defaults to v0.25.1) from GitHub.
2. Installs or upgrades the exporter as a Windows service that listens on `:9182` and enables the `cpu,cs,logical_disk,net,os,service,system,textfile` collectors.
3. Opens an inbound firewall rule for TCP/9182.
4. Restarts the `windows_exporter` service if it was already present.

If you want a different port or collector set, pass parameters:
```powershell
./install-windows-exporter.ps1 -Version "0.25.1" -ListenPort 9183 -Collectors "cpu,logical_disk,net"
```

## Verification
1. Browse to http://localhost:9182/metrics on the Windows desktop – you should see Prometheus metrics.
2. Inside the observability stack run `docker compose logs -f prometheus` and confirm the new `windows_omen3090` target shows `UP` in http://localhost:9090/targets.
3. Grafana (http://localhost:3001) now includes an **OMEN 3090 Windows Overview** dashboard under the *Windows Hosts* folder.

## Troubleshooting
- **Port already in use**: change the `-ListenPort` parameter and update `prometheus/prometheus.yml` accordingly (job `windows_omen3090`).
- **Firewall blocked**: rerun the script; it always (re)creates the rule named `Prometheus Windows Exporter 9182`. Ensure corporate AV policies allow the binary.
- **Collectors missing**: edit the script or reinstall manually using `msiexec /i windows_exporter.msi ENABLECOLLECTORS=...`.

## Removal
To uninstall the exporter:
```powershell
Get-Service windows_exporter | Stop-Service -Force
msiexec /x {B2EC2BFE-EXPORTER-GUID}
Remove-Item "C:\\Program Files\\windows_exporter" -Recurse -Force
Remove-NetFirewallRule -DisplayName "Prometheus Windows Exporter 9182"
```
(Replace the GUID with the value shown in *Apps & Features*).