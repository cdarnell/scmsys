This folder contains Kubernetes manifest templates for deploying `tesla_collector`.

Files:

- `tesla-secret.example.yaml` — example Secret for client credentials / access token.
- `tesla-token-bootstrap-job.yaml` — bootstrap Job template (placeholder) to run PKCE/auth flow and write token into a Secret.
- `collector-deployment.yaml` — Deployment for the collector, includes Prometheus metrics containerPort and example liveness/readiness probes.
- `serviceaccount-rbac.yaml` — ServiceAccount, Role and RoleBinding allowing the collector to read secrets (used by bootstrap job / collector if needed).

Usage:

1. Copy `tesla-secret.example.yaml` to `tesla-secret.yaml`, fill values, and `kubectl apply -f tesla-secret.yaml`.
2. If you have a PKCE/automation script, adapt `tesla-token-bootstrap-job.yaml` to run it and write the token into a Secret.
3. Update the image in `collector-deployment.yaml` and `kubectl apply -f` the manifests.

When you're ready I can generate a fully opinionated set of manifests (namespace, probes, resource requests, HPA, etc.).
