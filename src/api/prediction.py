"""
DonNext Prediction Microservice
Python FastAPI service for cluster predictions with 4 targets
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import random
from collections import defaultdict

app = FastAPI(
    title="DonNext Prediction Service",
    description="Microservice for cluster predictions with 4 target models",
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
class PredictionTarget(BaseModel):
    name: str  # no_handover, intra_freq_handover, inter_freq_handover, inter_rat_handover
    probability: float
    confidence: float

class ModelPerformance(BaseModel):
    model_name: str
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    auc_roc: float
    training_samples: int
    last_updated: datetime

class ClusterPrediction(BaseModel):
    cluster_id: int
    timestamp: datetime
    predictions: List[PredictionTarget]
    dominant_prediction: str
    confidence: float
    model_used: str
    features_used: Dict[str, float]

class ModelComparison(BaseModel):
    models: List[str]
    metrics_comparison: Dict[str, Dict[str, float]]
    best_model: str
    best_model_metrics: Dict[str, float]
    recommendation: str

class PredictionHistory(BaseModel):
    cluster_id: int
    predictions: List[ClusterPrediction]
    accuracy_trend: List[float]
    confidence_trend: List[float]

# In-memory storage (in production, use database)
cluster_predictions: Dict[int, List[ClusterPrediction]] = defaultdict(list)
model_performances: Dict[str, ModelPerformance] = {}
prediction_history: Dict[int, List[ClusterPrediction]] = defaultdict(list)

# Available models
AVAILABLE_MODELS = ["XGBoost", "RandomForest", "NeuralNetwork", "LogisticRegression"]
TARGET_NAMES = ["no_handover", "intra_freq_handover", "inter_freq_handover", "inter_rat_handover"]

def initialize_models():
    """Initialize model performances"""
    for model_name in AVAILABLE_MODELS:
        # Generate realistic model performance metrics
        base_accuracy = 0.85 + random.uniform(-0.1, 0.12)
        
        model_performances[model_name] = ModelPerformance(
            model_name=model_name,
            accuracy=base_accuracy,
            precision=base_accuracy + random.uniform(-0.05, 0.05),
            recall=base_accuracy + random.uniform(-0.05, 0.05),
            f1_score=base_accuracy + random.uniform(-0.03, 0.03),
            auc_roc=base_accuracy + random.uniform(0.02, 0.08),
            training_samples=random.randint(10000, 50000),
            last_updated=datetime.now() - timedelta(hours=random.randint(1, 24))
        )

def generate_cluster_features(cluster_id: int) -> Dict[str, float]:
    """Generate realistic cluster features"""
    return {
        "rsrp": -70.0 - random.uniform(0, 25),
        "rsrq": -10.0 - random.uniform(0, 8),
        "sinr": 15.0 + random.uniform(-10, 15),
        "cqi": 10.0 + random.uniform(-5, 6),
        "velocity": random.uniform(0, 120),
        "cell_load": random.uniform(0.3, 0.9),
        "handover_history": random.uniform(0, 0.5),
        "signal_stability": random.uniform(0.6, 1.0),
        "interference": random.uniform(0, 0.4),
        "ue_density": random.uniform(50, 500)
    }

def generate_predictions(features: Dict[str, float], model_name: str) -> List[PredictionTarget]:
    """Generate predictions based on features and model"""
    # Simulate model-specific prediction patterns
    if model_name == "XGBoost":
        # XGBoost tends to be more confident
        base_probs = [0.4, 0.3, 0.2, 0.1]
        confidence_boost = 0.1
    elif model_name == "RandomForest":
        # RandomForest is more balanced
        base_probs = [0.35, 0.3, 0.25, 0.1]
        confidence_boost = 0.05
    elif model_name == "NeuralNetwork":
        # NeuralNetwork can be more variable
        base_probs = [0.3, 0.35, 0.25, 0.1]
        confidence_boost = 0.08
    else:  # LogisticRegression
        # LogisticRegression is more conservative
        base_probs = [0.45, 0.25, 0.2, 0.1]
        confidence_boost = 0.03
    
    # Adjust probabilities based on features
    sinr_factor = max(0, min(1, features["sinr"] / 25))
    velocity_factor = max(0, min(1, features["velocity"] / 100))
    
    # High SINR increases no_handover probability
    base_probs[0] += sinr_factor * 0.2
    # High velocity increases handover probabilities
    base_probs[1] += velocity_factor * 0.1
    base_probs[2] += velocity_factor * 0.15
    
    # Normalize probabilities
    total = sum(base_probs)
    normalized_probs = [p / total for p in base_probs]
    
    # Add some randomness
    noise = [random.uniform(-0.05, 0.05) for _ in range(4)]
    final_probs = [max(0, min(1, p + n)) for p, n in zip(normalized_probs, noise)]
    
    # Renormalize
    total = sum(final_probs)
    final_probs = [p / total for p in final_probs]
    
    predictions = []
    for i, target_name in enumerate(TARGET_NAMES):
        confidence = final_probs[i] + confidence_boost + random.uniform(-0.05, 0.05)
        predictions.append(PredictionTarget(
            name=target_name,
            probability=final_probs[i],
            confidence=max(0, min(1, confidence))
        ))
    
    return predictions

def generate_cluster_prediction(cluster_id: int, model_name: str = None) -> ClusterPrediction:
    """Generate a cluster prediction"""
    if model_name is None:
        model_name = random.choice(AVAILABLE_MODELS)
    
    features = generate_cluster_features(cluster_id)
    predictions = generate_predictions(features, model_name)
    
    # Find dominant prediction
    dominant_prediction = max(predictions, key=lambda x: x.probability)
    confidence = dominant_prediction.confidence
    
    return ClusterPrediction(
        cluster_id=cluster_id,
        timestamp=datetime.now(),
        predictions=predictions,
        dominant_prediction=dominant_prediction.name,
        confidence=confidence,
        model_used=model_name,
        features_used=features
    )

def get_best_model() -> str:
    """Get the best performing model based on accuracy"""
    return max(model_performances.keys(), 
              key=lambda x: model_performances[x].accuracy)

# API Endpoints
@app.get("/")
async def root():
    return {"service": "prediction-service", "status": "running", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {
        "status": "UP",
        "service": "prediction-service",
        "timestamp": datetime.now().isoformat(),
        "models_loaded": len(model_performances)
    }

@app.get("/api/v1/models")
async def get_available_models():
    """Get all available prediction models"""
    return {"models": AVAILABLE_MODELS}

@app.get("/api/v1/models/performance")
async def get_model_performances():
    """Get performance metrics for all models"""
    return {"models": model_performances}

@app.get("/api/v1/models/best")
async def get_best_model_info():
    """Get information about the best performing model"""
    best_model = get_best_model()
    best_performance = model_performances[best_model]
    
    return {
        "best_model": best_model,
        "performance": best_performance,
        "recommendation": f"Use {best_model} for optimal prediction accuracy"
    }

@app.get("/api/v1/models/compare")
async def compare_models():
    """Compare all models across different metrics"""
    metrics_comparison = {}
    
    for metric in ["accuracy", "precision", "recall", "f1_score", "auc_roc"]:
        metrics_comparison[metric] = {
            model.name: getattr(model, metric) 
            for model in model_performances.values()
        }
    
    best_model = get_best_model()
    best_metrics = {
        metric: getattr(model_performances[best_model], metric)
        for metric in ["accuracy", "precision", "recall", "f1_score", "auc_roc"]
    }
    
    # Generate recommendation
    if best_metrics["accuracy"] > 0.92:
        recommendation = f"Excellent performance! {best_model} shows outstanding accuracy."
    elif best_metrics["accuracy"] > 0.88:
        recommendation = f"Good performance! {best_model} provides reliable predictions."
    else:
        recommendation = f"Moderate performance. Consider retraining {best_model} with more data."
    
    return ModelComparison(
        models=AVAILABLE_MODELS,
        metrics_comparison=metrics_comparison,
        best_model=best_model,
        best_model_metrics=best_metrics,
        recommendation=recommendation
    )

@app.get("/api/v1/clusters")
async def get_all_clusters():
    """Get all cluster IDs with predictions"""
    return {"clusters": list(cluster_predictions.keys())}

@app.get("/api/v1/clusters/{cluster_id}/predict")
async def predict_cluster(
    cluster_id: int, 
    model: Optional[str] = None,
    force_new: bool = False
):
    """Get prediction for a specific cluster"""
    if model and model not in AVAILABLE_MODELS:
        raise HTTPException(status_code=400, detail=f"Model {model} not available")
    
    # Check if we have recent predictions
    if (cluster_id in cluster_predictions and 
        cluster_predictions[cluster_id] and 
        not force_new):
        
        latest_prediction = cluster_predictions[cluster_id][-1]
        # Return if prediction is less than 5 minutes old
        if (datetime.now() - latest_prediction.timestamp).seconds < 300:
            return latest_prediction
    
    # Generate new prediction
    prediction = generate_cluster_prediction(cluster_id, model)
    cluster_predictions[cluster_id].append(prediction)
    prediction_history[cluster_id].append(prediction)
    
    # Keep only last 50 predictions per cluster
    if len(cluster_predictions[cluster_id]) > 50:
        cluster_predictions[cluster_id] = cluster_predictions[cluster_id][-50:]
    
    return prediction

@app.get("/api/v1/predictions/batch")
async def batch_predict(cluster_ids: List[int], model: Optional[str] = None):
    """Get predictions for multiple clusters"""
    results = []
    
    for cluster_id in cluster_ids:
        try:
            prediction = await predict_cluster(cluster_id, model)
            results.append(prediction)
        except Exception as e:
            results.append({"cluster_id": cluster_id, "error": str(e)})
    
    return {"predictions": results}

@app.get("/api/v1/predictions/realtime")
async def get_realtime_predictions(limit: int = 5):
    """Get real-time predictions for dashboard"""
    cluster_ids = [77, 78, 79, 80, 81, 82, 83, 84, 85]
    realtime_predictions = []
    
    for cluster_id in cluster_ids[:limit]:
        # Generate new prediction
        prediction = generate_cluster_prediction(cluster_id)
        cluster_predictions[cluster_id].append(prediction)
        realtime_predictions.append(prediction)
    
    return {
        "predictions": realtime_predictions,
        "timestamp": datetime.now(),
        "best_model": get_best_model()
    }

@app.get("/api/v1/clusters/{cluster_id}/history")
async def get_prediction_history(cluster_id: int, limit: int = 20):
    """Get prediction history for a cluster"""
    if cluster_id not in prediction_history:
        raise HTTPException(status_code=404, detail=f"No history for cluster {cluster_id}")
    
    history = prediction_history[cluster_id][-limit:]
    
    # Calculate trends
    accuracy_trend = [p.confidence for p in history]
    confidence_trend = [p.confidence for p in history]
    
    return PredictionHistory(
        cluster_id=cluster_id,
        predictions=history,
        accuracy_trend=accuracy_trend,
        confidence_trend=confidence_trend
    )

@app.get("/api/v1/predictions/summary")
async def get_prediction_summary():
    """Get overall prediction summary"""
    total_predictions = sum(len(predictions) for predictions in cluster_predictions.values())
    
    # Count dominant predictions
    dominant_counts = defaultdict(int)
    total_confidence = 0
    confidence_count = 0
    
    for predictions in cluster_predictions.values():
        for pred in predictions:
            dominant_counts[pred.dominant_prediction] += 1
            total_confidence += pred.confidence
            confidence_count += 1
    
    avg_confidence = total_confidence / confidence_count if confidence_count > 0 else 0
    
    return {
        "total_predictions": total_predictions,
        "clusters_with_predictions": len(cluster_predictions),
        "dominant_predictions": dict(dominant_counts),
        "average_confidence": avg_confidence,
        "best_model": get_best_model(),
        "model_performances": {name: perf.accuracy for name, perf in model_performances.items()},
        "last_updated": datetime.now()
    }

@app.post("/api/v1/models/{model_name}/retrain")
async def retrain_model(model_name: str):
    """Simulate model retraining"""
    if model_name not in AVAILABLE_MODELS:
        raise HTTPException(status_code=404, detail=f"Model {model_name} not found")
    
    # Simulate retraining by improving performance slightly
    current_perf = model_performances[model_name]
    improvement = random.uniform(0.01, 0.03)
    
    model_performances[model_name] = ModelPerformance(
        model_name=model_name,
        accuracy=min(0.99, current_perf.accuracy + improvement),
        precision=min(0.99, current_perf.precision + improvement * 0.8),
        recall=min(0.99, current_perf.recall + improvement * 0.9),
        f1_score=min(0.99, current_perf.f1_score + improvement * 0.85),
        auc_roc=min(0.99, current_perf.auc_roc + improvement * 0.7),
        training_samples=current_perf.training_samples + random.randint(1000, 5000),
        last_updated=datetime.now()
    )
    
    return {
        "message": f"Model {model_name} retrained successfully",
        "new_performance": model_performances[model_name],
        "improvement": improvement
    }

# Initialize on startup
@app.on_event("startup")
async def startup_event():
    initialize_models()
    print("ðŸ¤– Prediction service initialized with models:", AVAILABLE_MODELS)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)

