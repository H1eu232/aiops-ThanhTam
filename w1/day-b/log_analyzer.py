#!/usr/bin/env python3
"""
Mini Log Analyzer using Drain3
Analyzes log files and detects anomalies via template analysis
"""

import sys
import re
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from drain3 import TemplateMiner
from drain3.template_miner_config import TemplateMinerConfig

# Log pattern (supports both HDFS and BGL formats)
HDFS_PATTERN = re.compile(r'^(\d+)\s+(\d+)\s+(\d+)\s+(\w+)\s+([^:]+):\s+(.*)$')
BGL_PATTERN = re.compile(r'^(?:\S+)\s+(\d+)\s+(?:\S+)\s+(\S+)\s+(?:\S+)\s+(?:\S+)\s+(?:\S+)\s+(\S+)\s+(\S+)\s+(.*)$')

def analyze_log_file(filepath, drain_sim_th=0.5):
    """Analyze log file and return analysis results"""

    # Initialize Drain3
    config = TemplateMinerConfig()
    config.drain_sim_th = drain_sim_th
    config.drain_depth = 4
    miner = TemplateMiner(config=config)

    parsed_logs = []
    total_lines = 0
    timestamps = []

    # Parse log file
    with open(filepath, 'r') as f:
        for line in f:
            total_lines += 1

            # Try HDFS pattern first, then BGL
            match = HDFS_PATTERN.match(line.strip())
            if match:
                date, time, pid, level, component, message = match.groups()
                try:
                    timestamp = pd.to_datetime(f"20{date[:2]}-{date[2:4]}-{date[4:]} {time[:2]}:{time[2:4]}:{time[4:]}")
                except:
                    timestamp = None
            else:
                match = BGL_PATTERN.match(line.strip())
                if match:
                    ts, node, type_, level, message = match.groups()
                    try:
                        timestamp = pd.to_datetime(float(ts), unit='s')
                    except:
                        timestamp = None
                else:
                    continue

            # Parse with Drain3
            result = miner.add_log_message(message)
            parsed_logs.append({
                'timestamp': timestamp,
                'message': message,
                'template_id': result['cluster_id'],
                'template': result['template_mined']
            })
            timestamps.append(timestamp)

    df = pd.DataFrame(parsed_logs)
    unique_templates = len(miner.drain.clusters)

    # Generate template statistics
    template_summary = df.groupby(['template_id', 'template']).size().reset_index(name='count')
    template_summary['percentage'] = (template_summary['count'] / len(df) * 100).round(2)
    template_summary = template_summary.sort_values('count', ascending=False)

    # Top-5 templates
    top_5 = template_summary.head(5)

    # Detect spikes in last hour
    one_hour_ago = max(df['timestamp']) - timedelta(hours=1) if max(df['timestamp']) else None
    if one_hour_ago:
        recent_logs = df[df['timestamp'] >= one_hour_ago]
        recent_templates = recent_logs.groupby('template_id').size()

        # Compare with historical average
        historical_avg = df.groupby('template_id').size().mean()
        spikes = recent_templates[recent_templates > 2 * historical_avg]
        spike_templates = [
            {'template_id': tid, 'recent_count': recent_templates[tid]}
            for tid in spikes.index
        ]
    else:
        spike_templates = []

    # Detect new templates (first in last hour)
    if one_hour_ago:
        old_data = df[df['timestamp'] < one_hour_ago]
        recent_data = df[df['timestamp'] >= one_hour_ago]

        old_templates = set(old_data['template_id'].unique())
        recent_templates_set = set(recent_data['template_id'].unique())
        new_templates_ids = recent_templates_set - old_templates

        new_templates = [
            {
                'template_id': tid,
                'template': df[df['template_id'] == tid]['template'].iloc[0],
                'first_time': recent_data[recent_data['template_id'] == tid]['timestamp'].min()
            }
            for tid in new_templates_ids
        ]
    else:
        new_templates = []

    return {
        'total_lines': total_lines,
        'unique_templates': unique_templates,
        'top_5_templates': top_5,
        'spike_templates': spike_templates,
        'new_templates': new_templates,
        'dataframe': df
    }

def print_report(results, filepath):
    """Print formatted analysis report"""

    print("\n" + "="*70)
    print(f"LOG ANALYSIS REPORT: {filepath}")
    print("="*70)

    print(f"\n[1] SUMMARY")
    print(f"  Total log lines:        {results['total_lines']:,}")
    print(f"  Unique templates:       {results['unique_templates']}")

    print(f"\n[2] TOP-5 TEMPLATES")
    for idx, row in results['top_5_templates'].iterrows():
        print(f"  {idx+1}. [ID {row['template_id']:3d}] ({row['percentage']:5.2f}%) {row['count']:6d} logs")
        print(f"     Template: {row['template'][:70]}")

    print(f"\n[3] TEMPLATE SPIKES (in last hour)")
    if results['spike_templates']:
        for item in results['spike_templates']:
            print(f"  - Template {item['template_id']}: {item['recent_count']} recent logs")
    else:
        print("  No significant spikes detected")

    print(f"\n[4] NEW TEMPLATES (appeared in last hour)")
    if results['new_templates']:
        for item in results['new_templates']:
            print(f"  - [ID {item['template_id']}] {item['template'][:70]}")
    else:
        print("  No new templates detected")

    print(f"\n" + "="*70 + "\n")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(f"Usage: python log_analyzer.py <logfile> [drain_sim_th]")
        print(f"Example: python log_analyzer.py HDFS_2k.log 0.5")
        sys.exit(1)

    log_file = sys.argv[1]
    drain_sim_th = float(sys.argv[2]) if len(sys.argv) > 2 else 0.5

    try:
        results = analyze_log_file(log_file, drain_sim_th)
        print_report(results, log_file)
    except FileNotFoundError:
        print(f"Error: Log file '{log_file}' not found")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)
