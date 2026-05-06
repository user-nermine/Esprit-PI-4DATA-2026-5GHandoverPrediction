"""
DonNext — Monitoring Microservice  (port 8002)
D:\\pipline_c\\monitoring\\app.py

What changed vs original v1:
  1. ClusterMetric: added rsrp / sinr / ho_rate / velocity optional fields
     so simulator radio KPIs are stored and drive real alerts
  2. generate_alert(): replaced random alerts with NB2/NB4 real thresholds:
       rsrp ≤ -110 dBm → CRITICAL  (NB2 FE-3, cluster C54 = -112.9 dBm)
       rsrp ≤ -100 dBm → HIGH
       sinr ≤  0   dB  → CRITICAL  (NB2 FE-3, cluster C51 = -8.3 dB)
       sinr ≤  3   dB  → MEDIUM
       ho_rate ≥ 0.15  → HIGH      (NB2 FE-5, C1=20.7%, C6=18.6%)
       velocity > 100  → MEDIUM    (DSO3 CELL_CHANGE trigger)
       Returns None when no threshold is exceeded (no alert spam)
  3. calculate_system_health(): fixed division-by-zero on empty store;
     uses rsrp/sinr for health classification when available
  4. /api/v1/metrics/realtime: reads from store (no extra random generation)
  5. initialize_sample_data(): seeds healthy metrics (rsrp in [-90,-70])
     so dashboard starts green
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
    description="Real NB2/NB4 alert thresholds — radio KPI driven",
    version="2.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── NB2 / NB4 real thresholds ─────────────────────────────────────────────────
RSRP_CRITICAL = -110.0   # NB2 FE-3  C54 = -112.9 dBm
RSRP_HIGH     = -100.0   # signal degraded boundary
SINR_CRITICAL =    0.0   # NB2 FE-3  C51 = -8.3 dB
SINR_HIGH     =    3.0   # NB4 alert threshold
HO_RATE_HIGH  =    0.15  # NB2 FE-5  C1=20.7%
HO_RATE_MED   =    0.08
VELOCITY_HIGH =  100.0   # DSO3 CELL_CHANGE trigger

# ── Models ────────────────────────────────────────────────────────────────────

class ClusterMetric(BaseModel):
    cluster_id:          int
    timestamp:           datetime
    cpu_usage:           float
    memory_usage:        float
    network_throughput:  float
    latency_ms:          float
    packet_loss:         float
    availability:        float
    error_rate:          float
    active_connections:  int
    # Radio KPIs from simulator — drive NB2-based alerts
    rsrp:                Optional[float] = None
    sinr:                Optional[float] = None
    ho_rate:             Optional[float] = None
    velocity:            Optional[float] = None


class SystemHealth(BaseModel):
    total_clusters:    int
    healthy_clusters:  int
    warning_clusters:  int
    critical_clusters: int
    avg_cpu_usage:     float
    avg_memory_usage:  float
    avg_latency:       float
    total_throughput:  float
    uptime_percentage: float
    last_updated:      datetime


class Alert(BaseModel):
    id:            str
    cluster_id:    int
    severity:      str
    type:          str
    message:       str
    timestamp:     datetime
    resolved:      bool
    metric_name:   Optional[str]   = None
    threshold:     Optional[float] = None
    current_value: Optional[float] = None


# ── In-memory store ───────────────────────────────────────────────────────────

cluster_metrics:       Dict[int, List[ClusterMetric]] = defaultdict(list)
alerts:                List[Alert]                    = []
system_health_history: List[SystemHealth]             = []
_alert_counter: int = 0


# ── Helpers ───────────────────────────────────────────────────────────────────

def _healthy_kpi() -> dict:
    """KPI snapshot seeded in the healthy operating region."""
    return {
        "rsrp":      round(random.uniform(-90, -70), 2),
        "rsrq":      round(random.uniform(-12,  -5), 2),
        "sinr":      round(random.uniform(12,   25), 2),
        "cqi":       round(random.uniform(8,    14), 1),
        "tx_power":  round(random.uniform(12,   20), 1),
        "velocity":  round(random.uniform(0,    60), 1),
        "n_records": random.randint(150, 350),
        "ho_rate":   round(random.uniform(0.05, 0.18), 3),
    }


def generate_cluster_metric(
    cluster_id: int,
    timestamp: datetime = None,
    kpi: dict = None,
) -> ClusterMetric:
    if timestamp is None:
        timestamp = datetime.now()
    if kpi:
        sinr     = float(kpi.get("sinr",     15) or 15)
        ho_rate  = float(kpi.get("ho_rate", 0.1) or 0.1)
        n_rec    = int(kpi.get("n_records",  200) or 200)
        rsrp     = float(kpi.get("rsrp",    -85) or -85)
        velocity = float(kpi.get("velocity",   0) or 0)
    else:
        kpi = _healthy_kpi()
        sinr     = kpi["sinr"]
        ho_rate  = kpi["ho_rate"]
        n_rec    = kpi["n_records"]
        rsrp     = kpi["rsrp"]
        velocity = kpi["velocity"]

    return ClusterMetric(
        cluster_id=cluster_id,
        timestamp=timestamp,
        cpu_usage=max(0, min(100, 30 + velocity * 0.3 + random.uniform(-5, 10))),
        memory_usage=max(0, min(100, 40 + n_rec * 0.05 + random.uniform(-5, 10))),
        network_throughput=max(50, 1000 - abs(rsrp) * 3 + random.uniform(-50, 50)),
        latency_ms=max(1, 50 - sinr * 0.8 + random.uniform(-3, 3)),
        packet_loss=max(0, ho_rate * 5 + random.uniform(-0.3, 0.3)),
        availability=min(100, 98 + sinr / 100),
        error_rate=max(0, ho_rate * 3 + random.uniform(-0.1, 0.2)),
        active_connections=n_rec,
        rsrp=rsrp,
        sinr=sinr,
        ho_rate=ho_rate,
        velocity=velocity,
    )


def generate_alert(cluster_id: int, kpi: dict = None) -> Optional[Alert]:
    """
    Generate alert based on real NB2/NB4 thresholds.
    Returns None when no threshold exceeded — prevents alert spam
    on healthy pushes.
    """
    global _alert_counter

    MESSAGES = {
        "RSRP_CRITICAL": f"RSRP critique cluster {cluster_id} (≤{RSRP_CRITICAL} dBm — NB2 FE-3)",
        "RSRP_HIGH":     f"RSRP dégradé cluster {cluster_id} (≤{RSRP_HIGH} dBm)",
        "SINR_CRITICAL": f"SINR négatif cluster {cluster_id} — interférence (NB2 FE-3)",
        "SINR_HIGH":     f"SINR faible cluster {cluster_id} (≤{SINR_HIGH} dB)",
        "HO_RATE_HIGH":  f"Taux HO élevé cluster {cluster_id} (≥{HO_RATE_HIGH} — NB2 FE-5)",
        "HO_RATE_MED":   f"Taux HO modéré cluster {cluster_id} (≥{HO_RATE_MED})",
        "CELL_CHANGE":   f"Changement cellule imminent cluster {cluster_id} (velocity élevée)",
    }

    if kpi:
        rsrp     = float(kpi.get("rsrp",     -85) or -85)
        sinr     = float(kpi.get("sinr",      15) or 15)
        ho_rate  = float(kpi.get("ho_rate",  0.1) or 0.1)
        velocity = float(kpi.get("velocity",   0) or 0)

        if rsrp <= RSRP_CRITICAL:
            t, s, th, cv = "RSRP_CRITICAL", "CRITICAL", RSRP_CRITICAL, rsrp
        elif sinr <= SINR_CRITICAL:
            t, s, th, cv = "SINR_CRITICAL", "CRITICAL", SINR_CRITICAL, sinr
        elif rsrp <= RSRP_HIGH:
            t, s, th, cv = "RSRP_HIGH", "HIGH", RSRP_HIGH, rsrp
        elif ho_rate >= HO_RATE_HIGH:
            t, s, th, cv = "HO_RATE_HIGH", "HIGH", HO_RATE_HIGH, ho_rate
        elif sinr <= SINR_HIGH:
            t, s, th, cv = "SINR_HIGH", "MEDIUM", SINR_HIGH, sinr
        elif velocity > VELOCITY_HIGH:
            t, s, th, cv = "CELL_CHANGE", "MEDIUM", VELOCITY_HIGH, velocity
        elif ho_rate >= HO_RATE_MED:
            t, s, th, cv = "HO_RATE_MED", "LOW", HO_RATE_MED, ho_rate
        else:
            return None  # All KPIs healthy — no alert
    else:
        # Initialization fallback — create a low-severity resolved alert
        t  = random.choice(["HO_RATE_MED", "SINR_HIGH"])
        s  = "LOW"
        th = HO_RATE_MED
        cv = round(random.uniform(0.08, 0.12), 3)

    _alert_counter += 1
    return Alert(
        id=f"alert_{cluster_id}_{_alert_counter:05d}",
        cluster_id=cluster_id,
        severity=s,
        type=t,
        message=MESSAGES.get(t, f"Alerte cluster {cluster_id}"),
        timestamp=datetime.now() - timedelta(minutes=random.randint(0, 5)),
        resolved=False,
        metric_name=t.lower(),
        threshold=th,
        current_value=cv,
    )


def calculate_system_health() -> SystemHealth:
    """
    Fixed: uses len(active) not total to avoid division-by-zero.
    Health classification: NB2-based when rsrp/sinr available,
    IT-based (cpu/latency) as fallback.
    """
    active = [(cid, metrics[-1]) for cid, metrics in cluster_metrics.items() if metrics]
    n = max(len(active), 1)
    healthy = warning = critical = 0
    sum_cpu = sum_mem = sum_lat = sum_tput = 0.0

    for _, m in active:
        if m.rsrp is not None and m.sinr is not None:
            # NB2-based: rsrp > -100 AND sinr > 3 → healthy
            if m.rsrp > RSRP_HIGH and m.sinr > SINR_HIGH:
                healthy += 1
            elif m.rsrp > RSRP_CRITICAL and m.sinr > SINR_CRITICAL:
                warning += 1
            else:
                critical += 1
        else:
            # IT-based fallback
            if m.cpu_usage < 70 and m.memory_usage < 70 and m.latency_ms < 25:
                healthy += 1
            elif m.cpu_usage < 85 and m.memory_usage < 85 and m.latency_ms < 40:
                warning += 1
            else:
                critical += 1
        sum_cpu  += m.cpu_usage
        sum_mem  += m.memory_usage
        sum_lat  += m.latency_ms
        sum_tput += m.network_throughput

    return SystemHealth(
        total_clusters=len(active),
        healthy_clusters=healthy,
        warning_clusters=warning,
        critical_clusters=critical,
        avg_cpu_usage=round(sum_cpu / n, 2),
        avg_memory_usage=round(sum_mem / n, 2),
        avg_latency=round(sum_lat / n, 2),
        total_throughput=round(sum_tput, 2),
        uptime_percentage=round(99.5 + random.uniform(-0.3, 0.5), 3),
        last_updated=datetime.now(),
    )


def _store_metric(metric: ClusterMetric):
    cluster_metrics[metric.cluster_id].append(metric)
    if len(cluster_metrics[metric.cluster_id]) > 100:
        cluster_metrics[metric.cluster_id] = cluster_metrics[metric.cluster_id][-100:]


def initialize_sample_data():
    """Seed 24 h of healthy metrics so dashboard starts green."""
    for cid in [77, 78, 79, 80, 81, 82, 83, 84, 85]:
        for h in range(24, 0, -1):
            _store_metric(generate_cluster_metric(
                cid,
                datetime.now() - timedelta(hours=h),
                kpi=_healthy_kpi(),
            ))
    # Seed a few already-resolved historical alerts
    for cid in [77, 78, 79]:
        a = generate_alert(cid)
        if a:
            a.resolved = True
            alerts.append(a)


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {
        "service": "monitoring-service", "status": "running", "version": "2.0.0",
        "thresholds": {
            "rsrp_critical": RSRP_CRITICAL, "rsrp_high": RSRP_HIGH,
            "sinr_critical": SINR_CRITICAL, "sinr_high": SINR_HIGH,
            "ho_rate_high": HO_RATE_HIGH,   "velocity_high": VELOCITY_HIGH,
        },
    }


@app.get("/health")
async def health_check():
    return {
        "status": "UP", "service": "monitoring-service",
        "timestamp": datetime.now().isoformat(),
        "clusters_monitored": len(cluster_metrics),
    }


# ── INGEST — called by simulator every 3 s ────────────────────────────────────

@app.post("/api/v1/metrics/ingest", status_code=201)
async def ingest_metric(metric: ClusterMetric):
    """Receive real-time metric from simulator. Generate alert only when threshold exceeded."""
    _store_metric(metric)
    kpi = {
        "rsrp": metric.rsrp, "sinr": metric.sinr,
        "ho_rate": metric.ho_rate, "velocity": metric.velocity,
    }
    if any(v is not None for v in kpi.values()):
        alert = generate_alert(metric.cluster_id, kpi)
        if alert:
            alerts.append(alert)
            if len(alerts) > 500:
                alerts[:] = alerts[-500:]
    return {"status": "ok", "cluster_id": metric.cluster_id}


# ── Read endpoints ────────────────────────────────────────────────────────────

@app.get("/api/v1/clusters")
async def get_all_clusters():
    return {"clusters": list(cluster_metrics.keys())}


@app.get("/api/v1/clusters/{cluster_id}/metrics")
async def get_cluster_metrics(cluster_id: int, limit: int = 10):
    if cluster_id not in cluster_metrics:
        raise HTTPException(404, f"Cluster {cluster_id} not found")
    return {"cluster_id": cluster_id, "metrics": cluster_metrics[cluster_id][-limit:]}


@app.get("/api/v1/metrics/realtime")
async def get_realtime_metrics(limit: int = 5):
    """Return latest stored metric per cluster — no extra random generation."""
    realtime = [
        cluster_metrics[cid][-1]
        for cid in list(cluster_metrics.keys())[:limit]
        if cluster_metrics[cid]
    ]
    return {"metrics": realtime, "timestamp": datetime.now()}


@app.get("/api/v1/system/health")
async def get_system_health():
    health = calculate_system_health()
    system_health_history.append(health)
    return health


@app.get("/api/v1/alerts")
async def get_alerts(
    severity: Optional[str] = None,
    resolved: Optional[bool] = None,
    limit: int = 20,
):
    filtered = alerts.copy()
    if severity:
        filtered = [a for a in filtered if a.severity == severity.upper()]
    if resolved is not None:
        filtered = [a for a in filtered if a.resolved == resolved]
    filtered.sort(key=lambda x: x.timestamp, reverse=True)
    return {"alerts": filtered[:limit], "total": len(filtered)}


@app.get("/api/v1/alerts/active")
async def get_active_alerts():
    active = sorted(
        [a for a in alerts if not a.resolved],
        key=lambda x: x.timestamp, reverse=True,
    )
    return {"alerts": active}


@app.post("/api/v1/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: str):
    for a in alerts:
        if a.id == alert_id:
            a.resolved = True
            return {"message": f"Alert {alert_id} resolved"}
    raise HTTPException(404, f"Alert {alert_id} not found")


@app.get("/api/v1/metrics/trends")
async def get_metric_trends(cluster_id: Optional[int] = None, hours: int = 24):
    cutoff = datetime.now() - timedelta(hours=hours)
    clusters = [cluster_id] if cluster_id else list(cluster_metrics.keys())
    trends = {}
    for cid in clusters:
        if cid not in cluster_metrics:
            continue
        recent = [m for m in cluster_metrics[cid] if m.timestamp >= cutoff]
        if not recent:
            recent = cluster_metrics[cid][-1:]
        trends[cid] = {
            "cpu_trend":        [m.cpu_usage for m in recent],
            "memory_trend":     [m.memory_usage for m in recent],
            "latency_trend":    [m.latency_ms for m in recent],
            "throughput_trend": [m.network_throughput for m in recent],
            "rsrp_trend":       [m.rsrp for m in recent if m.rsrp is not None],
            "sinr_trend":       [m.sinr for m in recent if m.sinr is not None],
            "timestamps":       [m.timestamp.isoformat() for m in recent],
        }
    return {"trends": trends}


@app.get("/api/v1/performance/summary")
async def get_performance_summary():
    health = calculate_system_health()
    active = [a for a in alerts if not a.resolved]
    perf = 100 - (health.avg_cpu_usage * 0.4
                  + health.avg_memory_usage * 0.3
                  + health.avg_latency * 0.3)
    return {
        "system_health":         health,
        "active_alerts_count":   len(active),
        "critical_alerts_count": len([a for a in active if a.severity == "CRITICAL"]),
        "performance_score":     max(0, round(perf, 2)),
        "uptime":                health.uptime_percentage,
        "total_clusters":        health.total_clusters,
        "last_updated":          datetime.now(),
    }


# ── Startup ───────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup_event():
    initialize_sample_data()
    print(" Monitoring service ready on :8002")
    print(f"   RSRP_CRITICAL={RSRP_CRITICAL}  SINR_CRITICAL={SINR_CRITICAL}")
    print(f"   HO_RATE_HIGH={HO_RATE_HIGH}     VELOCITY_HIGH={VELOCITY_HIGH}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)