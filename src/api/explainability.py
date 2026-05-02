"""
API endpoints pour l'explainability des clusters
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict
from pydantic import BaseModel

from src.api.services.explainability_service import explainability_service


router = APIRouter(prefix="/api/v1/explainability", tags=["explainability"])


class ClusterKPI(BaseModel):
    """ModÃ¨le pour les KPI de cluster"""
    rsrp: Optional[float] = None
    rsrq: Optional[float] = None
    sinr: Optional[float] = None
    cqi: Optional[float] = None
    tx_power: Optional[float] = None
    velocity: Optional[float] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    n_records: Optional[int] = None
    ho_rate: Optional[float] = None


class Predictions(BaseModel):
    """ModÃ¨le pour les prÃ©dictions des 4 labels"""
    no_handover: float
    intra_freq_handover: float
    inter_freq_handover: float
    inter_rat_handover: float


class ExplainabilityData(BaseModel):
    """ModÃ¨le pour les donnÃ©es d'explainability"""
    shap_values: Dict[str, float]
    feature_importance: Dict[str, float]
    sample_size: int
    model_type: str


class ClusterExplainability(BaseModel):
    """ModÃ¨le complet pour l'explainability d'un cluster"""
    cluster_id: int
    cluster_kpi: ClusterKPI
    predictions: Predictions
    explainability: ExplainabilityData
    dominant_prediction: str
    confidence: float
    timestamp: str


@router.get("/cluster/{cluster_id}", response_model=ClusterExplainability)
async def get_cluster_explainability(cluster_id: int):
    """
    Obtenir l'explainability complÃ¨te d'un cluster spÃ©cifique
    """
    try:
        explainability_data = explainability_service.get_cluster_explainability(cluster_id)
        
        if not explainability_data:
            raise HTTPException(status_code=404, detail=f"Cluster {cluster_id} non trouvÃ© ou erreur d'explainability")
        
        return explainability_data
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'explainability du cluster {cluster_id}: {str(e)}")


@router.get("/cluster/{cluster_id}/predictions", response_model=Predictions)
async def get_cluster_predictions(cluster_id: int):
    """
    Obtenir uniquement les prÃ©dictions d'un cluster
    """
    try:
        explainability_data = explainability_service.get_cluster_explainability(cluster_id)
        
        if not explainability_data:
            raise HTTPException(status_code=404, detail=f"Cluster {cluster_id} non trouvÃ©")
        
        return explainability_data["predictions"]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors des prÃ©dictions du cluster {cluster_id}: {str(e)}")


@router.get("/cluster/{cluster_id}/shap")
async def get_cluster_shap_values(cluster_id: int):
    """
    Obtenir les valeurs SHAP d'un cluster
    """
    try:
        shap_values = explainability_service.get_shap_values_for_cluster(cluster_id)
        
        if not shap_values:
            raise HTTPException(status_code=404, detail=f"Cluster {cluster_id} non trouvÃ© ou pas de valeurs SHAP")
        
        return {
            "cluster_id": cluster_id,
            "shap_values": shap_values,
            "feature_names": list(shap_values.keys())
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la rÃ©cupÃ©ration des SHAP du cluster {cluster_id}: {str(e)}")


@router.get("/cluster/{cluster_id}/feature-importance")
async def get_cluster_feature_importance(cluster_id: int):
    """
    Obtenir l'importance des features pour un cluster
    """
    try:
        feature_importance = explainability_service.get_feature_importance_for_cluster(cluster_id)
        
        if not feature_importance:
            raise HTTPException(status_code=404, detail=f"Cluster {cluster_id} non trouvÃ©")
        
        return {
            "cluster_id": cluster_id,
            "feature_importance": feature_importance,
            "top_features": sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)[:10]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la rÃ©cupÃ©ration de l'importance des features: {str(e)}")


@router.post("/compare")
async def compare_clusters(cluster_ids: List[int]):
    """
    Comparer l'explainability entre plusieurs clusters
    """
    try:
        if len(cluster_ids) < 2:
            raise HTTPException(status_code=400, detail="Au moins 2 clusters sont nÃ©cessaires pour la comparaison")
        
        if len(cluster_ids) > 10:
            raise HTTPException(status_code=400, detail="Maximum 10 clusters pour la comparaison")
        
        comparison = explainability_service.compare_clusters_explainability(cluster_ids)
        
        if not comparison:
            raise HTTPException(status_code=404, detail="Impossible de comparer les clusters spÃ©cifiÃ©s")
        
        return comparison
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la comparaison des clusters: {str(e)}")


@router.get("/global/feature-importance")
async def get_global_feature_importance():
    """
    Obtenir l'importance globale des features du modÃ¨le
    """
    try:
        feature_importance = explainability_service.get_global_feature_importance()
        
        return {
            "feature_importance": feature_importance,
            "top_features": sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)[:20]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la rÃ©cupÃ©ration de l'importance globale: {str(e)}")


@router.get("/clusters/top-explainability")
async def get_top_clusters_explainability(
    limit: int = Query(10, ge=1, le=50)
):
    """
    Obtenir l'explainability des plus grands clusters
    """
    try:
        from src.api.utils.data_loader import data_loader
        
        top_clusters = data_loader.get_top_clusters(limit)
        results = []
        
        for cluster_id, _ in top_clusters:
            explainability_data = explainability_service.get_cluster_explainability(cluster_id)
            if explainability_data:
                results.append(explainability_data)
        
        return {
            "total_clusters": len(results),
            "clusters": results
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la rÃ©cupÃ©ration des top clusters: {str(e)}")


@router.get("/clusters/by-prediction/{prediction_type}")
async def get_clusters_by_prediction(
    prediction_type: str,
    limit: int = Query(20, ge=1, le=100)
):
    """
    Obtenir les clusters classÃ©s par type de prÃ©diction dominante
    """
    try:
        from src.api.config import settings
        
        if prediction_type not in settings.labels:
            raise HTTPException(status_code=400, detail=f"Type de prÃ©diction invalide. Valeurs possibles: {settings.labels}")
        
        from src.api.utils.data_loader import data_loader
        
        top_clusters = data_loader.get_top_clusters(100)  # Plus de clusters pour filtrer
        results = []
        
        for cluster_id, _ in top_clusters:
            explainability_data = explainability_service.get_cluster_explainability(cluster_id)
            if explainability_data and explainability_data["dominant_prediction"] == prediction_type:
                results.append(explainability_data)
            
            if len(results) >= limit:
                break
        
        return {
            "prediction_type": prediction_type,
            "total_clusters": len(results),
            "clusters": results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la rÃ©cupÃ©ration des clusters par prÃ©diction: {str(e)}")


@router.get("/summary")
async def get_explainability_summary():
    """
    Obtenir un rÃ©sumÃ© de l'explainability sur tous les clusters
    """
    try:
        from src.api.utils.data_loader import data_loader
        from src.api.config import settings
        
        # Statistiques de base
        all_clusters = data_loader.get_all_clusters()
        top_clusters = data_loader.get_top_clusters(20)
        
        # Analyser les prÃ©dictions
        prediction_counts = {label: 0 for label in settings.labels}
        confidence_sum = 0
        analyzed_count = 0
        
        for cluster_id, _ in top_clusters:
            explainability_data = explainability_service.get_cluster_explainability(cluster_id)
            if explainability_data:
                dominant_pred = explainability_data["dominant_prediction"]
                confidence = explainability_data["confidence"]
                
                prediction_counts[dominant_pred] += 1
                confidence_sum += confidence
                analyzed_count += 1
        
        avg_confidence = confidence_sum / analyzed_count if analyzed_count > 0 else 0
        
        # Feature importance globale
        global_importance = explainability_service.get_global_feature_importance()
        
        summary = {
            "total_clusters": len(all_clusters),
            "analyzed_clusters": analyzed_count,
            "average_confidence": avg_confidence,
            "prediction_distribution": prediction_counts,
            "most_common_prediction": max(prediction_counts, key=prediction_counts.get) if prediction_counts else None,
            "global_feature_importance": global_importance,
            "top_features": sorted(global_importance.items(), key=lambda x: x[1], reverse=True)[:10] if global_importance else []
        }
        
        return summary
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors du rÃ©sumÃ© de l'explainability: {str(e)}")


@router.post("/cluster/{cluster_id}/force-explain")
async def force_cluster_explainability(cluster_id: int):
    """
    Forcer le recalcul de l'explainability d'un cluster
    """
    try:
        # Vider le cache pour ce cluster
        from src.api.utils.data_loader import data_loader
        
        if cluster_id in data_loader._cluster_cache:
            del data_loader._cluster_cache[cluster_id]
        if cluster_id in data_loader._kpi_cache:
            del data_loader._kpi_cache[cluster_id]
        
        # Recalculer l'explainability
        explainability_data = explainability_service.get_cluster_explainability(cluster_id)
        
        if not explainability_data:
            raise HTTPException(status_code=404, detail=f"Cluster {cluster_id} non trouvÃ©")
        
        return {
            "message": f"Explainability du cluster {cluster_id} forcÃ©e avec succÃ¨s",
            "cluster_id": cluster_id,
            "dominant_prediction": explainability_data["dominant_prediction"],
            "confidence": explainability_data["confidence"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors du forÃ§age de l'explainability: {str(e)}")

