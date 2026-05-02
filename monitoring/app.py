"""
DonNext — Monitoring Microservice  (port 8002)
Accepts real-time cluster metrics from the simulator and exposes
dashboard endpoints for the frontend.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import random
from collections import defaultdict

app = FastAPI(
    title="DonNext Monitoring Service",
    description="Microservice for cluster monitoring and metrics",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Models ───────────────────────────────────────────────────────────────────

class ClusterMetric(BaseModel):
    cluster_id: int
    timestamp: datetime
    cpu_usage: float
    memory_usage: float
    network_throughput: float
    latency_ms: float
    packet_loss: float
    availability: float
    error_rate: float
    active_connections: int


class SystemHealth(BaseModel):
    total_clusters: int
    healthy_clusters: int
    warning_clusters: int
    critical_clusters: int
    avg_cpu_usage: float
    avg_memory_usage: float
    avg_latency: float
    total_throughput: float
    uptime_percentage: float
    last_updated: datetime


class Alert(BaseModel):
    id: str
    cluster_id: int
    severity: str          # LOW | MEDIUM | HIGH | CRITICAL
    type: str
    message: str
    timestamp: datetime
    resolved: bool
    metric_name: Optional[str] = None
    threshold: Optional[float] = None
    current_value: Optional[float] = None


# ─── In-memory store ──────────────────────────────────────────────────────────

cluster_metrics: Dict[int, List[ClusterMetric]] = defaultdict(list)
alerts: List[Alert] = []
system_health_history: List[SystemHealth] = []


# ─── Helpers ──────────────────────────────────────────────────────────────────

def generate_cluster_metric(cluster_id: int, timestamp: datetime = None) -> ClusterMetric:
    """Fallback random metric (used when simulator is not running)."""
    if timestamp is None:
        timestamp = datetime.now()
    base_cpu = 30 + random.uniform(-10, 40)
    base_mem = 40 + random.uniform(-15, 35)
    return ClusterMetric(
        cluster_id=cluster_id,
        timestamp=timestamp,
        cpu_usage=max(0, min(100, base_cpu + random.uniform(-5, 5))),
        memory_usage=max(0, min(100, base_mem + random.uniform(-5, 5))),
        network_throughput=random.uniform(100, 1000),
        latency_ms=random.uniform(1, 50),
        packet_loss=random.uniform(0, 5),
        availability=random.uniform(95, 100),
        error_rate=random.uniform(0, 2),
        active_connections=random.randint(50, 500),
    )


def generate_alert(cluster_id: int) -> Alert:
    severities = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    alert_types = ["CPU_HIGH", "MEMORY_HIGH", "LATENCY_HIGH", "PACKET_LOSS", "CONNECTIONS_HIGH"]
    severity = random.choice(severities)
    alert_type = random.choice(alert_types)
    messages = {
        "CPU_HIGH": f"CPU usage is above threshold for cluster {cluster_id}",
        "MEMORY_HIGH": f"Memory usage is critical for cluster {cluster_id}",
        "LATENCY_HIGH": f"High latency detected on cluster {cluster_id}",
        "PACKET_LOSS": f"Packet loss detected on cluster {cluster_id}",
        "CONNECTIONS_HIGH": f"Too many active connections on cluster {cluster_id}",
    }
    return Alert(
        id=f"alert_{cluster_id}_{random.randint(1000, 9999)}",
        cluster_id=cluster_id,
        severity=severity,
        type=alert_type,
        message=messages[alert_type],
        timestamp=datetime.now() - timedelta(minutes=random.randint(1, 60)),
        resolved=random.choice([True, False]),
        metric_name=alert_type.lower(),
        threshold=random.uniform(70, 90),
        current_value=random.uniform(75, 95),
    )


def calculate_system_health() -> SystemHealth:
    total = len(cluster_metrics)
    healthy = warning = critical = 0
    total_cpu = total_mem = total_lat = total_tput = 0.0

    for metrics in cluster_metrics.values():
        if not metrics:
            continue
        m = metrics[-1]
        if m.cpu_usage < 70 and m.memory_usage < 70 and m.latency_ms < 20 and m.availability > 99:
            healthy += 1
        elif m.cpu_usage < 85 and m.memory_usage < 85 and m.latency_ms < 40:
            warning += 1
        else:
            critical += 1
        total_cpu  += m.cpu_usage
        total_mem  += m.memory_usage
        total_lat  += m.latency_ms
        total_tput += m.network_throughput

    return SystemHealth(
        total_clusters=total,
        healthy_clusters=healthy,
        warning_clusters=warning,
        critical_clusters=critical,
        avg_cpu_usage=total_cpu / total if total else 0,
        avg_memory_usage=total_mem / total if total else 0,
        avg_latency=total_lat / total if total else 0,
        total_throughput=total_tput,
        uptime_percentage=99.5 + random.uniform(-0.5, 0.5),
        last_updated=datetime.now(),
    )


def _store_metric(metric: ClusterMetric):
    cluster_metrics[metric.cluster_id].append(metric)
    if len(cluster_metrics[metric.cluster_id]) > 100:
        cluster_metrics[metric.cluster_id] = cluster_metrics[metric.cluster_id][-100:]


def initialize_sample_data():
    cluster_ids = [77, 78, 79, 80, 81, 82, 83, 84, 85]
    for cid in cluster_ids:
        for hours_ago in range(24, 0, -1):
            _store_metric(generate_cluster_metric(cid, datetime.now() - timedelta(hours=hours_ago)))
    for i in range(5):
        alerts.append(generate_alert(cluster_ids[i % len(cluster_ids)]))


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {"service": "monitoring-service", "status": "running", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    return {
        "status": "UP",
        "service": "monitoring-service",
        "timestamp": datetime.now().isoformat(),
        "clusters_monitored": len(cluster_metrics),
    }


# ── INGEST (called by simulator) ──────────────────────────────────────────────

@app.post("/api/v1/metrics/ingest", status_code=201)
async def ingest_metric(metric: ClusterMetric):
    """
    Receive a real-time metric pushed by the simulator.
    This replaces the internal random generation for that cluster.
    """
    _store_metric(metric)
    return {"status": "ok", "cluster_id": metric.cluster_id}


# ── READ endpoints ─────────────────────────────────────────────────────────────

@app.get("/api/v1/clusters")
async def get_all_clusters():
    return {"clusters": list(cluster_metrics.keys())}


@app.get("/api/v1/clusters/{cluster_id}/metrics")
async def get_cluster_metrics(cluster_id: int, limit: int = 10):
    if cluster_id not in cluster_metrics:
        raise HTTPException(status_code=404, detail=f"Cluster {cluster_id} not found")
    return {"cluster_id": cluster_id, "metrics": cluster_metrics[cluster_id][-limit:]}


@app.get("/api/v1/metrics/realtime")
async def get_realtime_metrics(limit: int = 5):
    realtime = []
    for cid in list(cluster_metrics.keys())[:limit]:
        m = generate_cluster_metric(cid)
        _store_metric(m)
        realtime.append(m)
    return {"metrics": realtime, "timestamp": datetime.now()}


@app.get("/api/v1/system/health")
async def get_system_health():
    health = calculate_system_health()
    system_health_history.append(health)
    return health


@app.get("/api/v1/alerts")
async def get_alerts(severity: Optional[str] = None, resolved: Optional[bool] = None, limit: int = 20):
    filtered = alerts.copy()
    if severity:
        filtered = [a for a in filtered if a.severity == severity.upper()]
    if resolved is not None:
        filtered = [a for a in filtered if a.resolved == resolved]
    filtered.sort(key=lambda x: x.timestamp, reverse=True)
    return {"alerts": filtered[:limit], "total": len(filtered)}


@app.get("/api/v1/alerts/active")
async def get_active_alerts():
    active = sorted([a for a in alerts if not a.resolved], key=lambda x: x.timestamp, reverse=True)
    return {"alerts": active}


@app.post("/api/v1/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: str):
    for alert in alerts:
        if alert.id == alert_id:
            alert.resolved = True
            return {"message": f"Alert {alert_id} resolved"}
    raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")


@app.get("/api/v1/metrics/trends")
async def get_metric_trends(cluster_id: Optional[int] = None, hours: int = 24):
    trends = {}
    cutoff = datetime.now() - timedelta(hours=hours)
    clusters_to_check = [cluster_id] if cluster_id else list(cluster_metrics.keys())
    for cid in clusters_to_check:
        if cid in cluster_metrics:
            recent = [m for m in cluster_metrics[cid] if m.timestamp >= cutoff]
            trends[cid] = {
                "cpu_trend":        [m.cpu_usage for m in recent],
                "memory_trend":     [m.memory_usage for m in recent],
                "latency_trend":    [m.latency_ms for m in recent],
                "throughput_trend": [m.network_throughput for m in recent],
                "timestamps":       [m.timestamp.isoformat() for m in recent],
            }
    return {"trends": trends}


@app.get("/api/v1/performance/summary")
async def get_performance_summary():
    health = calculate_system_health()
    active_alerts = [a for a in alerts if not a.resolved]
    perf = 100 - (health.avg_cpu_usage * 0.4 + health.avg_memory_usage * 0.3 + health.avg_latency * 0.3)
    return {
        "system_health": health,
        "active_alerts_count": len(active_alerts),
        "critical_alerts_count": len([a for a in active_alerts if a.severity == "CRITICAL"]),
        "performance_score": max(0, perf),
        "uptime": health.uptime_percentage,
        "total_clusters": health.total_clusters,
        "last_updated": datetime.now(),
    }


# ─── Startup ──────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup_event():
    initialize_sample_data()
    print("🔧 Monitoring service ready on :8002")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)