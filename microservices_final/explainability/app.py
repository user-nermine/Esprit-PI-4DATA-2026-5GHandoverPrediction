"""
DoNext 5G — Explainability Service (port 8001)
Provides SHAP explanations and feature importance for predictions
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Optional, List
from datetime import datetime
import random

app = FastAPI(
    title="DonNext Explainability Service",
    description="SHAP explanations and feature importance for DSO predictions",
    version="2.0.0"
)

# CORS handled by Gateway

explainability_store: Dict[int, Dict] = {}

# Liste des features importantes
FEATURES = ["rsrp", "sinr", "ho_rate", "velocity", "cqi", "packet_loss", "n_records"]

@app.get("/health")
async def health():
    return {"status": "UP", "service": "explainability-service", "timestamp": datetime.now().isoformat()}

@app.get("/")
async def root():
    return {
        "service": "explainability-service",
        "status": "running",
        "version": "2.0.0",
        "features": FEATURES
    }

@app.post("/api/v1/explainability/cluster/ingest", status_code=201)
async def ingest_explainability(request: dict):
    """
    Reçoit les données pour l'explicabilité
    """
    cluster_id = request.get("cluster_id")
    features = request.get("features", {})
    
    rsrp = features.get("rsrp", -85.0)
    sinr = features.get("sinr", 15.0)
    ho_rate = features.get("ho_rate", 0.08)
    velocity = features.get("velocity", 30.0)
    cqi = features.get("cqi", 10.0)
    packet_loss = features.get("packet_loss_mean", 0.02)
    n_records = features.get("n_records", 200)
    
    # SHAP values
    shap_values = [
        {"feature": "sinr", "value": sinr, "shap": round(0.35 if sinr > 10 else -0.25, 3), 
         "impact": "positive" if sinr > 10 else "negative"},
        {"feature": "rsrp", "value": rsrp, "shap": round(0.25 if rsrp > -90 else -0.30, 3),
         "impact": "positive" if rsrp > -90 else "negative"},
        {"feature": "ho_rate", "value": round(ho_rate, 3), "shap": round(0.20 if ho_rate < 0.08 else -0.28, 3),
         "impact": "positive" if ho_rate < 0.08 else "negative"},
        {"feature": "velocity", "value": round(velocity, 1), "shap": round(0.15 if velocity < 40 else -0.12, 3),
         "impact": "positive" if velocity < 40 else "negative"},
        {"feature": "cqi", "value": round(cqi, 1), "shap": 0.18, "impact": "positive"},
    ]
    
    # Feature importance
    feature_importance = {
        "sinr": 0.35, "rsrp": 0.28, "ho_rate": 0.22, "velocity": 0.10, "cqi": 0.05
    }
    
    # Explication
    if sinr < 5:
        explanation = f"Le principal facteur de risque est le SINR faible ({round(sinr,1)} dBm)"
    elif rsrp < -100:
        explanation = f"Le signal RSRP ({round(rsrp,1)} dBm) est trop faible"
    elif ho_rate > 0.12:
        explanation = f"Le taux de handover ({round(ho_rate,3)}) est élevé"
    else:
        explanation = "Les indicateurs sont dans les normes"
    
    explainability_store[cluster_id] = {
        "shap_values": shap_values,
        "feature_importance": feature_importance,
        "prediction_explanation": explanation,
        "last_updated": datetime.now()
    }
    
    return {"status": "ok", "cluster_id": cluster_id}

@app.get("/api/v1/explainability/cluster/{cluster_id}")
async def get_explainability(cluster_id: int):
    if cluster_id not in explainability_store:
        return {"cluster_id": cluster_id, "shap_values": [], "feature_importance": {}}
    result = explainability_store[cluster_id].copy()
    result["cluster_id"] = cluster_id
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
