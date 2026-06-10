# W2-D3 Service Design

## Pipeline architecture

`POST /incident` validates the request with Pydantic, converts the alerts into the
same dictionary format used in D1, then runs the real correlation and RCA logic.
Correlation uses a session window with `gap_sec=120` because the D1 dataset contains
one cascade that continues for several minutes, while consecutive alerts remain less
than two minutes apart. Topology grouping uses an undirected service graph and
`max_hop=2` to capture nearby cascade effects without merging the independent
recommender and search alerts. RCA uses the directed graph, alert timing, and keyword
kNN retrieval against D2 incident history.

## Latency budget

The measured 20-request run produced p50 `3.912 ms` and p99 `5.588 ms`.
Average phases were validation `0.101 ms`, correlation `0.094 ms`, RCA `2.788 ms`,
LLM `0 ms`, and serialization estimate `0.041 ms`. RCA owns most of the budget
because every cluster is compared with the incident catalog.

## Production concern and framework trade-off

The service intentionally runs with one Uvicorn worker for a 4 GB machine. Four
concurrent clients all returned 200, but their average client latency increased to
`25.024 ms`; CPU-bound RCA on a single process is the first bottleneck. The LLM path
is optional and disabled by default, so provider failure falls back to deterministic
graph plus retrieval output. `/readyz` checks only core graph/history resources.

FastAPI was selected over Flask because request validation and automatic 422 responses
are built in. BentoML provides richer model-serving features, but adds unnecessary
deployment complexity for this small deterministic pipeline.
