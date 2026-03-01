# scmsys Workspace

This repository now tracks every home stack from a single root so GitHub stays clean and predictable.

```
scmsys/
├── automation/            # OCI Terraform + helper scripts (see ./automation/README.md)
├── observability-stack/   # Prometheus/Grafana/Vector bundle with dashboards
├── ollama-stack/          # Ollama runtime bundle + docs
├── prometheus-stack/      # Tesla metrics collector + dashboards/tools
└── zeroclaw/              # Upstream ZeroClaw runtime snapshot for builds/tests
```

Add future stacks (for example `openclaw/`) directly under the repo root so they inherit the same Traefik/reverse-proxy/pairing workflow.
