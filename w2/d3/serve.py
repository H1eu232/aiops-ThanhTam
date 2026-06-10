import json
import os
import re
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, Request
from pydantic import BaseModel, ConfigDict, Field


BASE_DIR = Path(__file__).resolve().parent
SERVICES_FILE = BASE_DIR.parent / "d1" / "dataset" / "services.json"
HISTORY_FILE = BASE_DIR.parent / "d2" / "dataset" / "incidents_history.json"
USE_LLM = os.getenv("AIOPS_USE_LLM", "false").lower() == "true"
SEVERITY_RANK = {"info": 0, "warn": 1, "crit": 2}

service_graph: dict[str, set[str]] = defaultdict(set)
reverse_graph: dict[str, set[str]] = defaultdict(set)
topology_graph: dict[str, set[str]] = defaultdict(set)
incident_history: list[dict[str, Any]] = []
resources_ready = False


class Alert(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    ts: datetime
    service: str = Field(min_length=1)
    metric: str = Field(min_length=1)
    severity: Literal["info", "warn", "crit"]
    value: float | int
    threshold: float | int
    labels: dict[str, Any] = Field(default_factory=dict)


class IncidentRequest(BaseModel):
    alerts: list[Alert] = Field(min_length=1)
    gap_sec: int = Field(default=120, ge=1, le=3600)
    max_hop: int = Field(default=2, ge=0, le=10)


def load_resources() -> None:
    global resources_ready, incident_history
    with SERVICES_FILE.open(encoding="utf-8") as file:
        graph_data = json.load(file)
    service_names = {service["name"] for service in graph_data["services"]}
    for name in service_names:
        service_graph[name]
        reverse_graph[name]
        topology_graph[name]
    for edge in graph_data["edges"]:
        source, target = edge["from"], edge["to"]
        if source in service_names and target in service_names:
            service_graph[source].add(target)
            reverse_graph[target].add(source)
            topology_graph[source].add(target)
            topology_graph[target].add(source)

    with HISTORY_FILE.open(encoding="utf-8") as file:
        history_payload = json.load(file)
    incident_history = history_payload.get("incidents", history_payload)
    resources_ready = bool(service_graph and incident_history)


@asynccontextmanager
async def lifespan(_: FastAPI):
    load_resources()
    yield


app = FastAPI(title="GeekShop AIOps Incident API", version="1.0.0", lifespan=lifespan)


@app.middleware("http")
async def latency_middleware(request: Request, call_next):
    started = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Response-Time-Ms"] = f"{(time.perf_counter() - started) * 1000:.3f}"
    return response


def alert_to_dict(alert: Alert) -> dict[str, Any]:
    output = alert.model_dump()
    output["ts"] = alert.ts.isoformat().replace("+00:00", "Z")
    return output


def parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def fingerprint(alert: dict[str, Any]) -> str:
    return f"{alert['service']}|{alert['metric']}|{alert['severity']}"


def hop_distance(source: str, target: str, max_hop: int) -> int | None:
    if source == target:
        return 0
    queue = deque([(source, 0)])
    seen = {source}
    while queue:
        node, depth = queue.popleft()
        if depth >= max_hop:
            continue
        for neighbor in topology_graph.get(node, set()):
            if neighbor == target:
                return depth + 1
            if neighbor not in seen:
                seen.add(neighbor)
                queue.append((neighbor, depth + 1))
    return None


def session_groups(alerts: list[dict[str, Any]], gap_sec: int) -> list[list[dict[str, Any]]]:
    ordered = sorted(alerts, key=lambda alert: parse_ts(alert["ts"]))
    sessions = [[ordered[0]]]
    for alert in ordered[1:]:
        gap = (parse_ts(alert["ts"]) - parse_ts(sessions[-1][-1]["ts"])).total_seconds()
        if gap <= gap_sec:
            sessions[-1].append(alert)
        else:
            sessions.append([alert])
    return sessions


def topology_groups(alerts: list[dict[str, Any]], max_hop: int) -> list[list[dict[str, Any]]]:
    clusters: list[dict[str, Any]] = []
    for alert in sorted(alerts, key=lambda item: parse_ts(item["ts"])):
        for cluster in clusters:
            if hop_distance(cluster["center"], alert["service"], max_hop) is not None:
                cluster["alerts"].append(alert)
                break
        else:
            clusters.append({"center": alert["service"], "alerts": [alert]})
    return [cluster["alerts"] for cluster in clusters]


def correlate(alerts: list[dict[str, Any]], gap_sec: int, max_hop: int) -> list[dict[str, Any]]:
    clusters = []
    for session_index, session in enumerate(session_groups(alerts, gap_sec)):
        for group_index, group in enumerate(topology_groups(session, max_hop)):
            clusters.append(
                {
                    "cluster_id": f"c-{session_index:03d}-{group_index:03d}",
                    "alert_count": len(group),
                    "services": sorted({alert["service"] for alert in group}),
                    "time_range": [min(alert["ts"] for alert in group), max(alert["ts"] for alert in group)],
                    "max_severity": max(group, key=lambda alert: SEVERITY_RANK[alert["severity"]])["severity"],
                    "fingerprints": list(dict.fromkeys(fingerprint(alert) for alert in group)),
                }
            )
    return clusters


def cluster_alerts(cluster: dict[str, Any], alerts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    start, end = map(parse_ts, cluster["time_range"])
    services = set(cluster["services"])
    return [
        alert
        for alert in alerts
        if alert["service"] in services and start <= parse_ts(alert["ts"]) <= end
    ]


def active_ancestors(service: str, active: set[str]) -> set[str]:
    seen: set[str] = set()
    queue = deque([service])
    while queue:
        node = queue.popleft()
        for caller in reverse_graph.get(node, set()):
            if caller in active and caller not in seen:
                seen.add(caller)
                queue.append(caller)
    return seen


def graph_temporal_top3(cluster: dict[str, Any], alerts: list[dict[str, Any]]) -> list[list[Any]]:
    active = set(cluster["services"])
    relevant = cluster_alerts(cluster, alerts)
    start, end = map(parse_ts, cluster["time_range"])
    duration = max((end - start).total_seconds(), 1.0)
    first_seen: dict[str, datetime] = {}
    max_severity: dict[str, int] = {}
    for alert in relevant:
        service = alert["service"]
        timestamp = parse_ts(alert["ts"])
        first_seen[service] = min(first_seen.get(service, timestamp), timestamp)
        max_severity[service] = max(max_severity.get(service, 0), SEVERITY_RANK[alert["severity"]])
    impacts = {service: len(active_ancestors(service, active)) for service in active}
    max_impact = max(max(impacts.values()), 1)
    scores = []
    for service in active:
        impact = impacts[service] / max_impact
        temporal = 1 - ((first_seen.get(service, end) - start).total_seconds() / duration)
        terminal = 1.0 if not (service_graph.get(service, set()) & active) else 0.0
        severity = max_severity.get(service, 0) / 2
        score = 0.40 * impact + 0.35 * temporal + 0.15 * terminal + 0.10 * severity
        scores.append([service, round(score, 2)])
    return sorted(scores, key=lambda item: (-item[1], item[0]))[:3]


def tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def similarity(
    cluster: dict[str, Any],
    alerts: list[dict[str, Any]],
    incident: dict[str, Any],
    graph_root: str,
) -> float:
    context = []
    for alert in cluster_alerts(cluster, alerts):
        context.extend(
            [
                alert["service"],
                alert["metric"],
                alert["severity"],
                alert.get("labels", {}).get("note", ""),
            ]
        )
    cluster_tokens = tokenize(" ".join(cluster["services"] + cluster["fingerprints"] + context))
    incident_tokens = tokenize(
        " ".join(incident.get("services_involved", []))
        + " "
        + incident.get("summary", "")
        + " "
        + incident.get("root_cause_class", "")
    )
    keyword_overlap = len(cluster_tokens & incident_tokens) / len(cluster_tokens) if cluster_tokens else 0.0
    cluster_services = set(cluster["services"])
    history_services = set(incident.get("services_involved", []))
    service_overlap = len(cluster_services & history_services) / max(
        min(len(cluster_services), len(history_services)), 1
    )
    root_agreement = 1.0 if incident.get("root_cause_service") == graph_root else 0.0
    return 0.50 * keyword_overlap + 0.25 * service_overlap + 0.25 * root_agreement


def run_rca(cluster: dict[str, Any], alerts: list[dict[str, Any]]) -> dict[str, Any]:
    graph_top3 = graph_temporal_top3(cluster, alerts)
    root_cause = graph_top3[0][0]
    similar = sorted(
        ((incident, similarity(cluster, alerts, incident, root_cause)) for incident in incident_history),
        key=lambda item: (-item[1], item[0]["id"]),
    )[:3]
    if not similar or similar[0][1] <= 0:
        return {
            "root_cause": root_cause,
            "class": "other",
            "confidence": round(0.5 * graph_top3[0][1], 2),
            "recommended_actions": ["Investigate manually"],
            "graph_top3": graph_top3,
            "similar_incidents": [],
            "method": "graph-only-fallback",
        }
    best, retrieval_score = similar[0]
    return {
        "root_cause": root_cause,
        "class": best["root_cause_class"],
        "confidence": round(min(0.99, 0.65 * graph_top3[0][1] + 0.35 * retrieval_score), 2),
        "recommended_actions": [best["remediation"]],
        "graph_top3": graph_top3,
        "similar_incidents": [incident["id"] for incident, _ in similar],
        "method": "graph+keyword-knn" if not USE_LLM else "graph+keyword-knn+llm-fallback",
    }


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/readyz")
def readyz():
    return {
        "status": "ready" if resources_ready else "not_ready",
        "core_resources_loaded": resources_ready,
        "llm_enabled": USE_LLM,
    }


@app.post("/incident")
def incident(payload: IncidentRequest):
    timings: dict[str, float] = {}
    started = time.perf_counter()
    alerts = [alert_to_dict(alert) for alert in payload.alerts]
    timings["validate_ms"] = (time.perf_counter() - started) * 1000

    phase = time.perf_counter()
    clusters = correlate(alerts, payload.gap_sec, payload.max_hop)
    timings["correlate_ms"] = (time.perf_counter() - phase) * 1000

    phase = time.perf_counter()
    rca_results = [run_rca(cluster, alerts) for cluster in clusters]
    timings["rca_ms"] = (time.perf_counter() - phase) * 1000
    timings["llm_ms"] = 0.0

    response = {
        "clusters": clusters,
        "root_cause": rca_results[0]["root_cause"],
        "recommended_actions": rca_results[0]["recommended_actions"],
        "rca_results": rca_results,
    }
    phase = time.perf_counter()
    json.dumps(response)
    timings["serialize_ms"] = (time.perf_counter() - phase) * 1000
    response["phase_timings_ms"] = {key: round(value, 3) for key, value in timings.items()}
    return response
