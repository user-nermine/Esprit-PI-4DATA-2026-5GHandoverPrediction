"""
API endpoints pour les prÃ©dictions et logs dynamiques
"""

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

from src.api.services.explainability_service import explainability_service
from src.api.services.logging_service import dynamic_logging_service
from src.api.utils.logger import explainability_logger


router = APIRouter(prefix="/api/v1", tags=["predictions", "logs"])


class LogEntry(BaseModel):
    """ModÃ¨le pour une entrÃ©e de log dynamique"""
    timestamp: str
    cluster_id: int
    cluster_kpi: Dict[str, float]
    predictions: Dict[str, float]
    explainability: Dict[str, Any]
    dominant_prediction: str
    confidence: float


@router.get("/logs/dynamic", response_model=List[LogEntry])
async def get_dynamic_logs(
    limit: int = Query(50, ge=1, le=200),
    cluster_id: Optional[int] = Query(None)
):
    """
    Obtenir les logs dynamiques rÃ©cents
    """
    try:
        if cluster_id:
            # Logs spÃ©cifiques Ã  un cluster
            logs = explainability_logger.get_cluster_logs(cluster_id, limit)
        else:
            # Logs dynamiques gÃ©nÃ©raux
            logs = dynamic_logging_service.get_recent_dynamic_logs(limit)
        
        return logs
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la rÃ©cupÃ©ration des logs: {str(e)}")


@router.get("/logs/cluster/{cluster_id}")
async def get_cluster_logs(
    cluster_id: int,
    limit: int = Query(100, ge=1, le=500)
):
    """
    Obtenir tous les logs d'un cluster spÃ©cifique
    """
    try:
        logs = explainability_logger.get_cluster_logs(cluster_id, limit)
        
        return {
            "cluster_id": cluster_id,
            "logs": logs,
            "total": len(logs)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la rÃ©cupÃ©ration des logs du cluster {cluster_id}: {str(e)}")


@router.post("/logs/dynamic/start")
async def start_dynamic_logging(background_tasks: BackgroundTasks):
    """
    DÃ©marrer les logs dynamiques des clusters
    """
    try:
        # DÃ©marrer en arriÃ¨re-plan
        background_tasks.add_task(dynamic_logging_service.start_dynamic_logging)
        
        return {
            "message": "Logs dynamiques dÃ©marrÃ©s",
            "status": "starting"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors du dÃ©marrage des logs dynamiques: {str(e)}")


@router.post("/logs/dynamic/stop")
async def stop_dynamic_logging():
    """
    ArrÃªter les logs dynamiques
    """
    try:
        await dynamic_logging_service.stop_dynamic_logging()
        
        return {
            "message": "Logs dynamiques arrÃªtÃ©s",
            "status": "stopped"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'arrÃªt des logs dynamiques: {str(e)}")


@router.get("/logs/dynamic/status")
async def get_dynamic_logging_status():
    """
    Obtenir le statut des logs dynamiques
    """
    try:
        status = dynamic_logging_service.get_logging_status()
        
        return status
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la rÃ©cupÃ©ration du statut: {str(e)}")


@router.post("/logs/dynamic/force-cluster/{cluster_id}")
async def force_log_cluster(cluster_id: int):
    """
    Forcer le logging immÃ©diat d'un cluster
    """
    try:
        success = dynamic_logging_service.force_log_cluster(cluster_id)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"Cluster {cluster_id} non trouvÃ© ou erreur de logging")
        
        return {
            "message": f"Cluster {cluster_id} forcÃ© loggÃ© avec succÃ¨s",
            "cluster_id": cluster_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors du forÃ§age du logging: {str(e)}")


@router.post("/logs/dynamic/set-sequence")
async def set_cluster_sequence(cluster_ids: List[int]):
    """
    DÃ©finir une sÃ©quence personnalisÃ©e de clusters pour les logs dynamiques
    """
    try:
        if len(cluster_ids) == 0:
            raise HTTPException(status_code=400, detail="La sÃ©quence ne peut pas Ãªtre vide")
        
        if len(cluster_ids) > 100:
            raise HTTPException(status_code=400, detail="Maximum 100 clusters dans la sÃ©quence")
        
        dynamic_logging_service.set_cluster_sequence(cluster_ids)
        
        return {
            "message": f"SÃ©quence de {len(cluster_ids)} clusters dÃ©finie",
            "sequence": cluster_ids
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la dÃ©finition de la sÃ©quence: {str(e)}")


@router.post("/logs/dynamic/jump-to/{cluster_id}")
async def jump_to_cluster(cluster_id: int):
    """
    Sauter Ã  un cluster spÃ©cifique dans la sÃ©quence de logging
    """
    try:
        success = dynamic_logging_service.jump_to_cluster(cluster_id)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"Cluster {cluster_id} pas dans la sÃ©quence actuelle")
        
        return {
            "message": f"Saut au cluster {cluster_id} rÃ©ussi",
            "cluster_id": cluster_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors du saut au cluster: {str(e)}")


@router.get("/logs/dynamic/statistics")
async def get_logging_statistics():
    """
    Obtenir des statistiques sur les logs dynamiques
    """
    try:
        stats = dynamic_logging_service.get_logging_statistics()
        
        return stats
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la rÃ©cupÃ©ration des statistiques: {str(e)}")


@router.get("/predictions/cluster/{cluster_id}")
async def get_cluster_predictions(cluster_id: int):
    """
    Obtenir les prÃ©dictions dÃ©taillÃ©es pour un cluster
    """
    try:
        explainability_data = explainability_service.get_cluster_explainability(cluster_id)
        
        if not explainability_data:
            raise HTTPException(status_code=404, detail=f"Cluster {cluster_id} non trouvÃ©")
        
        return {
            "cluster_id": cluster_id,
            "predictions": explainability_data["predictions"],
            "dominant_prediction": explainability_data["dominant_prediction"],
            "confidence": explainability_data["confidence"],
            "timestamp": explainability_data["timestamp"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors des prÃ©dictions du cluster {cluster_id}: {str(e)}")


@router.get("/predictions/summary")
async def get_predictions_summary():
    """
    Obtenir un rÃ©sumÃ© des prÃ©dictions sur tous les clusters analysÃ©s
    """
    try:
        from src.api.config import settings
        
        # Obtenir les logs dynamiques rÃ©cents
        recent_logs = dynamic_logging_service.get_recent_dynamic_logs(200)
        
        if not recent_logs:
            return {
                "total_predictions": 0,
                "prediction_distribution": {},
                "average_confidence": 0.0,
                "message": "Aucune prÃ©diction rÃ©cente trouvÃ©e"
            }
        
        # Analyser les prÃ©dictions
        prediction_counts = {label: 0 for label in settings.labels}
        confidence_sum = 0.0
        cluster_predictions = {}
        
        for log in recent_logs:
            cluster_id = log.get("cluster_id")
            predictions = log.get("predictions", {})
            confidence = log.get("confidence", 0.0)
            
            # Compter les prÃ©dictions dominantes
            dominant_pred = log.get("dominant_prediction")
            if dominant_pred:
                prediction_counts[dominant_pred] += 1
            
            # Accumuler la confiance
            confidence_sum += confidence
            
            # Regrouper par cluster
            if cluster_id not in cluster_predictions:
                cluster_predictions[cluster_id] = []
            cluster_predictions[cluster_id].append({
                "predictions": predictions,
                "confidence": confidence,
                "timestamp": log.get("timestamp")
            })
        
        avg_confidence = confidence_sum / len(recent_logs)
        
        # Top clusters par nombre de prÃ©dictions
        top_clusters = sorted(
            [(cid, len(preds)) for cid, preds in cluster_predictions.items()],
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        summary = {
            "total_predictions": len(recent_logs),
            "unique_clusters": len(cluster_predictions),
            "prediction_distribution": prediction_counts,
            "average_confidence": avg_confidence,
            "most_common_prediction": max(prediction_counts, key=prediction_counts.get) if prediction_counts else None,
            "top_clusters": [{"cluster_id": cid, "prediction_count": count} for cid, count in top_clusters],
            "labels": settings.labels
        }
        
        return summary
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors du rÃ©sumÃ© des prÃ©dictions: {str(e)}")


@router.get("/predictions/by-confidence")
async def get_predictions_by_confidence(
    min_confidence: float = Query(0.5, ge=0.0, le=1.0),
    max_confidence: float = Query(1.0, ge=0.0, le=1.0),
    limit: int = Query(50, ge=1, le=200)
):
    """
    Obtenir les prÃ©dictions filtrÃ©es par niveau de confiance
    """
    try:
        if min_confidence > max_confidence:
            raise HTTPException(status_code=400, detail="min_confidence doit Ãªtre <= max_confidence")
        
        recent_logs = dynamic_logging_service.get_recent_dynamic_logs(500)
        
        # Filtrer par confiance
        filtered_logs = [
            log for log in recent_logs
            if min_confidence <= log.get("confidence", 0.0) <= max_confidence
        ]
        
        # Limiter les rÃ©sultats
        filtered_logs = filtered_logs[:limit]
        
        return {
            "confidence_range": [min_confidence, max_confidence],
            "total_found": len(filtered_logs),
            "predictions": filtered_logs
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors du filtrage par confiance: {str(e)}")


@router.delete("/logs/clear")
async def clear_all_logs():
    """
    Vider tous les logs d'explainability
    """
    try:
        explainability_logger.clear_logs()
        
        return {
            "message": "Tous les logs d'explainability ont Ã©tÃ© vidÃ©s",
            "timestamp": "now"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors du vidage des logs: {str(e)}")


@router.get("/health")
async def health_check():
    """
    VÃ©rification de santÃ© du service de prÃ©dictions
    """
    try:
        from src.api.utils.data_loader import data_loader
        
        clusters = data_loader.get_all_clusters()
        
        health = {
            "status": "healthy",
            "data_access": len(clusters) > 0,
            "total_clusters": len(clusters),
            "dynamic_logging": dynamic_logging_service.get_logging_status(),
            "explainability_service": "running"
        }
        
        return health
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

