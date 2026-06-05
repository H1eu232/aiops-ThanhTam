from __future__ import annotations

from collections import Counter, deque
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from typing import Any

ALERTS_FILE = Path(__file__).with_name("alerts.jsonl")
WINDOW_SIZE = 5
COOLDOWN_TICKS = 20

recent_samples: deque[dict[str, Any]] = deque(maxlen=WINDOW_SIZE)
last_alert_tick: dict[str, int] = {}
tick_count = 0


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def log_evidence(logs: list[dict[str, Any]]) -> Counter:
    text = " ".join(log.get("message", "").lower() for log in logs)
    levels = Counter(log.get("level", "INFO") for log in logs)
    evidence = Counter()

    if "outofmemory" in text or "gc pause" in text:
        evidence["memory_leak"] += 1
    if "queue depth high" in text or "overloaded" in text:
        evidence["traffic_spike"] += 1
    if "upstream timeout" in text or "circuit breaker" in text:
        evidence["dependency_timeout"] += 1
    if levels["ERROR"] or levels["FATAL"]:
        evidence["error_log"] += levels["ERROR"] + levels["FATAL"]

    return evidence


def metric_flags(metrics: dict[str, float], logs: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    memory_limit = max(float(metrics.get("memory_limit_bytes", 1)), 1.0)
    memory_util = float(metrics.get("memory_usage_bytes", 0)) / memory_limit
    rps = float(metrics.get("http_requests_per_sec", 0))
    latency = float(metrics.get("http_p99_latency_ms", 0))
    five_xx = float(metrics.get("http_5xx_rate", 0))
    gc_pause = float(metrics.get("jvm_gc_pause_ms_avg", 0))
    queue_depth = float(metrics.get("queue_depth", 0))
    timeout_rate = float(metrics.get("upstream_timeout_rate", 0))
    log_flags = log_evidence(logs)

    return {
        "memory_leak": {
            "hit": (
                memory_util >= 0.75
                and gc_pause >= 60
                and (latency >= 250 or five_xx >= 3 or log_flags["memory_leak"])
            ),
            "severity": "critical" if memory_util >= 0.85 or five_xx >= 10 else "warning",
            "message": (
                f"Memory utilization {memory_util:.0%}, GC pause {gc_pause:.1f}ms, "
                f"p99 latency {latency:.1f}ms, 5xx {five_xx:.2f}%"
            ),
        },
        "traffic_spike": {
            "hit": (
                rps >= 350
                and queue_depth >= 50
                and timeout_rate < 5
                and (latency >= 300 or five_xx >= 3 or log_flags["traffic_spike"])
            ),
            "severity": "critical" if queue_depth >= 120 or five_xx >= 10 else "warning",
            "message": (
                f"Traffic spike suspected: rps {rps:.1f}, queue depth {queue_depth:.0f}, "
                f"p99 latency {latency:.1f}ms, 5xx {five_xx:.2f}%"
            ),
        },
        "dependency_timeout": {
            "hit": (
                timeout_rate >= 8
                and five_xx >= 3
                and (latency >= 350 or log_flags["dependency_timeout"])
            ),
            "severity": "critical" if timeout_rate >= 35 or five_xx >= 15 else "warning",
            "message": (
                f"Dependency timeout suspected: upstream timeout {timeout_rate:.2f}%, "
                f"5xx {five_xx:.2f}%, p99 latency {latency:.1f}ms"
            ),
        },
    }


def detect_anomaly(payload: dict[str, Any]) -> dict[str, str] | None:
    metrics = payload.get("metrics", {})
    logs = payload.get("logs", [])
    current_flags = metric_flags(metrics, logs)

    recent_samples.append({"flags": current_flags})
    if len(recent_samples) < 3:
        return None

    scores: dict[str, int] = {}
    for fault_type in current_flags:
        scores[fault_type] = sum(
            1 for sample in recent_samples if sample["flags"][fault_type]["hit"]
        )

    best_type, best_score = max(scores.items(), key=lambda item: item[1])
    if best_score < 2 or not current_flags[best_type]["hit"]:
        return None

    if tick_count - last_alert_tick.get(best_type, -COOLDOWN_TICKS) < COOLDOWN_TICKS:
        return None

    last_alert_tick[best_type] = tick_count
    return {
        "timestamp": payload.get("timestamp") or utc_now_iso(),
        "type": best_type,
        "severity": current_flags[best_type]["severity"],
        "message": current_flags[best_type]["message"],
    }


def write_alert(alert: dict[str, str]) -> None:
    with ALERTS_FILE.open("a", encoding="utf-8") as file:
        file.write(json.dumps(alert, ensure_ascii=False) + "\n")


class PipelineHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/health":
            self.send_json(200, {"status": "ok"})
            return
        self.send_json(404, {"error": "not found"})

    def do_POST(self) -> None:
        global tick_count

        if self.path != "/ingest":
            self.send_json(404, {"error": "not found"})
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(content_length)
            payload = json.loads(body.decode("utf-8"))
        except (ValueError, json.JSONDecodeError):
            self.send_json(400, {"error": "invalid json"})
            return

        tick_count += 1
        alert = detect_anomaly(payload)

        if alert:
            write_alert(alert)
            self.send_json(200, {"status": "ok", "alert": "written"})
            return

        self.send_json(200, {"status": "ok"})

    def send_json(self, status_code: int, payload: dict[str, str]) -> None:
        response = json.dumps(payload).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def log_message(self, format: str, *args: Any) -> None:
        return


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", 8000), PipelineHandler)
    print("Pipeline listening on http://localhost:8000/ingest")
    server.serve_forever()
