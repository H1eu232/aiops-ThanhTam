# ADR-002: Preserve Diagnostic Traces and Reduce Logs at Ingest

**Status:** Accepted

## Context

Current tracing samples uniformly at 1%, hiding rare slow requests that caused at least two recent incidents. Meanwhile, 52 GB/day of logs drives the largest single cost category, and engineers mostly search by service, time, trace, and deployment. The redesign must improve root-cause speed while cutting storage cost.

## Decision

Use OTel gateway tail sampling to retain 100% of error traces, 20% of traces above service-specific latency thresholds, and 5% of normal traces, targeting about 8% overall. Attach trace IDs to structured logs. Drop health-check and known debug noise, rate-limit repeated messages, and sample low-value success logs so only 60% of current log bytes enter Loki. Retain 7 days hot and 90 days compressed in S3.

## Alternatives Considered

**Keep 1% head sampling and all logs.** Rejected because it preserves the exact diagnostic failure and cost structure the project must fix.

**Retain 100% of traces and aggressively delete logs.** Rejected because full trace retention is expensive and logs remain necessary for audit, database details, and code paths not fully instrumented.

**Sample all signal types uniformly.** Rejected because uniform sampling discards rare errors and tail latency precisely when they matter most; signal value is not uniform.

## Consequences

Positive consequences are materially better evidence for slow/error incidents, trace-to-log navigation, and a reduction from 52 to 31.2 GB/day of indexed logs. This directly supports the 35% median time-to-root-cause target.

Negative consequences are irreversible loss of dropped logs, delayed traces while the collector waits for decisions, and increased gateway memory requirements. Security/audit namespaces bypass sampling, all drop rules are version-controlled, and the migration dual-ships raw logs to Splunk until audit signs off.

