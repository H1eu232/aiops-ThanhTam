# Component Decisions

| Capability | Choice | Why this one | What gets worse if changed in six months |
|---|---|---|---|
| Metrics ingestion, storage, query | OpenTelemetry Collector + Grafana Mimir | Prometheus-compatible queries preserve existing staging knowledge while object storage and horizontal scaling remove host and cardinality-based SaaS pricing. | Migrating recording rules, SLO queries, and long-retention blocks to a non-PromQL system becomes expensive. |
| Logs ingestion, storage, search | OTel Collector + Grafana Loki + S3 | Label-indexed structured logs make the common service/trace/deploy searches cheap while retaining raw compressed logs for audit. | Teams lose LogQL knowledge and must rebuild audit exports and saved searches. |
| Distributed tracing | OTel SDK/Collector + Grafana Tempo | Tail sampling retains all errors and slow traces, and Tempo integrates trace-to-log, exemplars, and service graphs in Grafana. | Instrumentation remains portable, but stored trace history and Grafana correlations must be rebuilt. |
| Alerting and correlation/grouping | Mimir ruler + Alertmanager + Grafana service graph | Rules-as-code plus inhibition and fingerprint grouping directly addresses 47-page alert storms and shows likely upstream causes. | Alert-rule migration and tuned grouping/inhibition logic must be repeated and revalidated. |
| Incident routing and paging | PagerDuty Business, reduced from 65 to 35 responder seats | Paging reliability, schedules, and escalations are not the place to take migration risk; non-responders use Grafana incident records. | Replacing it later means re-testing every schedule, escalation policy, and compliance control. |
| Dashboards and SLO tracking | Grafana OSS + Sloth-generated SLO rules | One UI queries all three signals and supports service-centric navigation, while SLOs remain version-controlled PromQL. | Dashboard JSON is portable, but plugins, links, and SLO workflows need adjustment. |
| Synthetic checks | Prometheus Blackbox Exporter in two regions | It covers HTTP, TCP, TLS-expiry, and critical user-path checks without per-check SaaS pricing. | Losing independent SaaS probes reduces confidence during a total cloud-region failure. |
| Incident audit and pattern search | Small in-house incident record service on PostgreSQL | PagerDuty webhooks plus operator actions create a searchable 90-day decision trail with service/action fields. | Its schema/API creates a small maintenance burden and must be exported before replacement. |

## Operating Principles

- Grafana is the first investigation surface; PagerDuty is only for page acknowledgement and escalation.
- Telemetry must carry `service.name`, `team`, `env`, `region`, `deployment.version`, and `trace_id`.
- CI rejects metrics containing unapproved unbounded labels such as `customer_id`.
- Paging is reserved for actionable user-impact symptoms; low-criticality standalone failures create tickets.

