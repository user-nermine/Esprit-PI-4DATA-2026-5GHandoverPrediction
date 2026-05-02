"""
DonNext — Real-time KPI Simulator
Generates realistic cluster KPI snapshots every N seconds and pushes
them to all three microservices simultaneously.

Usage:
    python simulator.py                  # default: 3-second interval
    python simulator.py --interval 1     # 1-second interval
    python simulator.py --clusters 77 78 79  # specific clusters only
    python simulator.py --once           # push one round then exit
"""

import argparse
import random
import time
from datetime import datetime

import requests

# ─── Service URLs ─────────────────────────────────────────────────────────────

MONITORING_URL     = "http://localhost:8002"
PREDICTION_URL     = "http://localhost:8003"
EXPLAINABILITY_URL = "http://localhost:8001"

DEFAULT_CLUSTERS   = [77, 78, 79, 80, 81, 82, 83, 84, 85]
DEFAULT_INTERVAL   = 3   # seconds


# ─── KPI generation ───────────────────────────────────────────────────────────

# Persistent per-cluster "state" so values drift realistically over time
# instead of jumping randomly each tick.
_cluster_state: dict = {}

def _init_state(cluster_id: int) -> dict:
    return {
        "rsrp":     random.uniform(-100, -70),
        "rsrq":     random.uniform(-15,  -5),
        "sinr":     random.uniform(5,    25),
        "cqi":      random.uniform(5,    14),
        "tx_power": random.uniform(12,   22),
        "velocity": random.uniform(0,    80),
        "latitude": random.uniform(33,   37),
        "longitude":random.uniform(8,    11),
        "n_records":random.randint(100,  400),
        "ho_rate":  random.uniform(0.05, 0.30),
    }

def _drift(value: float, step: float, low: float, high: float) -> float:
    """Random walk clamped to [low, high]."""
    return round(max(low, min(high, value + random.uniform(-step, step))), 3)

def generate_kpi(cluster_id: int) -> dict:
    """Return a drifting KPI snapshot for a cluster."""
    if cluster_id not in _cluster_state:
        _cluster_state[cluster_id] = _init_state(cluster_id)

    s = _cluster_state[cluster_id]
    s["rsrp"]      = _drift(s["rsrp"],      1.5,  -115, -60)
    s["rsrq"]      = _drift(s["rsrq"],      0.5,  -20,  -3)
    s["sinr"]      = _drift(s["sinr"],      1.0,  0,    35)
    s["cqi"]       = _drift(s["cqi"],       0.3,  1,    15)
    s["tx_power"]  = _drift(s["tx_power"],  0.5,  10,   23)
    s["velocity"]  = _drift(s["velocity"],  3.0,  0,    120)
    s["latitude"]  = _drift(s["latitude"],  0.001,33,   37)
    s["longitude"] = _drift(s["longitude"], 0.001,8,    11)
    s["n_records"] = int(_drift(s["n_records"], 10, 50, 500))
    s["ho_rate"]   = _drift(s["ho_rate"],   0.02, 0,    0.5)

    return dict(s)   # return a copy


# ─── Push functions ───────────────────────────────────────────────────────────

def push_monitoring(cluster_id: int, kpi: dict) -> int:
    payload = {
        "cluster_id":         cluster_id,
        "timestamp":          datetime.now().isoformat(),
        # Map KPI fields to monitoring-specific fields
        "cpu_usage":          random.uniform(20, 85),
        "memory_usage":       random.uniform(30, 80),
        "network_throughput": random.uniform(100, 1000),
        "latency_ms":         max(1, 50 - kpi["sinr"] * 0.8 + random.uniform(-3, 3)),
        "packet_loss":        max(0, kpi["ho_rate"] * 5 + random.uniform(-0.5, 0.5)),
        "availability":       min(100, 98 + kpi["sinr"] / 100),
        "error_rate":         max(0, kpi["ho_rate"] * 3 + random.uniform(-0.2, 0.2)),
        "active_connections": kpi["n_records"],
    }
    r = requests.post(f"{MONITORING_URL}/api/v1/metrics/ingest", json=payload, timeout=3)
    return r.status_code


def push_prediction(cluster_id: int, kpi: dict) -> int:
    payload = {"cluster_id": cluster_id, "features": kpi}
    r = requests.post(f"{PREDICTION_URL}/api/v1/clusters/ingest", json=payload, timeout=3)
    return r.status_code


def push_explainability(cluster_id: int, kpi: dict) -> int:
    r = requests.post(
        f"{EXPLAINABILITY_URL}/api/v1/explainability/cluster/ingest",
        params={"cluster_id": cluster_id},
        json=kpi,
        timeout=3,
    )
    return r.status_code


# ─── Main loop ────────────────────────────────────────────────────────────────

def run_once(cluster_ids: list, verbose: bool = True):
    """Push one round of data to all services for all clusters."""
    results = []
    for cluster_id in cluster_ids:
        kpi = generate_kpi(cluster_id)
        row = {"cluster_id": cluster_id, "ok": True}
        try:
            s_mon  = push_monitoring(cluster_id, kpi)
            s_pred = push_prediction(cluster_id, kpi)
            s_expl = push_explainability(cluster_id, kpi)
            row["monitoring"]     = s_mon
            row["prediction"]     = s_pred
            row["explainability"] = s_expl
            row["ok"] = all(s in (200, 201) for s in [s_mon, s_pred, s_expl])
        except requests.exceptions.ConnectionError as e:
            row["ok"]    = False
            row["error"] = str(e)
        results.append(row)

    if verbose:
        ts = datetime.now().strftime("%H:%M:%S")
        for row in results:
            if row["ok"]:
                print(
                    f"[{ts}] cluster={row['cluster_id']:>3}  "
                    f"mon={row.get('monitoring')}  "
                    f"pred={row.get('prediction')}  "
                    f"expl={row.get('explainability')}"
                )
            else:
                print(f"[{ts}] cluster={row['cluster_id']:>3}  ⚠  {row.get('error', 'non-200 response')}")

    return results


def run_loop(cluster_ids: list, interval: float):
    print(f"╔══════════════════════════════════════════════════╗")
    print(f"║  DonNext Simulator                               ║")
    print(f"║  Clusters : {str(cluster_ids):<38}║")
    print(f"║  Interval : {interval}s{' ' * 37}║")
    print(f"║  Services : :8001  :8002  :8003                  ║")
    print(f"║  Press Ctrl+C to stop                            ║")
    print(f"╚══════════════════════════════════════════════════╝\n")

    while True:
        run_once(cluster_ids)
        time.sleep(interval)


# ─── CLI ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DonNext KPI Simulator")
    parser.add_argument(
        "--interval", type=float, default=DEFAULT_INTERVAL,
        help=f"Seconds between pushes (default: {DEFAULT_INTERVAL})"
    )
    parser.add_argument(
        "--clusters", type=int, nargs="+", default=DEFAULT_CLUSTERS,
        help="Cluster IDs to simulate (default: 77-85)"
    )
    parser.add_argument(
        "--once", action="store_true",
        help="Push one round then exit (useful for testing)"
    )
    args = parser.parse_args()

    if args.once:
        run_once(args.clusters)
    else:
        try:
            run_loop(args.clusters, args.interval)
        except KeyboardInterrupt:
            print("\n⏹  Simulator stopped.")