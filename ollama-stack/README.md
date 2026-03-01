# Ollama Stack

Self-contained Docker Compose project for running Ollama with Prometheus-friendly metrics and feeding the existing observability stack (Prometheus + Grafana).

## Prerequisites

- Docker Desktop + Docker Compose v2
- External Docker network `metrics_network` (created by your observability stack)
- Prometheus + Grafana already running from `projects/observability-stack`

## Usage

1. From this directory run:
   ```powershell
   docker compose up -d
   ```
2. Pull a model and sanity-check the API:
   ```powershell
   docker exec -it ollama ollama pull llama3
   docker exec -it ollama ollama run llama3
   ```
3. Exposed endpoints:
   - API: http://localhost:11435
   - Metrics: http://localhost:11439/metrics

The container joins `metrics_network` so Prometheus can scrape it directly by service name.

## Prometheus Integration

`observability-stack/prometheus/prometheus.yml` already contains:
```yaml
- job_name: ollama
  static_configs:
    - targets: ["ollama:11439"]
```
After you start this stack, reload Prometheus (`curl -XPOST http://localhost:9090/-/reload`) and verify the target shows **UP** at http://localhost:9090/targets.

## Grafana Dashboard

An "Ollama Overview" dashboard lives at `observability-stack/grafana/dashboards/ollama/ollama-overview.json` and is auto-provisioned into Grafana. It charts:
- Request throughput and latency (p95)
- Prompt/completion token rates
- Queue depth
- CPU/GPU utilization and loaded models

Open Grafana at http://localhost:3001, navigate to the **Ollama Overview** dashboard under the *ZeroClaw* folder, and confirm metrics begin populating once you issue requests.

## Operational Notes

- Models persist inside the `ollama-models` Docker volume.
- If you need a different host port, adjust the `ports` section and keep Prometheus pointed at the container name/metrics port.
- Health checks use the local `/api/tags` endpoint; if you disable it, update `docker-compose.yml` accordingly.
