# Eight-Week Migration Plan

## Guarantees and Success Measures

- No observability blackout: every cut-over uses dual-write during business hours; the old path remains live until the next gate passes.
- Every rollback is executable within 30 minutes by changing an OTel exporter/traffic flag, never by restoring data.
- Baseline: historical median MTTD is 11 minutes and median MTTR is 26 minutes. Six-month target is median first-root-cause hypothesis at or below 5.2 minutes, a 35% improvement from the reported 8-minute baseline.

| Week | Work and cut-over | Go/no-go gate | Rollback within 30 minutes |
|---|---|---|---|
| 1 | Inventory dashboards, alerts, integrations, data owners, and contracts. Build POC for Loki query performance and OTel tail sampling. File Splunk non-renewal before its 90-day deadline. | POC sustains 2x assumed ingest; p99 7-day common queries under 10s; audit queries identified. | No production cut-over; stop POC and select Grafana Cloud fallback if gate fails. |
| 2 | Deploy HA OTel gateways, S3 buckets, Mimir/Loki/Tempo, Grafana, and monitoring for the monitoring stack. Start telemetry from staging. | Multi-AZ failure test loses no accepted telemetry; recovery under 15 minutes; backups restore successfully. | Route staging exporters back to existing tools and destroy no old resources. |
| 3 | Instrument production services and dual-write metrics/traces to Datadog and new stack. Enable metadata standards and cardinality checks in warn-only mode. | 98% of services emit required labels; metric delta under 2%; collector drop under 0.1%. | Disable new exporters via feature flag; Datadog agents remain untouched. |
| 4 | Enable trace tail sampling and service graph in shadow mode. Rebuild critical dashboards/SLOs in Grafana; train on-call with two synthetic incidents. | 100% error traces retained in test; 95% critical dashboards reproduced; two on-call engineers independently identify root cause within 6 minutes. | Revert to head sampling/new exporter off; Datadog APM remains primary. |
| 5 | Dual-ship logs to Splunk and Loki. Apply drop/sampling rules only on Loki path; validate audit exports and 7/30/90-day search behavior. | 100% compliance sources present; p99 7-day common query under 10s; sampled pipeline reaches 35%+ byte reduction without losing test incident evidence. | Switch Grafana links back to Splunk; raw Splunk forwarding continues unchanged. |
| 6 | Reproduce alerts as code in Mimir/Loki, add fingerprint grouping and service-graph inhibition, and send shadow notifications without paging. | 95% of historical actionable rules reproduced; zero missed synthetic pages; alert storm collapses 47 events to at most 4 grouped incidents. | Disable new receiver; existing Datadog/Splunk-to-PagerDuty integrations remain active. |
| 7 | Cut primary investigation surface to Grafana and primary paging source to Alertmanager. Enable incident record service. Freeze new vendor-specific rules. | On-call completes a 48-hour rotation with no missed pages; median synthetic first hypothesis under 5.2 minutes; audit trail captures 100% of actions. | Re-enable old PagerDuty integrations and publish old-tool incident runbook; dual-write remains active. |
| 8 | Stop Datadog ingest, reduce PagerDuty to 35 responders, and stop Splunk ingest after security sign-off; retain read access/export per contract. | Seven stable days; cost run-rate under $23,000; no Sev-1/2 evidence gaps; executive and security approval. | Re-enable Datadog exporters immediately; restore Splunk forwarding before contract end; keep 30-day Datadog reactivation budget. |

## Six-Month Outcome Review

Track monthly spend, page-group ratio, first-hypothesis time, median MTTD/MTTR, query p99, telemetry loss, and repeated remediation actions. The project succeeds only if monthly cost is at most $25,200 and median first-hypothesis time improves by at least 30%.

