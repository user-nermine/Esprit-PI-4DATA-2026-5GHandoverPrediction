"""
DonNext Monitoring Microservice
Python FastAPI service for cluster monitoring and metrics
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
    version="1.0.0"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
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
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    type: str
    message: str
    timestamp: datetime
    resolved: bool
    metric_name: Optional[str] = None
    threshold: Optional[float] = None
    current_value: Optional[float] = None

# In-memory storage (in production, use Redis or database)
cluster_metrics: Dict[int, List[ClusterMetric]] = defaultdict(list)
alerts: List[Alert] = []
system_health_history: List[SystemHealth] = []

# Initialize with sample data
def initialize_sample_data():
    """Initialize with sample cluster metrics"""
    cluster_ids = [77, 78, 79, 80, 81, 82, 83, 84, 85]
    
    for cluster_id in cluster_ids:
        # Generate last 24 hours of metrics (every hour)
        for hours_ago in range(24, 0, -1):
            timestamp = datetime.now() - timedelta(hours=hours_ago)
            metric = generate_cluster_metric(cluster_id, timestamp)
            cluster_metrics[cluster_id].append(metric)
    
    # Generate initial alerts
    for i in range(5):
        alert = generate_alert(cluster_ids[i % len(cluster_ids)])
        alerts.append(alert)

def generate_cluster_metric(cluster_id: int, timestamp: datetime = None) -> ClusterMetric:
    """Generate a realistic cluster metric"""
    if timestamp is None:
        timestamp = datetime.now()
    
    # Generate realistic metrics with some randomness
    base_cpu = 30 + random.uniform(-10, 40)
    base_memory = 40 + random.uniform(-15, 35)
    
    return ClusterMetric(
        cluster_id=cluster_id,
        timestamp=timestamp,
        cpu_usage=max(0, min(100, base_cpu + random.uniform(-5, 5))),
        memory_usage=max(0, min(100, base_memory + random.uniform(-5, 5))),
        network_throughput=random.uniform(100, 1000),  # Mbps
        latency_ms=random.uniform(1, 50),
        packet_loss=random.uniform(0, 5),  # percentage
        availability=random.uniform(95, 100),  # percentage
        error_rate=random.uniform(0, 2),  # percentage
        active_connections=random.randint(50, 500)
    )

def generate_alert(cluster_id: int) -> Alert:
    """Generate a realistic alert"""
    severities = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    alert_types = ["CPU_HIGH", "MEMORY_HIGH", "LATENCY_HIGH", "PACKET_LOSS", "CONNECTIONS_HIGH"]
    
    severity = random.choice(severities)
    alert_type = random.choice(alert_types)
    
    messages = {
        "CPU_HIGH": f"CPU usage is above threshold for cluster {cluster_id}",
        "MEMORY_HIGH": f"Memory usage is critical for cluster {cluster_id}",
        "LATENCY_HIGH": f"High latency detected on cluster {cluster_id}",
        "PACKET_LOSS": f"Packet loss detected on cluster {cluster_id}",
        "CONNECTIONS_HIGH": f"Too many active connections on cluster {cluster_id}"
    }
    
    return Alert(
        id=f"alert_{cluster_id}_{random.randint(1000, 9999)}",
        cluster_id=cluster_id,
        severity=severity,
        type=alert_type,
        message=messages[alert_type],
        timestamp=datetime.now() - timedelta(minutes=random.randint(1, 60)),
        resolved=random.choice([True, False]),
        metric_name=alert_type.lower().replace("_", "_"),
        threshold=random.uniform(70, 90),
        current_value=random.uniform(75, 95)
    )

def calculate_system_health() -> SystemHealth:
    """Calculate overall system health"""
    total_clusters = len(cluster_metrics)
    healthy_clusters = 0
    warning_clusters = 0
    critical_clusters = 0
    
    total_cpu = 0
    total_memory = 0
    total_latency = 0
    total_throughput = 0
    
    for cluster_id, metrics in cluster_metrics.items():
        if metrics:
            latest_metric = metrics[-1]
            
            # Determine cluster health based on latest metrics
            if (latest_metric.cpu_usage < 70 and 
                latest_metric.memory_usage < 70 and 
                latest_metric.latency_ms < 20 and 
                latest_metric.availability > 99):
                healthy_clusters += 1
            elif (latest_metric.cpu_usage < 85 and 
                  latest_metric.memory_usage < 85 and 
                  latest_metric.latency_ms < 40):
                warning_clusters += 1
            else:
                critical_clusters += 1
            
            total_cpu += latest_metric.cpu_usage
            total_memory += latest_metric.memory_usage
            total_latency += latest_metric.latency_ms
            total_throughput += latest_metric.network_throughput
    
    return SystemHealth(
        total_clusters=total_clusters,
        healthy_clusters=healthy_clusters,
        warning_clusters=warning_clusters,
        critical_clusters=critical_clusters,
        avg_cpu_usage=total_cpu / total_clusters if total_clusters > 0 else 0,
        avg_memory_usage=total_memory / total_clusters if total_clusters > 0 else 0,
        avg_latency=total_latency / total_clusters if total_clusters > 0 else 0,
        total_throughput=total_throughput,
        uptime_percentage=99.5 + random.uniform(-0.5, 0.5),
        last_updated=datetime.now()
    )

# API Endpoints
@app.get("/")
async def root():
    return {"service": "monitoring-service", "status": "running", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {
        "status": "UP",
        "service": "monitoring-service",
        "timestamp": datetime.now().isoformat(),
        "clusters_monitored": len(cluster_metrics)
    }

@app.get("/api/v1/clusters")
async def get_all_clusters():
    """Get all monitored cluster IDs"""
    return {"clusters": list(cluster_metrics.keys())}

@app.get("/api/v1/clusters/{cluster_id}/metrics")
async def get_cluster_metrics(cluster_id: int, limit: int = 10):
    """Get metrics for a specific cluster"""
    if cluster_id not in cluster_metrics:
        raise HTTPException(status_code=404, detail=f"Cluster {cluster_id} not found")
    
    metrics = cluster_metrics[cluster_id][-limit:]
    return {"cluster_id": cluster_id, "metrics": metrics}

@app.get("/api/v1/metrics/realtime")
async def get_realtime_metrics(limit: int = 5):
    """Get real-time metrics for monitoring dashboard"""
    realtime_metrics = []
    
    for cluster_id in list(cluster_metrics.keys())[:limit]:
        # Generate current metric
        current_metric = generate_cluster_metric(cluster_id)
        cluster_metrics[cluster_id].append(current_metric)
        
        # Keep only last 100 metrics per cluster
        if len(cluster_metrics[cluster_id]) > 100:
            cluster_metrics[cluster_id] = cluster_metrics[cluster_id][-100:]
        
        realtime_metrics.append(current_metric)
    
    return {"metrics": realtime_metrics, "timestamp": datetime.now()}

@app.get("/api/v1/system/health")
async def get_system_health():
    """Get overall system health"""
    health = calculate_system_health()
    system_health_history.append(health)
    
    # Keep only last 100 health records
    if len(system_health_history) > 100:
        system_health_history[-100:]
    
    return health

@app.get("/api/v1/alerts")
async def get_alerts(severity: Optional[str] = None, resolved: Optional[bool] = None, limit: int = 20):
    """Get alerts with optional filters"""
    filtered_alerts = alerts.copy()
    
    if severity:
        filtered_alerts = [a for a in filtered_alerts if a.severity == severity.upper()]
    
    if resolved is not None:
        filtered_alerts = [a for a in filtered_alerts if a.resolved == resolved]
    
    # Sort by timestamp (most recent first)
    filtered_alerts.sort(key=lambda x: x.timestamp, reverse=True)
    
    return {"alerts": filtered_alerts[:limit], "total": len(filtered_alerts)}

@app.get("/api/v1/alerts/active")
async def get_active_alerts():
    """Get only active (unresolved) alerts"""
    active_alerts = [a for a in alerts if not a.resolved]
    active_alerts.sort(key=lambda x: x.timestamp, reverse=True)
    return {"alerts": active_alerts}

@app.post("/api/v1/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: str):
    """Resolve an alert"""
    for alert in alerts:
        if alert.id == alert_id:
            alert.resolved = True
            return {"message": f"Alert {alert_id} resolved"}
    
    raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")

@app.get("/api/v1/metrics/trends")
async def get_metric_trends(cluster_id: Optional[int] = None, hours: int = 24):
    """Get metric trends over time"""
    trends = {}
    
    clusters_to_check = [cluster_id] if cluster_id else list(cluster_metrics.keys())
    
    for cid in clusters_to_check:
        if cid in cluster_metrics:
            # Get metrics from last N hours
            cutoff_time = datetime.now() - timedelta(hours=hours)
            recent_metrics = [m for m in cluster_metrics[cid] if m.timestamp >= cutoff_time]
            
            trends[cid] = {
                "cpu_trend": [m.cpu_usage for m in recent_metrics],
                "memory_trend": [m.memory_usage for m in recent_metrics],
                "latency_trend": [m.latency_ms for m in recent_metrics],
                "throughput_trend": [m.network_throughput for m in recent_metrics],
                "timestamps": [m.timestamp.isoformat() for m in recent_metrics]
            }
    
    return {"trends": trends}

@app.get("/api/v1/performance/summary")
async def get_performance_summary():
    """Get performance summary for dashboard"""
    health = calculate_system_health()
    active_alerts = [a for a in alerts if not a.resolved]
    
    # Calculate performance metrics
    avg_performance = 100 - (health.avg_cpu_usage * 0.4 + health.avg_memory_usage * 0.3 + health.avg_latency * 0.3)
    
    return {
        "system_health": health,
        "active_alerts_count": len(active_alerts),
        "critical_alerts_count": len([a for a in active_alerts if a.severity == "CRITICAL"]),
        "performance_score": max(0, avg_performance),
        "uptime": health.uptime_percentage,
        "total_clusters": health.total_clusters,
        "last_updated": datetime.now()
    }

# Initialize sample data on startup
@app.on_event("startup")
async def startup_event():
    initialize_sample_data()
    print("ðŸ”§ Monitoring service initialized with sample data")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)

