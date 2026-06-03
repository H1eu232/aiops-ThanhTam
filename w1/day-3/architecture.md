# Architecture Design: Anomaly Detection on Payment Service

This document describes the End-to-End (E2E) telemetry and anomaly detection architecture designed for a distributed **Payment Service**.

---

## 1. End-to-End Data Flow Diagram (Mermaid)

```mermaid
graph TD
    %% Service Layer
    subgraph Service Layer
        PS[Payment Microservice - Go] -->|OTel Traces & Metrics| OC[OpenTelemetry SDK]
        AS[Authentication Service - Python] -->|OTel Traces & Metrics| OC
    end

    %% Collection Layer
    subgraph Collection Layer
        OC -->|gRPC / OTLP| OTC[OpenTelemetry Collector]
    end

    %% Transport Layer
    subgraph Transport Layer
        OTC -->|Publish Logs & Traces| K_LT[Kafka Topic: payment.logs-traces]
        OTC -->|Publish Metrics| K_M[Kafka Topic: payment.metrics]
    end

    %% Processing Layer
    subgraph Processing Layer
        K_M -->|Stream Consumption| Flink[Apache Flink - Rolling Stats & Rate of Change]
        K_LT -->|Buffer Ingestion| Logstash[Logstash/Fluentbit]
    end

    %% Storage Layer
    subgraph Storage Layer
        Flink -->|Write Enriched Metrics| VM[(VictoriaMetrics - Time Series)]
        Logstash -->|Index Logs/Traces| ES[(Elasticsearch Cluster)]
    end

    %% Query & Machine Learning Layer
    subgraph Query & ML Alerting Layer
        Grafana[Grafana Dashboard] -->|PromQL Queries| VM
        Grafana -->|Lucene Queries| ES
        ML_Engine[Python ML Anomaly Engine] -->|Pull Metric Vectors| VM
        ML_Engine -->|Run Isolation Forest| Alert[PagerDuty / Slack Alert]
    end

    %% Styles
    classDef service fill:#f9f,stroke:#333,stroke-width:2px;
    classDef transport fill:#bbf,stroke:#333,stroke-width:2px;
    classDef processing fill:#bfb,stroke:#333,stroke-width:2px;
    classDef storage fill:#ffb,stroke:#333,stroke-width:2px;
    classDef ui fill:#fbb,stroke:#333,stroke-width:2px;

    class PS,AS service;
    class K_LT,K_M transport;
    class Flink,Logstash processing;
    class VM,ES storage;
    class Grafana,ML_Engine,Alert ui;
```

---

## 2. Component Analysis & Tool Choice

### 2.1 Service Layer
* **Role:** Processes online credit card and bank transactions, generates raw telemetry data (traces, logs, and transaction metric signals like amounts, transaction IDs, latency).
* **Tool Choice:** **Go/Python Microservices instrumented with OpenTelemetry (OTel) SDK**. 
  * *Rationale:* OTel is the industry standard for vendor-agnostic instrumentation. Go provides high performance for transaction execution, while Python handles authentication/validation layers.

### 2.2 Collection Layer
* **Role:** Receives raw telemetry from multiple instances, parses, filters, and batches data before sending it downstream to avoid overloading the pipeline.
* **Tool Choice:** **OpenTelemetry Collector (OTel Collector)**.
  * *Rationale:* Acts as a high-performance local proxy that buffers data, removes sensitive PII (like raw credit card numbers or user details), and standardizes formats to OpenTelemetry Protocol (OTLP).

### 2.3 Transport Layer
* **Role:** Acts as a high-throughput, fault-tolerant message queue to buffer spikes in payment transaction logs and metrics, decoupling collection from processing.
* **Tool Choice:** **Apache Kafka (Confluent / Managed MSK)**.
  * *Rationale:* Offers partitioned, distributed logs with microsecond latency. Can handle millions of events per second and allows parallel processing by downstream consumers.

### 2.4 Processing Layer
* **Role:** Performs real-time stream aggregation, anomaly calculations (e.g. rolling transaction failure rates, sliding window velocity detection) as events pass through.
* **Tool Choice:** **Apache Flink**.
  * *Rationale:* Flink is ideal for stateful, low-latency stream processing on event time. It calculates sliding rolling averages and variances of transaction amounts and failure codes over 1-minute and 5-minute windows.

### 2.5 Storage Layer
* **Role:** Persists telemetry data for long-term auditing and near-real-time querying.
* **Tool Choices:**
  * **VictoriaMetrics (Metrics):** An extremely lightweight, high-performance time-series database. Chosen over Prometheus for its lower memory footprint, superior compression ratios, and native clustering.
  * **Elasticsearch (Logs & Traces):** Used for indexing distributed transaction traces and application logs to support fast search and distributed debugging.

### 2.6 Query & Machine Learning Layer
* **Role:** Provides observability dashboards, queries metrics, and hosts automated anomaly detection models to alert engineers on issues (e.g. sudden drop in checkout rates).
* **Tool Choices:**
  * **Grafana:** Displays real-time dashboards by querying VictoriaMetrics and Elasticsearch.
  * **Custom Python ML Engine:** Runs on a scheduled interval (e.g., every 1 minute) querying VictoriaMetrics features (transaction throughput, latency, sliding standard deviations) and feeds them into an **Isolation Forest** model to flag outlier activity and trigger PagerDuty alerts.
