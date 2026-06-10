# W2-D3 EOD Checkpoint

## 1. Measured endpoint latency

I ran 20 sequential requests using the real 20-alert D1 dataset and read
`X-Response-Time-Ms`. The measured p50 was **3.912 ms** and p99 was **5.588 ms**.
Average internal phases were validation `0.101 ms`, correlation `0.094 ms`, RCA
`2.788 ms`, LLM `0 ms`, and serialization estimate `0.041 ms`. RCA consumed most
time because it scores graph candidates and retrieves similar history for every
cluster. With 10x more alerts, validation, correlation, and parts of RCA scale with
input size. Resource loading and disabled LLM cost remain fixed per process.

## 2. LLM failure and concurrency

I benchmarked 20 requests with concurrency 4 using Python `ThreadPoolExecutor`.
All requests returned 200. Total wall time was `126.842 ms`, average client latency
was `25.024 ms`, and the maximum response header latency was `23.451 ms`. The first
bottleneck is CPU-bound RCA work in the single Uvicorn worker. The service runs with
`AIOPS_USE_LLM=false`, so a provider outage does not break the endpoint. Graph plus
keyword-kNN retrieval is the deterministic fallback path.

## 3. Health and readiness

`/healthz` only verifies that the web process can answer requests and returns
`{"status":"ok"}`. `/readyz` verifies that the service graph and incident history
were loaded, and reports whether LLM enrichment is enabled. These endpoints are
separate so an orchestrator can distinguish a live process from one that is ready
to receive incidents. If the optional LLM provider is down, readiness still passes
because the core graph and retrieval pipeline remains functional.
