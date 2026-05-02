"""
DonNext — Explainability Microservice  (port 8001)
Accepts cluster KPI data from the simulator, computes mock SHAP values
and feature importance, and exposes explainability endpoints.
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
from datetime import datetime
import random
from collections import defaultdict

app = FastAPI(
    title="DonNext Explainability Service",
    description="Microservice for cluster prediction explainability (SHAP + feature importance)",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Constants ────────────────────────────────────────────────────────────────

LABELS = ["no_handover", "intra_freq_handover", "inter_freq_handover", "inter_rat_handover"]
FEATURE_NAMES = ["rsrp", "rsrq", "sinr", "cqi", "tx_power", "velocity",
                 "latitude", "longitude", "n_records", "ho_rate"]

# ─── Models ───────────────────────────────────────────────────────────────────

class ClusterKPI(BaseModel):
    rsrp:       Optional[float] = None
    rsrq:       Optional[float] = None
    sinr:       Optional[float] = None
    cqi:        Optional[float] = None
    tx_power:   Optional[float] = None
    velocity:   Optional[float] = None
    latitude:   Optional[float] = None
    longitude:  Optional[float] = None
    n_records:  Optional[int]   = None
    ho_rate:    Optional[float] = None


class Predictions(BaseModel):
    no_handover:         float
    intra_freq_handover: float
    inter_freq_handover: float
    inter_rat_handover:  float


class ExplainabilityData(BaseModel):
    shap_values:        Dict[str, float]
    feature_importance: Dict[str, float]
    sample_size:        int
    model_type:         str


class ClusterExplainability(BaseModel):
    cluster_id:           int
    cluster_kpi:          ClusterKPI
    predictions:          Predictions
    explainability:       ExplainabilityData
    dominant_prediction:  str
    confidence:           float
    timestamp:            str


# ─── In-memory store ──────────────────────────────────────────────────────────

# Maps cluster_id → latest KPI dict (populated by simulator or defaults)
kpi_store:  Dict[int, dict] = {}
# Maps cluster_id → latest explainability result
expl_store: Dict[int, dict] = {}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _default_kpi(cluster_id: int) -> dict:
    """Generate a random KPI snapshot when no real data has been ingested yet."""
    return {
        "rsrp":      round(random.uniform(-110, -65), 2),
        "rsrq":      round(random.uniform(-18, -3),   2),
        "sinr":      round(random.uniform(0,   30),   2),
        "cqi":       round(random.uniform(1,   15),   1),
        "tx_power":  round(random.uniform(10,  23),   1),
        "velocity":  round(random.uniform(0,   120),  1),
        "latitude":  round(random.uniform(33,  37),   5),
        "longitude": round(random.uniform(8,   11),   5),
        "n_records": random.randint(50, 500),
        "ho_rate":   round(random.uniform(0,   0.4),  3),
    }


def _compute_explainability(cluster_id: int, kpi: dict) -> dict:
    """
    Compute mock predictions + SHAP values from a KPI dict.
    Replace the internals here with your real model calls.
    """
    sinr     = kpi.get("sinr", 15) or 15
    velocity = kpi.get("velocity", 0) or 0
    ho_rate  = kpi.get("ho_rate", 0.1) or 0.1

    # Soft probabilities driven by the KPIs
    p_no   = max(0.05, min(0.85,  0.5 + sinr / 100  - velocity / 200))
    p_intra = max(0.05, min(0.85, 0.2 + velocity / 300 + ho_rate * 0.3))
    p_inter = max(0.05, min(0.85, 0.2 + velocity / 400 + ho_rate * 0.4))
    p_rat   = max(0.05, min(0.85, 0.1 + ho_rate * 0.5))
    total   = p_no + p_intra + p_inter + p_rat
    probs   = {
        "no_handover":         round(p_no   / total, 4),
        "intra_freq_handover": round(p_intra / total, 4),
        "inter_freq_handover": round(p_inter / total, 4),
        "inter_rat_handover":  round(p_rat   / total, 4),
    }
    dominant   = max(probs, key=probs.get)
    confidence = round(probs[dominant] + random.uniform(0, 0.05), 4)

    # Mock SHAP values (sum ≈ 0, magnitude driven by feature value)
    shap_values = {}
    for feat in FEATURE_NAMES:
        val = kpi.get(feat) or 0
        shap_values[feat] = round((val / 100 + random.uniform(-0.05, 0.05)) * random.choice([-1, 1]), 4)

    # Feature importance (all positive, sum = 1)
    raw_imp = {f: abs(shap_values[f]) + random.uniform(0.01, 0.05) for f in FEATURE_NAMES}
    total_imp = sum(raw_imp.values())
    feature_importance = {f: round(v / total_imp, 4) for f, v in raw_imp.items()}

    return {
        "cluster_id":          cluster_id,
        "cluster_kpi":         kpi,
        "predictions":         probs,
        "explainability": {
            "shap_values":        shap_values,
            "feature_importance": feature_importance,
            "sample_size":        kpi.get("n_records", 100),
            "model_type":         "XGBoost",
        },
        "dominant_prediction": dominant,
        "confidence":          confidence,
        "timestamp":           datetime.now().isoformat(),
    }


def _get_or_compute(cluster_id: int) -> dict:
    kpi = kpi_store.get(cluster_id) or _default_kpi(cluster_id)
    result = _compute_explainability(cluster_id, kpi)
    expl_store[cluster_id] = result
    return result


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {"service": "explainability-service", "status": "running", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    return {
        "status": "UP",
        "service": "explainability-service",
        "timestamp": datetime.now().isoformat(),
        "clusters_ingested": len(kpi_store),
    }


# ── INGEST (called by simulator) ──────────────────────────────────────────────

@app.post("/api/v1/explainability/cluster/ingest", status_code=201)
async def ingest_cluster_kpi(cluster_id: int, kpi: ClusterKPI):
    """
    Receive real KPI data from the simulator.
    The next call to any explainability endpoint for this cluster will
    use this data instead of random defaults.
    """
    kpi_store[cluster_id] = kpi.dict(exclude_none=False)
    return {"status": "ok", "cluster_id": cluster_id}


# ── Explainability endpoints ───────────────────────────────────────────────────

@app.get("/api/v1/explainability/cluster/{cluster_id}", response_model=ClusterExplainability)
async def get_cluster_explainability(cluster_id: int):
    return _get_or_compute(cluster_id)


@app.get("/api/v1/explainability/cluster/{cluster_id}/predictions", response_model=Predictions)
async def get_cluster_predictions(cluster_id: int):
    data = _get_or_compute(cluster_id)
    return data["predictions"]


@app.get("/api/v1/explainability/cluster/{cluster_id}/shap")
async def get_cluster_shap_values(cluster_id: int):
    data = _get_or_compute(cluster_id)
    shap = data["explainability"]["shap_values"]
    return {"cluster_id": cluster_id, "shap_values": shap, "feature_names": list(shap.keys())}


@app.get("/api/v1/explainability/cluster/{cluster_id}/feature-importance")
async def get_cluster_feature_importance(cluster_id: int):
    data = _get_or_compute(cluster_id)
    fi   = data["explainability"]["feature_importance"]
    return {
        "cluster_id": cluster_id,
        "feature_importance": fi,
        "top_features": sorted(fi.items(), key=lambda x: x[1], reverse=True)[:10],
    }


@app.post("/api/v1/explainability/compare")
async def compare_clusters(cluster_ids: List[int]):
    if len(cluster_ids) < 2:
        raise HTTPException(status_code=400, detail="At least 2 clusters required")
    if len(cluster_ids) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 clusters")
    results = {cid: _get_or_compute(cid) for cid in cluster_ids}
    return {
        "cluster_ids": cluster_ids,
        "comparison": {
            cid: {
                "dominant_prediction": r["dominant_prediction"],
                "confidence":          r["confidence"],
                "top_feature":         max(r["explainability"]["feature_importance"], key=r["explainability"]["feature_importance"].get),
            }
            for cid, r in results.items()
        },
    }


@app.get("/api/v1/explainability/global/feature-importance")
async def get_global_feature_importance():
    """Average feature importance across all ingested clusters."""
    all_fi: Dict[str, List[float]] = defaultdict(list)
    for cid in (list(kpi_store.keys()) or list(range(77, 86))):
        data = _get_or_compute(cid)
        for feat, val in data["explainability"]["feature_importance"].items():
            all_fi[feat].append(val)
    global_fi = {f: round(sum(v) / len(v), 4) for f, v in all_fi.items()}
    return {
        "feature_importance": global_fi,
        "top_features": sorted(global_fi.items(), key=lambda x: x[1], reverse=True)[:10],
    }


@app.get("/api/v1/explainability/clusters/top-explainability")
async def get_top_clusters_explainability(limit: int = Query(10, ge=1, le=50)):
    cluster_ids = list(kpi_store.keys()) or list(range(77, 77 + limit))
    results = [_get_or_compute(cid) for cid in cluster_ids[:limit]]
    return {"total_clusters": len(results), "clusters": results}


@app.get("/api/v1/explainability/clusters/by-prediction/{prediction_type}")
async def get_clusters_by_prediction(prediction_type: str, limit: int = Query(20, ge=1, le=100)):
    if prediction_type not in LABELS:
        raise HTTPException(status_code=400, detail=f"Invalid type. Choose from: {LABELS}")
    results = [
        _get_or_compute(cid)
        for cid in list(kpi_store.keys())
        if _get_or_compute(cid)["dominant_prediction"] == prediction_type
    ][:limit]
    return {"prediction_type": prediction_type, "total_clusters": len(results), "clusters": results}


@app.get("/api/v1/explainability/summary")
async def get_explainability_summary():
    cluster_ids = list(kpi_store.keys()) or list(range(77, 97))
    analyzed = [_get_or_compute(cid) for cid in cluster_ids[:20]]
    pred_counts = {label: 0 for label in LABELS}
    conf_total  = 0.0
    for r in analyzed:
        pred_counts[r["dominant_prediction"]] += 1
        conf_total += r["confidence"]
    avg_conf = conf_total / len(analyzed) if analyzed else 0

    global_fi_resp = await get_global_feature_importance()
    return {
        "total_clusters":        len(cluster_ids),
        "analyzed_clusters":     len(analyzed),
        "average_confidence":    avg_conf,
        "prediction_distribution": pred_counts,
        "most_common_prediction": max(pred_counts, key=pred_counts.get),
        "global_feature_importance": global_fi_resp["feature_importance"],
        "top_features": global_fi_resp["top_features"][:10],
    }


@app.post("/api/v1/explainability/cluster/{cluster_id}/force-explain")
async def force_cluster_explainability(cluster_id: int):
    """Invalidate cache and recompute explainability for a cluster."""
    expl_store.pop(cluster_id, None)
    data = _get_or_compute(cluster_id)
    return {
        "message":            f"Explainability recomputed for cluster {cluster_id}",
        "cluster_id":         cluster_id,
        "dominant_prediction": data["dominant_prediction"],
        "confidence":          data["confidence"],
    }


# ─── Startup ──────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup_event():
    print("🔍 Explainability service ready on :8001")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)