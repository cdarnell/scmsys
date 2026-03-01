# Home Stack Delivery Plan

This repository is the canonical home lab source of truth.  All telemetry, automation, and AI runtimes should land here so they can be versioned, cited in issues, and tracked through the Gentoofoo GitHub Project: <https://github.com/cdarnell/scmsys/projects?query=is%3Aopen>.

## Mission

1. **Foundation for Metrics** – Prometheus + Vector + Loki + Grafana ship with sane defaults so every runtime advertises health immediately.
2. **Foundation for AI Bots** – ZeroClaw (and future "openclaw"-style runtimes) boot with HTTPS ingress (Traefik), pairing helpers, and observability hooks enabled.
3. **Operational Discipline** – Every stack documents its bootstrap, secrets model, and rollback so the board can drive predictable releases.

## Workstreams / Board Columns

| Column | Scope |
| --- | --- |
| **Backlog** | Ideas or tools we want soon (new bots, exporters, dashboards). |
| **Foundations** | Structural repo work: layout, secrets hygiene, shared tooling, documentation. |
| **ZeroClaw** | Gateway/planner/executor health, Telegram channel verification, pairing automation. |
| **Telemetry** | Observability-stack, Prometheus-stack, Ollama metrics, Windows agents. |
| **Review/Done** | Items validated locally (compose up, scripts tested) and ready to close. |

Link each issue/card back to these folders so context lives alongside code.

## Immediate Priorities (2026-03-01)

1. **ZeroClaw baseline**
   - [ ] Fill `deploy/secure-stack/.env` with current secrets.
   - [ ] `docker compose up -d` inside `zeroclaw/deploy/secure-stack`.
   - [ ] Run `automation/scripts/auto-pair-gateway.ps1 -Verbose` to mint a token.
   - [ ] Send a Telegram test message and verify gateway logs + Loki dashboard.
   - [ ] Capture the steps in `docs/operations-runbook.md` (link card to commit).
2. **Observability refresh**
   - [ ] Boot `observability-stack` (`docker compose up -d`).
   - [ ] Import dashboards automatically (Grafana provisioning already wired).
   - [ ] Verify Vector’s Windows + Docker sources and Loki integration.
   - [ ] Note any missing exporters and open backlog cards.
3. **Prometheus/Tesla hygiene**
   - [ ] Recreate `.env` from `.env.example` (never commit secrets).
   - [ ] Document token bootstrap flow (PKCE script, requirements) in `prometheus-stack/README.md`.
   - [ ] Add automation for certificate download/refresh if needed.
4. **Repo polish**
   - [ ] Remove stale path references (`SCMSYS/…`) in docs.
   - [ ] Ensure each stack has a README linking back to the Gentoofoo project.
   - [ ] Consider a root `Makefile`/`run.ps1` to orchestrate common flows.

## Tracking Checklist Template

Copy this block into new project cards so progress is visible without opening local files:

```
- [ ] .env / secrets prepared
- [ ] docker compose up -d
- [ ] Health endpoint checked
- [ ] Metrics/logs verified in Grafana
- [ ] Docs/runbook updated
```

## Notes

- Keep sensitive material out of Git.  `.env`, PEM files, and tokens belong on the host or in a password manager.
- Prefer `git mv` when reorganizing folders so history survives.
- When adding a new stack (for example `openclaw/`), copy the pattern from `zeroclaw/` and register it in this document + the project board immediately.
