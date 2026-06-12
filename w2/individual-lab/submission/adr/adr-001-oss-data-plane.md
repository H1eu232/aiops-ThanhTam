# ADR-001: Operate an OSS Telemetry Data Plane

**Status:** Accepted

## Context

The current $42,000/month stack duplicates telemetry across Datadog, Splunk, and Grafana Cloud while on-call engineers still open four UIs. Logs alone cost $15,700/month, and host/cardinality pricing adds another $19,400/month. The design must reduce spend by at least 40% without losing metrics, logs, tracing, SLOs, alerting, or audit search. OSS is not free, so the decision must include infrastructure and 0.4 FTE operating cost.

## Decision

Operate OpenTelemetry Collectors feeding Grafana Mimir, Loki, and Tempo on the existing cloud platform, with S3-backed retention and Grafana OSS as the primary query surface. Use independently scalable read/write components, multi-AZ replicas, infrastructure-as-code, tested backups, and explicit per-team telemetry budgets.

## Alternatives Considered

**Consolidate entirely on Datadog.** Rejected because it improves the UI problem but retains host, indexed-log, and cardinality pricing. It cannot credibly reach the 40% reduction without sharply reducing capabilities.

**Consolidate on Grafana Cloud.** Rejected for the first six-month target because managed operations are attractive, but ingest pricing at the current log volume leaves less cost headroom and creates another vendor migration. It remains the preferred fallback if the POC shows the team cannot operate Loki within the reliability budget.

**Use OpenSearch for all logs and traces.** Rejected because full-text indexing of all fields is operationally and financially heavier than Loki/Tempo for the dominant service, trace, deployment, and time-window queries.

## Consequences

Positive consequences are a single investigation UI, open protocols, rules-as-code, and a modeled cost of $18,390/month including labor. Data retention can grow primarily in object storage rather than premium SaaS indexes.

Negative consequences are that Platform/SRE now owns a production-critical observability system. A telemetry outage can impair diagnosis, LogQL offers weaker arbitrary full-text performance than Splunk, and engineers need training. The design reserves $4,800/month of labor, keeps two-region blackbox checks, and uses Grafana Cloud as a documented emergency fallback option.

