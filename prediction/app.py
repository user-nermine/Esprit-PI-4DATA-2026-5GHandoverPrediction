"""
DonNext — Prediction Microservice  (port 8003)
D:\\pipline_c\\prediction\\app.py

What changed vs original:
  1. Loads ALL 4 DSO models at startup (not just DSO1/xgb)
     DSO1 → xgb_model.pkl   (binary: HO failure)
     DSO2 → xgb_dso2.pkl    (binary: signal degradation)
     DSO3 → xgb_dso3.pkl    (multi-class: next-best cell)
            label_encoder_cells.pkl
     DSO4 → xgb_dso4.pkl    (multi-class: HO type)
  2. Reads feature list from PT_output/config.json (cols_X)
     AND falls back to simulator KPI keys when config absent
  3. Scaler applied when scaler_minmax.pkl present
  4. Ingest route aligned: POST /api/v1/clusters/ingest
     (was /ingest — angular frontend expects /api/v1/...)
  5. Results endpoint: GET /api/v1/clusters/{id}/predict
  6. All 4 DSO results returned in one response dict
  7. POST /api/v1/models/reload → hot-reload after Airflow retrains
  8. Results JSON read from MODEL_output/DSO*/results_dso*.json
     and exposed at GET /api/v1/models/performance
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime
from collections import defaultdict
import numpy as np
import joblib, os, json, pickle

app = FastAPI(
    title="DonNext Prediction Service",
    description="All-DSO inference — real pkl models from MODEL_output/",
    version="3.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Path config (override with env vars in Docker / Airflow) ──────────────────
BASE         = os.getenv("PIPELINE_ROOT", "/app")
MODEL_OUT    = os.path.join(BASE, "MODEL_output")
PT_OUT       = os.path.join(BASE, "PT_output")
CONFIG_PATH  = os.path.join(PT_OUT, "config.json")
SCALER_PATH  = os.path.join(PT_OUT, "scaler_minmax.pkl")

# DSO4 HO type labels (NB4_DSO4 CLASS_NAMES)
DSO4_LABELS = [
    "no_handover", "intra_freq", "inter_freq", "inter_RAT_NR",
    "inter_operator", "intra_freq_pci", "inter_freq_pci", "ho_non_type",
]

# ── Global model registry ─────────────────────────────────────────────────────
_models  = {}   # key → loaded estimator
_scaler  = None
_cols_x  = None  # ordered feature list from config.json
_results = {}   # DSO → metrics dict from results_dso*.json
_encoder_cells = None  # DSO3 label encoder

history: Dict[int, List[Dict]] = defaultdict(list)


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class IngestPayload(BaseModel):
    cluster_id: int
    features:   Dict[str, float]

class AllDSOResult(BaseModel):
    cluster_id:          int
    timestamp:           str
    # DSO1 — HO failure (binary)
    ho_failure_prob:     float
    ho_success_prob:     float
    ho_failure_pred:     int
    # DSO2 — signal degradation (binary)
    degradation_prob:    float
    degradation_pred:    int
    degradation_severity: str
    # DSO3 — next-best cell (multi-class)
    top_cells:           List[Dict]
    best_cell:           object
    # DSO4 — HO type (multi-class)
    ho_type_probs:       Dict[str, float]
    dominant_ho_type:    str
    # meta
    confidence:          float
    models_used:         Dict[str, str]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_pkl(path: str):
    if os.path.exists(path):
        try:
            return joblib.load(path)
        except Exception:
            try:
                with open(path, "rb") as f:
                    return pickle.load(f)
            except Exception as e:
                print(f"  {path}: {e}")
    else:
        print(f"  not found: {path}")
    return None


def _load_json(path: str):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}


def load_all_models():
    """Load all DSO models, scaler, config, and results metrics."""
    global _models, _scaler, _cols_x, _results, _encoder_cells

    print("Loading models from MODEL_output/ …")

    # Feature config
    cfg = _load_json(CONFIG_PATH)
    _cols_x = cfg.get("cols_X") or cfg.get("features") or None
    if _cols_x:
        print(f"  config.json: {len(_cols_x)} features")

    # Scaler
    _scaler = _load_pkl(SCALER_PATH)
    if _scaler:
        print("  scaler_minmax.pkl loaded")

    # DSO1 — binary HO failure
    _models["DSO1"] = _load_pkl(os.path.join(MODEL_OUT, "DSO1", "xgb_model.pkl"))
    if _models["DSO1"]: print("   DSO1 xgb_model.pkl")

    # DSO2 — binary signal degradation
    _models["DSO2"] = _load_pkl(os.path.join(MODEL_OUT, "DSO2", "xgb_dso2.pkl"))
    if _models["DSO2"]: print("   DSO2 xgb_dso2.pkl")

    # DSO3 — multi-class next-best cell
    _models["DSO3"] = _load_pkl(os.path.join(MODEL_OUT, "DSO3", "xgb_dso3.pkl"))
    _encoder_cells  = _load_pkl(os.path.join(MODEL_OUT, "DSO3", "label_encoder_cells.pkl"))
    if _models["DSO3"]: print("   DSO3 xgb_dso3.pkl")
    if _encoder_cells:  print("   DSO3 label_encoder_cells.pkl")

    # DSO4 — multi-class HO type
    _models["DSO4"] = _load_pkl(os.path.join(MODEL_OUT, "DSO4", "xgb_dso4.pkl"))
    if _models["DSO4"]: print("   DSO4 xgb_dso4.pkl")

    # Training metrics from results JSON
    for dso, fname in [("DSO1","results_dso1.json"), ("DSO2","results_dso2.json"),
                       ("DSO3","results_dso3.json"), ("DSO4","results_dso4.json")]:
        _results[dso] = _load_json(os.path.join(MODEL_OUT, dso, fname))

    print("Model loading complete.")


def _build_row(feats: Dict[str, float]) -> np.ndarray:
    """
    Build a feature row aligned to cols_X from config.json.
    Falls back to the raw feature dict values if config absent.
    """
    if _cols_x:
        row = [float(feats.get(c, 0.0)) for c in _cols_x]
    else:
        row = list(feats.values())
    X = np.array(row, dtype=np.float32).reshape(1, -1)
    if _scaler is not None:
        try:
            X = _scaler.transform(X)
        except Exception:
            pass  # shape mismatch if cols differ — skip scaling
    return X


def _physics_fallback(feats: Dict[str, float]) -> Dict:
    """Physics-based approximation when a model file is missing."""
    sinr     = float(feats.get("sinr",      15) or 15)
    velocity = float(feats.get("velocity",   0) or 0)
    ho_rate  = float(feats.get("ho_rate", 0.1) or 0.1)
    rsrp     = float(feats.get("rsrp",    -85) or -85)

    ho_fail  = min(0.95, max(0.02, ho_rate * 2.0))
    deg      = min(0.95, max(0.02, (-rsrp - 85) / 30))

    p_no    = max(0.05, min(0.85, 0.50 + sinr/100 - velocity/200))
    p_intra = max(0.05, min(0.85, 0.20 + velocity/300 + ho_rate*0.3))
    p_inter = max(0.05, min(0.85, 0.15 + velocity/400 + ho_rate*0.4))
    p_rat   = max(0.05, min(0.85, 0.10 + ho_rate*0.5 + max(0,(-rsrp-95)/50)))
    tot     = p_no + p_intra + p_inter + p_rat

    cid     = int(feats.get("cluster_id", 77))
    return {
        "dso1_fail": round(ho_fail, 4),
        "dso2_deg":  round(deg, 4),
        "dso3_cells":[{"cell_id": cid*10+i, "prob": round(0.6-i*0.15,4)} for i in range(3)],
        "dso4_probs":{
            "no_handover":  round(p_no/tot,4),
            "intra_freq":   round(p_intra/tot,4),
            "inter_freq":   round(p_inter/tot,4),
            "inter_RAT_NR": round(p_rat/tot,4),
        },
    }


def run_inference(cluster_id: int, feats: Dict[str, float]) -> AllDSOResult:
    X = _build_row(feats)
    fb = _physics_fallback(feats)
    models_used = {}

    # ── DSO1: HO failure ─────────────────────────────────────────────────────
    if _models.get("DSO1"):
        try:
            p1 = _models["DSO1"].predict_proba(X)[0]
            ho_fail_p = round(float(p1[1] if len(p1) > 1 else p1[0]), 4)
            models_used["DSO1"] = "XGBoost"
        except Exception as e:
            print(f"DSO1 inference error: {e}")
            ho_fail_p = fb["dso1_fail"]
            models_used["DSO1"] = "fallback"
    else:
        ho_fail_p = fb["dso1_fail"]
        models_used["DSO1"] = "fallback"

    ho_succ_p  = round(1 - ho_fail_p, 4)
    ho_fail_pred = int(ho_fail_p > 0.5)

    # ── DSO2: Signal degradation ──────────────────────────────────────────────
    if _models.get("DSO2"):
        try:
            p2 = _models["DSO2"].predict_proba(X)[0]
            deg_p = round(float(p2[1] if len(p2) > 1 else p2[0]), 4)
            models_used["DSO2"] = "XGBoost"
        except Exception as e:
            print(f"DSO2 inference error: {e}")
            deg_p = fb["dso2_deg"]
            models_used["DSO2"] = "fallback"
    else:
        deg_p = fb["dso2_deg"]
        models_used["DSO2"] = "fallback"

    deg_pred = int(deg_p > 0.5)
    severity = "critical" if deg_p > 0.75 else "warning" if deg_p > 0.40 else "none"

    # ── DSO3: Next-best cell ──────────────────────────────────────────────────
    if _models.get("DSO3"):
        try:
            p3     = _models["DSO3"].predict_proba(X)[0]
            labels3 = list(_encoder_cells.classes_) if _encoder_cells else \
                      [f"cell_{i}" for i in range(len(p3))]
            pairs  = sorted(zip(labels3, p3), key=lambda x: x[1], reverse=True)
            top_cells = [{"cell_id": c, "prob": round(float(p), 4)} for c, p in pairs[:3]]
            models_used["DSO3"] = "XGBoost"
        except Exception as e:
            print(f"DSO3 inference error: {e}")
            top_cells = fb["dso3_cells"]
            models_used["DSO3"] = "fallback"
    else:
        top_cells = fb["dso3_cells"]
        models_used["DSO3"] = "fallback"

    best_cell = top_cells[0]["cell_id"]

    # ── DSO4: HO type ─────────────────────────────────────────────────────────
    if _models.get("DSO4"):
        try:
            p4 = _models["DSO4"].predict_proba(X)[0]
            n  = min(len(p4), len(DSO4_LABELS))
            ho_type_probs = {DSO4_LABELS[i]: round(float(p4[i]), 4) for i in range(n)}
            models_used["DSO4"] = "XGBoost"
        except Exception as e:
            print(f"DSO4 inference error: {e}")
            ho_type_probs = fb["dso4_probs"]
            models_used["DSO4"] = "fallback"
    else:
        ho_type_probs = fb["dso4_probs"]
        models_used["DSO4"] = "fallback"

    dominant_ho = max(ho_type_probs, key=ho_type_probs.get)
    confidence  = round(ho_type_probs[dominant_ho], 4)

    return AllDSOResult(
        cluster_id=cluster_id,
        timestamp=datetime.utcnow().isoformat(),
        ho_failure_prob=ho_fail_p,
        ho_success_prob=ho_succ_p,
        ho_failure_pred=ho_fail_pred,
        degradation_prob=deg_p,
        degradation_pred=deg_pred,
        degradation_severity=severity,
        top_cells=top_cells,
        best_cell=best_cell,
        ho_type_probs=ho_type_probs,
        dominant_ho_type=dominant_ho,
        confidence=confidence,
        models_used=models_used,
    )


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"service": "prediction-service", "version": "3.0.0",
            "models_loaded": {k: v is not None for k, v in _models.items()}}


@app.get("/health")
def health():
    return {
        "status": "UP",
        "models": {k: v is not None for k, v in _models.items()},
        "scaler": _scaler is not None,
        "cols_x": len(_cols_x) if _cols_x else 0,
    }


# ── INGEST — called by simulator every 3 s ────────────────────────────────────

@app.post("/api/v1/clusters/ingest", status_code=201)
def ingest(payload: IngestPayload):
    """Receive KPI from simulator → run all 4 DSO models → store result."""
    feats = dict(payload.features)
    feats["cluster_id"] = float(payload.cluster_id)
    result = run_inference(payload.cluster_id, feats)
    history[payload.cluster_id].append(result.dict())
    if len(history[payload.cluster_id]) > 100:
        history[payload.cluster_id] = history[payload.cluster_id][-100:]
    return result


# ── Query endpoints ────────────────────────────────────────────────────────────

@app.get("/api/v1/clusters/{cluster_id}/predict")
def predict_cluster(cluster_id: int):
    """Return latest prediction for a cluster (or compute fresh)."""
    if history.get(cluster_id):
        return history[cluster_id][-1]
    # No history yet — run with neutral KPI
    feats = {"cluster_id": float(cluster_id), "rsrp": -85.0, "sinr": 15.0,
             "rsrq": -10.0, "cqi": 9.0, "tx_power": 15.0,
             "velocity": 30.0, "ho_rate": 0.1, "n_records": 200.0,
             "latitude": 35.0, "longitude": 9.5}
    result = run_inference(cluster_id, feats)
    history[cluster_id].append(result.dict())
    return result


@app.get("/api/v1/clusters/{cluster_id}/history")
def get_history(cluster_id: int, limit: int = 20):
    data = history.get(cluster_id, [])
    return {"cluster_id": cluster_id, "predictions": data[-limit:],
            "confidence_trend": [p["confidence"] for p in data[-limit:]]}


@app.get("/api/v1/predictions/realtime")
def get_realtime(limit: int = 9):
    latest = []
    for cid in list(history.keys())[:limit]:
        if history[cid]:
            latest.append(history[cid][-1])
    return {"predictions": latest, "timestamp": datetime.utcnow().isoformat()}


@app.get("/api/v1/predictions/summary")
def get_summary():
    total = sum(len(v) for v in history.values())
    from collections import Counter
    ho_counts: Counter = Counter()
    confs = []
    for preds in history.values():
        for p in preds:
            ho_counts[p["dominant_ho_type"]] += 1
            confs.append(p["confidence"])
    return {
        "total_predictions":         total,
        "clusters_with_predictions": len(history),
        "ho_type_distribution":      dict(ho_counts),
        "average_confidence":        round(sum(confs)/len(confs), 4) if confs else 0,
        "model_status":              {k: v is not None for k, v in _models.items()},
        "training_metrics":          _results,
        "last_updated":              datetime.utcnow().isoformat(),
    }


@app.get("/api/v1/models/performance")
def get_model_performance():
    """Return training metrics from MODEL_output/DSO*/results_dso*.json."""
    return {"metrics": _results,
            "model_status": {k: v is not None for k, v in _models.items()}}


@app.post("/api/v1/models/reload")
def reload_models():
    """
    Hot-reload all models after Airflow retraining completes.
    Called by the Airflow DAG task 'notify_services' via:
      curl -X POST http://localhost:8003/api/v1/models/reload
    """
    load_all_models()
    return {"message": "Models reloaded",
            "status": {k: v is not None for k, v in _models.items()}}


# ── Startup ───────────────────────────────────────────────────────────────────

@app.on_event("startup")
def startup():
    load_all_models()
    print(" Prediction service ready on :8003")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)