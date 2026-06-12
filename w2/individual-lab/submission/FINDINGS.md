# Findings

## 1. Hardest Capability to Replace

Alerting and correlation was harder than storage because existing rules encode operational knowledge and currently produce ungrouped storms. I retained PagerDuty for paging, moved rule evaluation to Mimir/Loki, and added Alertmanager grouping plus service-graph inhibition. The compromise is continuing to pay $2,100/month for 35 PagerDuty responder seats instead of making paging fully OSS.

## 2. Resilience-for-Cost Trade-off

The design replaces independent Datadog/Splunk SaaS data planes with a Platform-operated Mimir/Loki/Tempo stack. That contributes most of the $23,610/month saving, but a total observability-stack outage could add an estimated 10 minutes of MTTR while responders fall back to two-region synthetic checks and application consoles. Multi-AZ replicas, S3 blocks, and the $4,800/month operations allocation reduce, but do not eliminate, that risk.

## 3. If the Required Cut Were 60%

A 60% cut requires a target below $16,800/month, versus this design's $18,390. I would replace PagerDuty Business with a lower-cost plan or OSS paging workflow and reduce Loki hot retention from 7 to 3 days, saving roughly $1,600/month. I would not reduce error/slow trace retention or remove Grafana correlation because those choices drive the root-cause-time target. This shows that paging seats, log compute, and operating labor dominate the remaining cost, not object storage.

## 4. Real-World Pattern Reused

The design copies Grafana's LGTM pattern: Loki for logs, Grafana for visualization, Tempo for traces, and Mimir for metrics, all using object storage and open telemetry formats. I changed it by adding an in-house PostgreSQL incident record and explicit service-graph-based Alertmanager inhibition to address GeekShop's missing decision audit and 47-page cascades.

## 5. Biggest Unknown

The biggest unknown is whether Loki can deliver p99 under 10 seconds for the team's common seven-day searches after indexing only bounded labels. If it fails, week 5 cannot safely remove Splunk. Week 1 therefore replays 2x the assumed 31.2 GB/day retained ingest and benchmarks the top 20 real queries before any production cut-over.

## POC Plan

The single most uncertain component is Loki. With three engineering days, replay representative structured and unstructured logs at **62.4 GB/day** equivalent into the proposed Loki topology, then run the top 20 incident and audit queries over seven-day and 30-day windows while one compactor runs. The assumption is confirmed only if p99 for common seven-day queries is under **10 seconds**, p99 for 30-day audit queries is under **30 seconds**, ingest loss is below **0.1%**, and projected Loki infrastructure remains below **$5,200/month** at that 2x load; otherwise choose Grafana Cloud Logs or revise indexing/retention before week 2.

