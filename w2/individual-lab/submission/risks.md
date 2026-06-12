# Risk Register

| Risk | Likelihood | Impact | Specific mitigation | Owner |
|---|---|---|---|---|
| Loki cannot meet long-window query latency at 2x growth | Medium | High | Week-1 replay POC must meet p99 under 10s for the top 20 queries at 2x ingest; otherwise use Grafana Cloud Logs before production migration. | Observability lead |
| OSS stack outage blinds incident response | Medium | High | Run multi-AZ replicas, two-region blackbox checks, S3-backed data, quarterly restore tests, and retain old exporters through the week-8 gate. | Platform SRE manager |
| Sampling drops evidence required for audit or RCA | Medium | High | Exempt security/audit namespaces, retain 100% errors, version drop rules, and dual-ship raw logs to Splunk until Security signs a source-by-source evidence checklist. | Security engineering lead |
| Alert migration misses tribal-knowledge rules | High | High | Export all rules, map owner/runbook/test case, replay six months of incidents, and require 95% coverage plus zero missed synthetic Sev-1/2 pages. | Incident management lead |
| Team lacks Mimir/Loki/Tempo operating skill | High | Medium | Allocate 0.4 FTE, complete vendor-neutral training in weeks 1-4, pair each on-call with Platform for two rotations, and contract 40 hours of specialist support. | Platform director |
| Splunk renews before migration completes | Medium | High | Submit written non-renewal in week 1, obtain acknowledgement, export 100 GB/day during the contract window, and track the deadline in procurement plus the incident calendar. | Procurement owner |

