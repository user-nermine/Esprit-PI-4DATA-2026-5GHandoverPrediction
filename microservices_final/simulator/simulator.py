"""
DoNext 5G — Simulator
Generates realistic 101-feature KPI snapshots per cluster
and pushes them to the 3 microservices every N seconds.

Features generated = exact cols_X from PT_output/config.json (101 features):
  29 radio brutes + 2 temporelles + 5 gaps + 45 T-5 window +
  11 jointures + 4 flags + 4 encodages + 1 cluster_id

Usage:
    python simulator.py
    python simulator.py --interval 1
    python simulator.py --clusters 77 78 79
    python simulator.py --once
"""

import argparse
import random
import time
from datetime import datetime

import requests

# ── Service URLs (Docker container names) ─────────────────────
MONITORING_URL     = "http://donnext-monitoring:8002"
PREDICTION_URL     = "http://donnext-prediction:8003"
EXPLAINABILITY_URL = "http://donnext-explainability:8001"

DEFAULT_CLUSTERS = [77, 78, 79, 80, 81, 82, 83, 84, 85]
DEFAULT_INTERVAL = 3

# ── Cluster profiles from NB2 cluster_gps.json ───────────────
CLUSTER_PROFILES = {
    77: {"rsrp": -72.1, "sinr": 14.2, "ho_rate": 0.006, "lat": 51.499, "lon": 7.455},
    78: {"rsrp": -71.9, "sinr": 15.0, "ho_rate": 0.027, "lat": 51.501, "lon": 7.457},
    79: {"rsrp": -72.2, "sinr": 13.8, "ho_rate": 0.041, "lat": 51.498, "lon": 7.453},
    80: {"rsrp": -73.4, "sinr": 12.9, "ho_rate": 0.042, "lat": 51.502, "lon": 7.460},
    81: {"rsrp": -73.3, "sinr": 13.1, "ho_rate": 0.040, "lat": 51.500, "lon": 7.458},
    82: {"rsrp": -74.1, "sinr": 12.5, "ho_rate": 0.038, "lat": 51.497, "lon": 7.451},
    83: {"rsrp": -74.5, "sinr": 12.1, "ho_rate": 0.035, "lat": 51.503, "lon": 7.462},
    84: {"rsrp": -75.0, "sinr": 11.8, "ho_rate": 0.033, "lat": 51.496, "lon": 7.449},
    85: {"rsrp": -75.2, "sinr": 11.5, "ho_rate": 0.031, "lat": 51.504, "lon": 7.464},
}

# ── State per cluster (random walk) ──────────────────────────
_state: dict = {}


def _drift(v, step, lo, hi):
    return round(max(lo, min(hi, v + random.uniform(-step, step))), 3)


def _init(cluster_id: int) -> dict:
    p = CLUSTER_PROFILES.get(
        cluster_id,
        {"rsrp": -85.0, "sinr": 10.0, "ho_rate": 0.10, "lat": 51.50, "lon": 7.45},
    )
    rsrp = p["rsrp"] + random.uniform(-3, 3)
    sinr = p["sinr"] + random.uniform(-2, 2)
    rsrq = -10.0 + random.uniform(-3, 3)
    vel = random.uniform(0, 60)
    return {
        "rsrp": rsrp,
        "rsrq": rsrq,
        "rssi": rsrp + random.uniform(8, 12),
        "sinr": sinr,
        "cqi": max(1, min(15, 10 + sinr / 5)),
        "tx_power": random.uniform(-5, 5),
        "ss_rsrp": rsrp + random.uniform(-2, 2),
        "ss_rsrq": rsrq + random.uniform(-0.5, 0.5),
        "ss_sinr": sinr + random.uniform(-1, 1),
        "ta": float(random.randint(0, 30)),
        "earfcn": float(random.choice([1300, 3100, 66986])),
        "primary_bandwidth": float(random.choice([10, 15, 20])),
        "cellbandwidths": float(random.choice([10, 15, 20])),
        "ul_bandwidth": float(random.choice([10, 15, 20])),
        "lte_mcs": float(random.randint(0, 28)),
        "lte_ri": float(random.choice([1, 2, 4])),
        "nr_mcs": float(random.randint(0, 27)),
        "nr_ri": float(random.choice([1, 2, 4])),
        "mcc": 262.0,
        "mnc": float(random.choice([1, 2, 3])),
        "tracking_area_code": float(random.randint(1000, 9999)),
        "latitude": p["lat"] + random.uniform(-0.002, 0.002),
        "longitude": p["lon"] + random.uniform(-0.002, 0.002),
        "altitude": random.uniform(50, 200),
        "location_accuracy": random.uniform(5, 20),
        "velocity": vel,
        "velocity_accuracy": random.uniform(0.5, 2.0),
        "bearing": random.uniform(0, 360),
        "bearing_accuracy": random.uniform(5, 15),
        "n_records": float(random.randint(100, 400)),
        "ho_rate": p["ho_rate"] + random.uniform(-0.01, 0.01),
        # T-5 history (initialise as current value + small noise)
        "rsrp_h": [rsrp + random.uniform(-2, 2) for _ in range(5)],
        "rsrq_h": [rsrq + random.uniform(-0.5, 0.5) for _ in range(5)],
        "sinr_h": [sinr + random.uniform(-1, 1) for _ in range(5)],
        "rssi_h": [rsrp + 10 + random.uniform(-1, 1) for _ in range(5)],
        "cqi_h": [
            max(1, min(15, 10 + sinr / 5 + random.uniform(-0.5, 0.5))) for _ in range(5)
        ],
        "tx_h": [random.uniform(-5, 5) for _ in range(5)],
        "ss_rsrp_h": [rsrp + random.uniform(-2, 2) for _ in range(5)],
        "ss_rsrq_h": [rsrq + random.uniform(-0.5, 0.5) for _ in range(5)],
        "ss_sinr_h": [sinr + random.uniform(-1, 1) for _ in range(5)],
        # Jointures
        "mean_latency": random.uniform(10, 50),
        "mean_dev_latency": random.uniform(2, 10),
        "min_latency": random.uniform(5, 20),
        "max_latency": random.uniform(30, 100),
        "packet_loss_mean": random.uniform(0, 0.05),
        "datarate_mean": random.uniform(10, 200),
        "datarate_max": random.uniform(50, 500),
        "tcp_rtt_mean": random.uniform(15, 80),
        "retrans_mean": random.uniform(0, 0.1),
        "pkt_error_mean": random.uniform(0, 0.02),
        "nb_neighbors_pid": float(random.randint(2, 8)),
    }


def generate_kpi(cluster_id: int) -> dict:
    if cluster_id not in _state:
        _state[cluster_id] = _init(cluster_id)
    s = _state[cluster_id]

    # Drift main signals
    s["rsrp"] = _drift(s["rsrp"], 1.5, -115, -60)
    s["rsrq"] = _drift(s["rsrq"], 0.5, -20, -3)
    s["rssi"] = s["rsrp"] + random.uniform(8, 12)
    s["sinr"] = _drift(s["sinr"], 1.0, -15, 35)
    s["cqi"] = round(
        max(1, min(15, 10 + s["sinr"] / 5 + random.uniform(-0.5, 0.5))), 1
    )
    s["tx_power"] = _drift(s["tx_power"], 0.5, -10, 10)
    s["ss_rsrp"] = _drift(s["ss_rsrp"], 1.2, -115, -60)
    s["ss_rsrq"] = _drift(s["ss_rsrq"], 0.4, -20, -3)
    s["ss_sinr"] = _drift(s["ss_sinr"], 0.8, -15, 35)
    s["velocity"] = _drift(s["velocity"], 3.0, 0, 120)
    s["latitude"] = _drift(s["latitude"], 0.001, 33, 37)
    s["longitude"] = _drift(s["longitude"], 0.001, 8, 11)
    s["n_records"] = float(int(_drift(s["n_records"], 10, 50, 500)))
    s["ho_rate"] = _drift(s["ho_rate"], 0.02, 0, 0.5)

    # Drift jointures
    s["mean_latency"] = _drift(s["mean_latency"], 2.0, 1, 100)
    s["datarate_mean"] = _drift(s["datarate_mean"], 5.0, 10, 500)
    s["tcp_rtt_mean"] = _drift(s["tcp_rtt_mean"], 2.0, 10, 150)

    # Shift T-5 history (push current value in, drop oldest)
    for sig, hist in [
        ("rsrp", "rsrp_h"),
        ("rsrq", "rsrq_h"),
        ("sinr", "sinr_h"),
        ("rssi", "rssi_h"),
        ("cqi", "cqi_h"),
        ("tx_power", "tx_h"),
        ("ss_rsrp", "ss_rsrp_h"),
        ("ss_rsrq", "ss_rsrq_h"),
        ("ss_sinr", "ss_sinr_h"),
    ]:
        s[hist] = s[hist][1:] + [s[sig]]

    # Compute gaps (current - mean of last 3 neighbors simulated)
    neighbor_rsrq = s["rsrq"] + random.uniform(-3, 3)
    neighbor_rssi = s["rssi"] + random.uniform(-3, 3)
    neighbor_sinr = s["sinr"] + random.uniform(-3, 3)
    neighbor_cqi = s["cqi"] + random.uniform(-1, 1)
    neighbor_tx = s["tx_power"] + random.uniform(-2, 2)

    now = datetime.now()
    week = now.isocalendar()[1]
    dow = now.weekday()

    # Build full 101-feature dict (exact order matches cols_X NB3)
    features = {
        # ── Radio brutes (29) ──────────────────────────────────
        "earfcn": s["earfcn"],
        "rsrp": s["rsrp"],
        "rsrq": s["rsrq"],
        "rssi": s["rssi"],
        "sinr": s["sinr"],
        "ta": s["ta"],
        "cqi": s["cqi"],
        "primary_bandwidth": s["primary_bandwidth"],
        "cellbandwidths": s["cellbandwidths"],
        "ul_bandwidth": s["ul_bandwidth"],
        "lte_mcs": s["lte_mcs"],
        "lte_ri": s["lte_ri"],
        "nr_mcs": s["nr_mcs"],
        "nr_ri": s["nr_ri"],
        "tx_power": s["tx_power"],
        "mcc": s["mcc"],
        "mnc": s["mnc"],
        "ss_rsrp": s["ss_rsrp"],
        "ss_rsrq": s["ss_rsrq"],
        "ss_sinr": s["ss_sinr"],
        "latitude": s["latitude"],
        "longitude": s["longitude"],
        "altitude": s["altitude"],
        "location_accuracy": s["location_accuracy"],
        "velocity": s["velocity"],
        "velocity_accuracy": s["velocity_accuracy"],
        "bearing": s["bearing"],
        "bearing_accuracy": s["bearing_accuracy"],
        "tracking_area_code": s["tracking_area_code"],
        # ── Temporelles (2) ───────────────────────────────────
        "week_of_year": float(week),
        "day_of_week": float(dow),
        # ── KPI Gaps (5) ──────────────────────────────────────
        "rsrq_gap": round(s["rsrq"] - neighbor_rsrq, 3),
        "rssi_gap": round(s["rssi"] - neighbor_rssi, 3),
        "sinr_gap": round(s["sinr"] - neighbor_sinr, 3),
        "cqi_gap": round(s["cqi"] - neighbor_cqi, 3),
        "tx_power_gap": round(s["tx_power"] - neighbor_tx, 3),
        # ── Fenêtre T-5 (45) ──────────────────────────────────
        "rsrp_T1": s["rsrp_h"][4],
        "rsrp_T2": s["rsrp_h"][3],
        "rsrp_T3": s["rsrp_h"][2],
        "rsrp_T4": s["rsrp_h"][1],
        "rsrp_T5": s["rsrp_h"][0],
        "rsrq_T1": s["rsrq_h"][4],
        "rsrq_T2": s["rsrq_h"][3],
        "rsrq_T3": s["rsrq_h"][2],
        "rsrq_T4": s["rsrq_h"][1],
        "rsrq_T5": s["rsrq_h"][0],
        "sinr_T1": s["sinr_h"][4],
        "sinr_T2": s["sinr_h"][3],
        "sinr_T3": s["sinr_h"][2],
        "sinr_T4": s["sinr_h"][1],
        "sinr_T5": s["sinr_h"][0],
        "rssi_T1": s["rssi_h"][4],
        "rssi_T2": s["rssi_h"][3],
        "rssi_T3": s["rssi_h"][2],
        "rssi_T4": s["rssi_h"][1],
        "rssi_T5": s["rssi_h"][0],
        "cqi_T1": s["cqi_h"][4],
        "cqi_T2": s["cqi_h"][3],
        "cqi_T3": s["cqi_h"][2],
        "cqi_T4": s["cqi_h"][1],
        "cqi_T5": s["cqi_h"][0],
        "tx_power_T1": s["tx_h"][4],
        "tx_power_T2": s["tx_h"][3],
        "tx_power_T3": s["tx_h"][2],
        "tx_power_T4": s["tx_h"][1],
        "tx_power_T5": s["tx_h"][0],
        "ss_rsrp_T1": s["ss_rsrp_h"][4],
        "ss_rsrp_T2": s["ss_rsrp_h"][3],
        "ss_rsrp_T3": s["ss_rsrp_h"][2],
        "ss_rsrp_T4": s["ss_rsrp_h"][1],
        "ss_rsrp_T5": s["ss_rsrp_h"][0],
        "ss_rsrq_T1": s["ss_rsrq_h"][4],
        "ss_rsrq_T2": s["ss_rsrq_h"][3],
        "ss_rsrq_T3": s["ss_rsrq_h"][2],
        "ss_rsrq_T4": s["ss_rsrq_h"][1],
        "ss_rsrq_T5": s["ss_rsrq_h"][0],
        "ss_sinr_T1": s["ss_sinr_h"][4],
        "ss_sinr_T2": s["ss_sinr_h"][3],
        "ss_sinr_T3": s["ss_sinr_h"][2],
        "ss_sinr_T4": s["ss_sinr_h"][1],
        "ss_sinr_T5": s["ss_sinr_h"][0],
        # ── Jointures (11) ────────────────────────────────────
        "mean_latency": s["mean_latency"],
        "mean_dev_latency": s["mean_dev_latency"],
        "min_latency": s["min_latency"],
        "max_latency": s["max_latency"],
        "packet_loss_mean": s["packet_loss_mean"],
        "datarate_mean": s["datarate_mean"],
        "datarate_max": s["datarate_max"],
        "tcp_rtt_mean": s["tcp_rtt_mean"],
        "retrans_mean": s["retrans_mean"],
        "pkt_error_mean": s["pkt_error_mean"],
        "nb_neighbors_pid": s["nb_neighbors_pid"],
        # ── Flags (4) ─────────────────────────────────────────
        "has_gps": 1.0,
        "is_5g": 1.0,
        "has_iperf": 1.0,
        "has_neigh": 1.0,
        # ── Encodages (4) ─────────────────────────────────────
        "source_folder_enc": 1.0,
        "network_enc": 3.0,
        "MNO_enc": 0.0,
        "device_enc": 2.0,
        # ── Cluster NB2 (1) ───────────────────────────────────
        "cluster_id": float(cluster_id),
        "ho_rate": s["ho_rate"],
        "n_records": s["n_records"],
    }
    return features


# ── Push functions ────────────────────────────────────────────


def push_monitoring(cluster_id: int, kpi: dict, dso_result: dict = None) -> int:
    """
    Monitoring receives radio KPIs + optional DSO prediction results.
    dso1_proba and dso2_flag are needed for HO_IMMINENT and RSRP_DROP alerts.
    """
    payload = {
        "cluster_id": cluster_id,
        "timestamp": datetime.now().isoformat(),
        "cpu_usage": random.uniform(20, 85),
        "memory_usage": random.uniform(30, 80),
        "network_throughput": max(
            50, 1000 - abs(kpi["rsrp"]) * 3 + random.uniform(-50, 50)
        ),
        "latency_ms": max(1, 50 - kpi["sinr"] * 0.8 + random.uniform(-3, 3)),
        "packet_loss": max(0, kpi["ho_rate"] * 5 + random.uniform(-0.5, 0.5)),
        "availability": min(100, 98 + kpi["sinr"] / 100),
        "error_rate": max(0, kpi["ho_rate"] * 3 + random.uniform(-0.2, 0.2)),
        "active_connections": int(kpi["n_records"]),
        # Radio KPIs for alert generation
        "rsrp": kpi["rsrp"],
        "sinr": kpi["sinr"],
        "ho_rate": kpi["ho_rate"],
        "velocity": kpi["velocity"],
    }
    # Forward DSO1/DSO2 predictions so monitoring can fire CRITICAL alerts
    if dso_result:
        payload["dso1_proba"] = dso_result.get("dso1", {}).get("proba", 0.0)
        payload["dso2_flag"] = dso_result.get("dso2", {}).get("drop_flag", 0)
    r = requests.post(
        f"{MONITORING_URL}/api/v1/metrics/ingest", json=payload, timeout=3
    )
    return r.status_code


def push_prediction(cluster_id: int, kpi: dict) -> int:
    """
    Sends all 101 features to prediction service.
    The loaded .pkl model uses these to predict DSO1/2/3/4.
    cluster_id is inside features dict (NB4 assertion requirement).
    """
    payload = {"cluster_id": cluster_id, "features": kpi}
    r = requests.post(
        f"{PREDICTION_URL}/api/v1/clusters/ingest", json=payload, timeout=3
    )
    return r.status_code


def push_explainability(cluster_id: int, kpi: dict) -> int:
    """
    Sends KPIs to explainability service.
    cluster_id in both query param and body.
    """
    body = {
        k: kpi[k]
        for k in [
            "rsrp",
            "rsrq",
            "sinr",
            "cqi",
            "tx_power",
            "velocity",
            "latitude",
            "longitude",
            "n_records",
            "ho_rate",
            "rsrp_T1",
            "rsrq_gap",
            "sinr_gap",
            "cluster_id",
        ]
        if k in kpi
    }
    body["cluster_id"] = cluster_id
    r = requests.post(
        f"{EXPLAINABILITY_URL}/api/v1/explainability/cluster/ingest",
        params={"cluster_id": cluster_id},
        json=body,
        timeout=3,
    )
    return r.status_code


# ── Main loop ─────────────────────────────────────────────────


def run_once(cluster_ids: list, verbose: bool = True):
    results = []
    for cid in cluster_ids:
        kpi = generate_kpi(cid)
        row = {"cluster_id": cid, "ok": True}
        try:
            # 1. Predict first — we need DSO1/DSO2 results for monitoring alerts
            pred_status = push_prediction(cid, kpi)
            row["prediction"] = pred_status

            # 2. Fetch the prediction result to extract dso1_proba / dso2_flag
            dso_result = None
            try:
                r = requests.get(
                    f"{PREDICTION_URL}/api/v1/clusters/{cid}/predict", timeout=3
                )
                if r.status_code == 200:
                    dso_result = r.json()
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
                pass  # monitoring will fall back to radio-KPI-only alerts

            # 3. Push to monitoring with DSO results attached
            row["monitoring"] = push_monitoring(cid, kpi, dso_result)
            row["explainability"] = push_explainability(cid, kpi)
            row["ok"] = all(
                s in (200, 201)
                for s in [row["monitoring"], row["prediction"], row["explainability"]]
            )
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            row["ok"] = False
            row["error"] = str(e)
        results.append(row)

    if verbose:
        ts = datetime.now().strftime("%H:%M:%S")
        for row in results:
            if row["ok"]:
                print(
                    f"[{ts}] cluster={row['cluster_id']:>3}  "
                    f"mon={row['monitoring']}  pred={row['prediction']}  "
                    f"expl={row['explainability']}"
                )
            else:
                print(
                    f"[{ts}] cluster={row['cluster_id']:>3}  ⚠  {row.get('error', 'non-200')}"
                )
    return results


def run_loop(cluster_ids: list, interval: float):
    print(f"╔══════════════════════════════════════════════════╗")
    print(f"║  DoNext Simulator — 101 features                 ║")
    print(f"║  Clusters : {str(cluster_ids):<38}║")
    print(f"║  Interval : {interval}s                                   ║")
    print(f"║  Services : :8001  :8002  :8003                  ║")
    print(f"║  Press Ctrl+C to stop                            ║")
    print(f"╚══════════════════════════════════════════════════╝\n")
    while True:
        run_once(cluster_ids)
        time.sleep(interval)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DoNext KPI Simulator")
    parser.add_argument("--interval", type=float, default=DEFAULT_INTERVAL)
    parser.add_argument("--clusters", type=int, nargs="+", default=DEFAULT_CLUSTERS)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    if args.once:
        run_once(args.clusters)
    else:
        try:
            run_loop(args.clusters, args.interval)
        except KeyboardInterrupt:
            print("\n⏹  Simulator stopped.")