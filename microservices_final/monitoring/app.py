"""
DoNext 5G — Monitoring Service (port 8002)

Fixes vs original:
  1. ClusterMetric: added rsrp/sinr/ho_rate/velocity fields
     so simulator radio KPIs can be stored and used for alerts
  2. generate_alert(): uses NB2/NB4 real thresholds
     rsrp < -110 → CRITICAL (NB2 FE-3, C54=-112.9 dBm)
     sinr < 0    → CRITICAL (NB2 FE-3, C51=-8.3 dB)
     ho_rate > 0.15 → HIGH (NB2 FE-5, C1=20.7%)
     DSO1 risk thresholds: P1>=0.70, P2>=0.50
  3. calculate_system_health(): fix division-by-zero bug
     uses rsrp/sinr for health classification when available
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
    description="Cluster monitoring with real NB2/NB4 alert thresholds",
    version="2.0.0",
)
# CORS handled by Gateway

# ── NB2/NB4 real thresholds ───────────────────────────────────
RSRP_CRITICAL = -110.0   # NB2 FE-3 (C54 = -112.9 dBm)
RSRP_HIGH     = -100.0   # signal degraded
SINR_CRITICAL =    0.0   # NB2 FE-3 (C51 = -8.3 dB)
SINR_HIGH     =    3.0   # NB4 alert service threshold
HO_RATE_HIGH  =   0.15   # NB2 FE-5 (C1=20.7%, C6=18.6%)
HO_RATE_MED   =   0.08
DSO1_P1       =   0.70   # NB4 DSO1
DSO1_P2       =   0.50

# ── Pydantic models ───────────────────────────────────────────

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
    # Radio KPIs from simulator (for NB2-based alerts)
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

# ── In-memory store ───────────────────────────────────────────
cluster_metrics:       Dict[int, List[ClusterMetric]] = defaultdict(list)
alerts:                List[Alert]                    = []
system_health_history: List[SystemHealth]             = []
_alert_counter = 0

# ── Helpers ───────────────────────────────────────────────────

def generate_cluster_metric(cluster_id: int, timestamp: datetime = None,
                             kpi: dict = None) -> ClusterMetric:
    if timestamp is None: timestamp = datetime.now()
    if kpi:
        sinr    = kpi.get("sinr",    15) or 15
        ho_rate = kpi.get("ho_rate", 0.1) or 0.1
        n_rec   = int(kpi.get("n_records", 200) or 200)
        rsrp    = kpi.get("rsrp",    -85) or -85
        velocity= kpi.get("velocity",  0) or 0
        return ClusterMetric(
            cluster_id=cluster_id, timestamp=timestamp,
            cpu_usage=max(0,min(100,30+velocity*.3+random.uniform(-5,10))),
            memory_usage=max(0,min(100,40+n_rec*.05+random.uniform(-5,10))),
            network_throughput=max(50,1000-abs(rsrp)*3+random.uniform(-50,50)),
            latency_ms=max(1,50-sinr*.8+random.uniform(-3,3)),
            packet_loss=max(0,ho_rate*5+random.uniform(-0.5,0.5)),
            availability=min(100,98+sinr/100),
            error_rate=max(0,ho_rate*3+random.uniform(-0.2,0.2)),
            active_connections=n_rec,
            rsrp=rsrp, sinr=sinr, ho_rate=ho_rate, velocity=velocity)
    else:
        return ClusterMetric(
            cluster_id=cluster_id, timestamp=timestamp,
            cpu_usage=max(0,min(100,30+random.uniform(-10,40))),
            memory_usage=max(0,min(100,40+random.uniform(-15,35))),
            network_throughput=random.uniform(100,1000),
            latency_ms=random.uniform(1,50), packet_loss=random.uniform(0,5),
            availability=random.uniform(95,100), error_rate=random.uniform(0,2),
            active_connections=random.randint(50,500))


def generate_alert(cluster_id: int, kpi: dict = None) -> Optional[Alert]:
    """
    Generate alert based on real NB2/NB4 thresholds.
    Returns None if no threshold exceeded.
    """
    global _alert_counter
    MESSAGES = {
        "RSRP_CRITICAL":  f"RSRP critique C{cluster_id} (≤{RSRP_CRITICAL} dBm — NB2 FE-3)",
        "RSRP_HIGH":      f"RSRP dégradé C{cluster_id} (≤{RSRP_HIGH} dBm)",
        "SINR_CRITICAL":  f"SINR négatif C{cluster_id} — interférence (NB2 FE-3)",
        "SINR_HIGH":      f"SINR faible C{cluster_id} (≤{SINR_HIGH} dB)",
        "HO_IMMINENT":    f"HO imminent C{cluster_id} (DSO1 ≥70%)",
        "HO_RISK":        f"Risque HO C{cluster_id} (DSO1 ≥50%)",
        "RSRP_DROP":      f"Chute signal imminente C{cluster_id} (DSO2)",
        "CLUSTER_RISK":   f"Zone à risque C{cluster_id} (ho_rate NB2 FE-5)",
        "CELL_CHANGE":    f"Changement cellule C{cluster_id} (velocity élevée)",
    }
    if kpi:
        rsrp    = kpi.get("rsrp",    -85) or -85
        sinr    = kpi.get("sinr",     15) or 15
        ho_rate = kpi.get("ho_rate", 0.1) or 0.1
        velocity= kpi.get("velocity",  0) or 0
        dso1_p  = float(kpi.get("dso1_proba", 0) or 0)
        dso2_f  = int(kpi.get("dso2_flag", 0) or 0)

        # P1 — CRITICAL
        if dso1_p >= DSO1_P1:
            t,s,th,cv = "HO_IMMINENT","CRITICAL",DSO1_P1,dso1_p
        elif rsrp <= RSRP_CRITICAL:
            t,s,th,cv = "RSRP_CRITICAL","CRITICAL",RSRP_CRITICAL,rsrp
        elif sinr <= SINR_CRITICAL:
            t,s,th,cv = "SINR_CRITICAL","CRITICAL",SINR_CRITICAL,sinr
        # P2 — HIGH
        elif dso2_f == 1:
            t,s,th,cv = "RSRP_DROP","HIGH",-6.0,rsrp
        elif dso1_p >= DSO1_P2:
            t,s,th,cv = "HO_RISK","HIGH",DSO1_P2,dso1_p
        elif rsrp <= RSRP_HIGH:
            t,s,th,cv = "RSRP_HIGH","HIGH",RSRP_HIGH,rsrp
        elif ho_rate >= HO_RATE_HIGH:
            t,s,th,cv = "CLUSTER_RISK","HIGH",HO_RATE_HIGH,ho_rate
        elif sinr <= SINR_HIGH:
            t,s,th,cv = "SINR_HIGH","MEDIUM",SINR_HIGH,sinr
        elif velocity > 100:
            t,s,th,cv = "CELL_CHANGE","MEDIUM",100.0,velocity
        else:
            return None  # No threshold exceeded — no alert
    else:
        # Fallback for initialization
        t = random.choice(["CLUSTER_RISK","RSRP_HIGH","SINR_HIGH"])
        s = random.choice(["MEDIUM","HIGH"])
        th = random.uniform(70,90); cv = random.uniform(75,95)

    _alert_counter += 1
    return Alert(
        id=f"alert_{cluster_id}_{_alert_counter:04d}",
        cluster_id=cluster_id, severity=s, type=t,
        message=MESSAGES.get(t,f"Alerte C{cluster_id}"),
        timestamp=datetime.now()-timedelta(minutes=random.randint(0,10)),
        resolved=False, metric_name=t.lower(), threshold=th, current_value=cv)


def calculate_system_health() -> SystemHealth:
    """
    FIX: use len(active) not total to avoid division by zero.
    Uses rsrp/sinr for health when available, cpu/latency otherwise.
    NB2 thresholds: rsrp > -100 AND sinr > 3 → healthy
    """
    active = [(cid, m[-1]) for cid, m in cluster_metrics.items() if m]
    n = max(len(active), 1)
    healthy = warning = critical = 0
    sum_cpu=sum_mem=sum_lat=sum_tput = 0.0

    for _, m in active:
        if m.rsrp is not None and m.sinr is not None:
            # NB2-based classification
            if m.rsrp > RSRP_HIGH and m.sinr > SINR_HIGH:
                healthy += 1
            elif m.rsrp > RSRP_CRITICAL and m.sinr > SINR_CRITICAL:
                warning += 1
            else:
                critical += 1
        else:
            # IT-based fallback
            if m.cpu_usage<70 and m.memory_usage<70 and m.latency_ms<25 and m.availability>99:
                healthy+=1
            elif m.cpu_usage<85 and m.memory_usage<85 and m.latency_ms<40:
                warning+=1
            else:
                critical+=1
        sum_cpu+=m.cpu_usage; sum_mem+=m.memory_usage
        sum_lat+=m.latency_ms; sum_tput+=m.network_throughput

    return SystemHealth(
        total_clusters=len(active),
        healthy_clusters=healthy, warning_clusters=warning, critical_clusters=critical,
        avg_cpu_usage=round(sum_cpu/n,2), avg_memory_usage=round(sum_mem/n,2),
        avg_latency=round(sum_lat/n,2), total_throughput=round(sum_tput,2),
        uptime_percentage=round(99.5+random.uniform(-0.3,0.5),3),
        last_updated=datetime.now())


def _store_metric(metric: ClusterMetric):
    cluster_metrics[metric.cluster_id].append(metric)
    if len(cluster_metrics[metric.cluster_id]) > 100:
        cluster_metrics[metric.cluster_id] = cluster_metrics[metric.cluster_id][-100:]


def initialize_sample_data():
    for cid in [77,78,79,80,81,82,83,84,85]:
        for h in range(24,0,-1):
            _store_metric(generate_cluster_metric(cid, datetime.now()-timedelta(hours=h)))
    # Seed a few resolved alerts
    for i in range(5):
        a = generate_alert([77,78,79,80,81][i%5])
        if a: a.resolved=True; alerts.append(a)

# ── Routes ────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {"service":"monitoring-service","status":"running","version":"2.0.0",
            "thresholds":{"rsrp_critical":RSRP_CRITICAL,"rsrp_high":RSRP_HIGH,
                          "sinr_critical":SINR_CRITICAL,"ho_rate_high":HO_RATE_HIGH,
                          "dso1_p1":DSO1_P1,"dso1_p2":DSO1_P2}}

@app.get("/health")
async def health():
    return {"status":"UP","service":"monitoring-service",
            "timestamp":datetime.now().isoformat(),
            "clusters_monitored":len(cluster_metrics)}

@app.post("/api/v1/metrics/ingest", status_code=201)
async def ingest_metric(metric: ClusterMetric):
    _store_metric(metric)
    # Generate alert from radio KPIs if thresholds exceeded
    kpi = {"rsrp":metric.rsrp,"sinr":metric.sinr,
           "ho_rate":metric.ho_rate,"velocity":metric.velocity}
    if any(v is not None for v in kpi.values()):
        alert = generate_alert(metric.cluster_id, kpi)
        if alert:
            alerts.append(alert)
            if len(alerts) > 500: alerts[:] = alerts[-500:]
    return {"status":"ok","cluster_id":metric.cluster_id}

@app.get("/api/v1/clusters")
async def get_clusters():
    return {"clusters":list(cluster_metrics.keys())}

@app.get("/api/v1/clusters/{cluster_id}/metrics")
async def get_cluster_metrics(cluster_id:int, limit:int=10):
    if cluster_id not in cluster_metrics:
        raise HTTPException(404, f"Cluster {cluster_id} not found")
    return {"cluster_id":cluster_id,"metrics":cluster_metrics[cluster_id][-limit:]}

@app.get("/api/v1/metrics/realtime")
async def get_realtime(limit:int=5):
    realtime=[cluster_metrics[cid][-1]
              for cid in list(cluster_metrics.keys())[:limit]
              if cluster_metrics[cid]]
    return {"metrics":realtime,"timestamp":datetime.now()}

@app.get("/api/v1/system/health")
async def get_health():
    h=calculate_system_health(); system_health_history.append(h); return h

@app.get("/api/v1/alerts")
async def get_alerts(severity:Optional[str]=None,resolved:Optional[bool]=None,limit:int=20):
    filtered=alerts.copy()
    if severity: filtered=[a for a in filtered if a.severity==severity.upper()]
    if resolved is not None: filtered=[a for a in filtered if a.resolved==resolved]
    filtered.sort(key=lambda x:x.timestamp,reverse=True)
    return {"alerts":filtered[:limit],"total":len(filtered)}

@app.get("/api/v1/alerts/active")
async def get_active():
    active=sorted([a for a in alerts if not a.resolved],
                  key=lambda x:x.timestamp,reverse=True)
    return {"alerts":active}

@app.post("/api/v1/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id:str):
    for a in alerts:
        if a.id==alert_id: a.resolved=True; return {"message":f"Alert {alert_id} resolved"}
    raise HTTPException(404,f"Alert {alert_id} not found")

@app.get("/api/v1/metrics/trends")
async def get_trends(cluster_id:Optional[int]=None,hours:int=24):
    cutoff=datetime.now()-timedelta(hours=hours)
    clusters=[cluster_id] if cluster_id else list(cluster_metrics.keys())
    trends={}
    for cid in clusters:
        if cid not in cluster_metrics: continue
        recent=[m for m in cluster_metrics[cid] if m.timestamp>=cutoff]
        if not recent: recent=cluster_metrics[cid][-1:] if cluster_metrics[cid] else []
        trends[cid]={
            "cpu_trend":       [m.cpu_usage for m in recent],
            "memory_trend":    [m.memory_usage for m in recent],
            "latency_trend":   [m.latency_ms for m in recent],
            "throughput_trend":[m.network_throughput for m in recent],
            "rsrp_trend":      [m.rsrp for m in recent if m.rsrp is not None],
            "sinr_trend":      [m.sinr for m in recent if m.sinr is not None],
            "timestamps":      [m.timestamp.isoformat() for m in recent],
        }
    return {"trends":trends}

@app.get("/api/v1/performance/summary")
async def get_performance():
    health=calculate_system_health()
    active=[a for a in alerts if not a.resolved]
    perf=100-(health.avg_cpu_usage*.4+health.avg_memory_usage*.3+health.avg_latency*.3)
    return {"system_health":health,
            "active_alerts_count":len(active),
            "critical_alerts_count":len([a for a in active if a.severity=="CRITICAL"]),
            "performance_score":max(0,round(perf,2)),
            "uptime":health.uptime_percentage,
            "total_clusters":health.total_clusters,
            "last_updated":datetime.now()}

@app.on_event("startup")
async def startup():
    initialize_sample_data()
    print("🔧 Monitoring service ready on :8002")
    print(f"   Thresholds: RSRP_CRITICAL={RSRP_CRITICAL} SINR_CRITICAL={SINR_CRITICAL}")
    print(f"   HO_RATE_HIGH={HO_RATE_HIGH} DSO1_P1={DSO1_P1}")

if __name__=="__main__":
    import uvicorn; uvicorn.run(app,host="0.0.0.0",port=8002)

