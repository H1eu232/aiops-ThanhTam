import sys

def calculate_costs():
    # Input pricing constants
    DATADOG_LOG_INGEST_GB = 0.10
    DATADOG_LOG_INDEX_GB = 2.40  # Ingestion + 30-day retention indexing
    DATADOG_METRIC_SERIES_MONTH = 0.05  # Custom metric series per month
    
    AWS_GP3_STORAGE_GB_MONTH = 0.08
    AWS_S3_STORAGE_GB_MONTH = 0.023
    AWS_NAT_GATEWAY_GB = 0.045
    AWS_INTER_AZ_GB = 0.01
    
    ENGINEER_MONTHLY_SALARY = 12500.0  # Assumes $150,000/year fully loaded cost
    
    # Scale tiers
    tiers = {
        "Small": {
            "services": 10,
            "logs_gb_day": 50,
            "metric_events_sec": 100_000,
            # We assume metric events are sent every 10s on average, leading to active series:
            "active_metric_series": 1_000_000,
            # Infrastructure sizing
            "vm_compute": 35.0,  # 1x t3.medium / c6g.large
            "es_compute": 230.0,  # 3x m6g.large
            "kafka_compute": 100.0,  # 3x t3.medium
            "flink_compute": 150.0,  # 2x c6g.large
            "fte_required": 0.20,
            "datadog_discount": 0.0,
        },
        "Medium": {
            "services": 100,
            "logs_gb_day": 500,
            "metric_events_sec": 1_000_000,
            "active_metric_series": 10_000_000,
            # Infrastructure sizing
            "vm_compute": 450.0,  # 3x c6g.xlarge
            "es_compute": 770.0,  # 5x m6g.xlarge
            "kafka_compute": 300.0,  # 3x r6g.large
            "flink_compute": 600.0,  # 4x c6g.xlarge
            "fte_required": 0.50,
            "datadog_discount": 0.20,  # 20% enterprise discount
        },
        "Large": {
            "services": 1000,
            "logs_gb_day": 5000,
            "metric_events_sec": 10_000_000,
            "active_metric_series": 100_000_000,
            # Infrastructure sizing
            "vm_compute": 1800.0,  # 6x c6g.2xlarge
            "es_compute": 4800.0,  # 12x r6g.2xlarge
            "kafka_compute": 1200.0,  # 6x r6g.xlarge
            "flink_compute": 2400.0,  # 8x c6g.2xlarge
            "fte_required": 1.50,
            "datadog_discount": 0.40,  # 40% enterprise volume discount
        }
    }
    
    results = {}
    
    for tier_name, config in tiers.items():
        # --- BUY (DATADOG) COST ---
        # Logs cost
        logs_monthly_gb = config["logs_gb_day"] * 30
        dd_logs_cost = logs_monthly_gb * (DATADOG_LOG_INGEST_GB + DATADOG_LOG_INDEX_GB)
        
        # Metrics cost
        dd_metrics_cost = config["active_metric_series"] * DATADOG_METRIC_SERIES_MONTH
        
        # Total list price
        dd_total_list = dd_logs_cost + dd_metrics_cost
        dd_total_discounted = dd_total_list * (1.0 - config["datadog_discount"])
        
        # --- BUILD (SELF-HOSTED) COST ---
        # Storage sizing (Assume 30 days retention)
        # VictoriaMetrics: highly compressed, ~0.5 bytes per sample.
        # total samples = metric_events_sec * 86400 * 30
        total_samples_month = config["metric_events_sec"] * 86400 * 30
        vm_storage_gb = (total_samples_month * 0.5) / (1024**3)
        vm_storage_cost = vm_storage_gb * AWS_GP3_STORAGE_GB_MONTH
        
        # Elasticsearch logs storage: 50% indexing overhead, 30 days
        es_storage_gb = config["logs_gb_day"] * 1.5 * 30
        es_storage_cost = es_storage_gb * AWS_GP3_STORAGE_GB_MONTH
        
        total_storage_cost = vm_storage_cost + es_storage_cost
        
        # Compute cost
        total_compute_cost = (
            config["vm_compute"] +
            config["es_compute"] +
            config["kafka_compute"] +
            config["flink_compute"]
        )
        
        # Network cost (Ingress + Cross-AZ + NAT Gateway)
        # logs_gb_month + metrics_gb_month (estimate metrics are 1/5th size of logs in raw format)
        raw_ingress_gb_month = logs_monthly_gb * 1.2
        network_cost = raw_ingress_gb_month * (AWS_NAT_GATEWAY_GB + AWS_INTER_AZ_GB)
        
        # Engineering overhead
        eng_cost = config["fte_required"] * ENGINEER_MONTHLY_SALARY
        
        build_infra_cost = total_storage_cost + total_compute_cost + network_cost
        build_total_cost = build_infra_cost + eng_cost
        
        results[tier_name] = {
            "config": config,
            "datadog": {
                "logs": dd_logs_cost,
                "metrics": dd_metrics_cost,
                "total": dd_total_discounted,
                "discount": config["datadog_discount"]
            },
            "build": {
                "storage": total_storage_cost,
                "compute": total_compute_cost,
                "network": network_cost,
                "infra_total": build_infra_cost,
                "engineering": eng_cost,
                "total": build_total_cost
            }
        }
    
    # Print Markdown Table
    print("# AIOps Cost Estimation Comparison: Build vs Buy\n")
    print("| Tier | Scale Details | Component | Buy (Datadog Monthly) | Build (AWS Self-Host Monthly) |")
    print("|:---|:---|:---|:---|:---|")
    
    for tier, res in results.items():
        cfg = res["config"]
        dd = res["datadog"]
        bld = res["build"]
        
        scale_str = f"- {cfg['services']} services<br>- {cfg['logs_gb_day']} GB logs/day<br>- {cfg['metric_events_sec']:,} events/s"
        
        # Format strings
        dd_discount_pct = f" (after {int(dd['discount']*100)}% disc.)" if dd['discount'] > 0 else ""
        
        print(f"| **{tier}** | {scale_str} | **Compute** | - | ${bld['compute']:,.2f} |")
        print(f"| | | **Storage** | ${dd['logs']:,.2f} (Logs) | ${bld['storage']:,.2f} (VM + ES) |")
        print(f"| | | **Metrics** | ${dd['metrics']:,.2f} | - |")
        print(f"| | | **Network** | Included | ${bld['network']:,.2f} |")
        print(f"| | | **Engineering** | Included | ${bld['engineering']:,.2f} ({cfg['fte_required']} FTE) |")
        print(f"| | | **TOTAL** | **${dd['total']:,.2f}**{dd_discount_pct} | **${bld['total']:,.2f}** (Infra: ${bld['infra_total']:,.2f}) |")
        print("| | | | | |")

if __name__ == "__main__":
    calculate_costs()
