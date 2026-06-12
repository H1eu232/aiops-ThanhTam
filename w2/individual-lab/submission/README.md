# GeekShop Observability Redesign

Start with [architecture-target.mmd](architecture-target.mmd), then read [cost-model.md](cost-model.md) and [migration-plan.md](migration-plan.md). The design replaces fragmented Datadog/Splunk/Grafana telemetry with an OpenTelemetry-based Grafana OSS stack, while retaining PagerDuty for reliable paging. It targets a 56.2% monthly cost reduction and a 35% median time-to-root-cause reduction without an observability blackout during migration.

