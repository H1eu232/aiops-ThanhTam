# Cost Model

## Assumptions

- Prices are monthly USD estimates for `us-east-1`, June 2026, before negotiated discounts and tax.
- Current production scale is 300 hosts, 52 GB logs/day, approximately 470,000 active metric series, and 65 PagerDuty users.
- Log pipeline drops or samples 40% of low-value debug/health-check events; 31.2 GB/day reaches Loki. Hot logs are 7 days on SSD; compressed logs are retained 90 days in S3.
- Tail sampling retains 100% of errors, 20% of slow traces, and 5% of normal traces, estimated at 8% overall.
- Metrics have a 250,000-series budget after removing unbounded labels; hot query retention is 30 days and object retention is 13 months.
- Platform operations cost includes 0.4 FTE at a fully loaded $12,000/month. This avoids pretending OSS is free.
- AWS object-storage/request assumptions should be validated in the [AWS Pricing Calculator](https://calculator.aws/) against the public [S3 pricing page](https://aws.amazon.com/s3/pricing/). PagerDuty target pricing uses the current invoice's $60/user/month Business rate.

## Monthly Model

| Cost line | Unit driver and visible math | Assumed scale today | Today | Target |
|---|---|---:|---:|---:|
| Datadog APM hosts | $40/host | 295 host equivalents | $11,800 | $0 |
| Datadog infrastructure metrics | $18/host | 300 hosts | $5,400 | $0 |
| Datadog custom-metric overage | invoice usage | 440K excess series | $2,200 | $0 |
| Datadog indexed logs | $1.70/million events | 1.05B events/month | $1,800 | $0 |
| Splunk Cloud logs | workload + 52 GB/day | 30-day hot retention | $13,900 | $0 |
| PagerDuty Business | $60/user/month | 65 today; 35 target responders | $3,900 | $2,100 |
| Grafana Cloud mirror | active users | 18 active users | $1,050 | $0 |
| Statuspage | current Business tier | 1 tenant | $290 | $290 |
| Datadog Synthetics | $5/API check/month | 270 checks | $1,360 | $0 |
| Datadog tracing premium | add-on | 1 | $300 | $0 |
| OTel gateway and agents | 6 compute equivalents x $150 + $300 headroom | n/a | $0 | $1,200 |
| Mimir compute/cache | 8 compute equivalents x $250 + $600 cache/SSD | 250K active series | $0 | $2,600 |
| Loki compute + SSD hot tier | 8 compute equivalents x $250 + $1,100 SSD | 31.2 GB/day; 7 days | $0 | $3,100 |
| Tempo compute/cache | 4 compute equivalents x $250 + $250 cache | estimated 9.6 GB/day retained | $0 | $1,250 |
| S3 storage + requests | 8 TB x $0.023/GB-month + $462 requests/overhead | about 8 TB total retained blocks | $0 | $650 |
| Grafana, Alertmanager, Postgres, blackbox | 4 compute equivalents x $200 + $300 managed DB | 300 hosts; 270 checks | $0 | $1,100 |
| Network, backups, support reserve | 15% reserve on platform infrastructure | target stack | $0 | $1,300 |
| Platform operating labor | 0.4 FTE x $12,000/month | target stack | $0 | $4,800 |
| **Total** |  |  | **$42,000** | **$18,390** |

**Reduction:** `$42,000 - $18,390 = $23,610/month`, or **56.2%**. This leaves `$6,810/month` of headroom below the binding 40%-reduction ceiling of `$25,200/month`.

## Sensitivity

| Scenario | What changes | Target monthly cost | Budget result |
|---|---|---:|---|
| Expected | Volumes as assumed above | $18,390 | 56.2% reduction |
| Data volume grows 2x faster than projected | Loki compute/SSD +$2,100; Tempo +$650; Mimir +$650; S3/network +$700; reserve +$600 | $23,090 | Still 45.0% below today |
| First budget breaker | Logs exceed about 3x target retained ingest without further sampling | Above $25,200 | Loki SSD/read compute breaks the 40% target first |

## Controls

- Per-team log and metric budgets are reported weekly in Grafana.
- CI blocks unbounded metric labels; OTel gateway drops known debug/health-check noise.
- A 20% infrastructure alert fires at `$20,160/month`; a hard review gate fires at `$23,000/month`.

## Pricing Validation Notes

- Before procurement, replace each "compute equivalent" with the selected instance type and region in the [AWS Pricing Calculator](https://calculator.aws/); the model intentionally includes headroom instead of assuming perfect utilization.
- AWS states S3 is pay-as-used across storage, requests, retrieval, and transfer; the model includes request/overhead cost rather than charging only stored bytes. See [S3 pricing](https://aws.amazon.com/s3/pricing/).
- PagerDuty and Statuspage figures use the current invoices in `data-pack/current-stack.md`, avoiding an assumed contract discount.
