"""
Application principale FastAPI pour le backend Explainability DoNext 5G
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.config import settings
from src.api.services.logging_service import dynamic_logging_service
from src.api import explainability, predictions
from src.api.utils.logger import explainability_logger


# Configuration du logging standard
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestion du cycle de vie de l'application"""
    
    # DÃ©marrage
    logger.info("DÃ©marrage du backend Explainability DoNext 5G...")
    
    # PrÃ©charger les donnÃ©es
    from src.api.utils.data_loader import data_loader
    data_loader.preload_top_clusters(20)
    
    # DÃ©marrer les logs dynamiques si activÃ©
    if settings.dynamic_logs_enabled:
        await dynamic_logging_service.start_dynamic_logging()
        logger.info("Logs dynamiques dÃ©marrÃ©s")
    else:
        logger.info("Logs dynamiques dÃ©sactivÃ©s")
    
    explainability_logger.log_system_event(
        "backend_started",
        "Backend Explainability DoNext 5G dÃ©marrÃ© avec succÃ¨s",
        version="1.0.0",
        dynamic_logs_enabled=settings.dynamic_logs_enabled,
        cluster_log_interval=settings.cluster_log_interval
    )
    
    yield
    
    # ArrÃªt
    logger.info("ArrÃªt du backend Explainability DoNext 5G...")
    
    # ArrÃªter les logs dynamiques
    if dynamic_logging_service.is_logging:
        await dynamic_logging_service.stop_dynamic_logging()
        logger.info("Logs dynamiques arrÃªtÃ©s")
    
    explainability_logger.log_system_event(
        "backend_stopped",
        "Backend Explainability DoNext 5G arrÃªtÃ©"
    )
    
    logger.info("Backend Explainability DoNext 5G arrÃªtÃ©")


# CrÃ©er l'application FastAPI
app = FastAPI(
    title="DoNext 5G Explainability API",
    description="Microservice d'explainability pour les prÃ©dictions de handover 5G avec logs dynamiques par cluster",
    version="1.0.0",
    lifespan=lifespan
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Ã€ configurer pour la production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclure les routers API
app.include_router(explainability.router)
app.include_router(predictions.router)


@app.get("/")
async def root():
    """
    Endpoint racine pour vÃ©rifier que l'API fonctionne
    """
    return {
        "message": "DoNext 5G Explainability API",
        "version": "1.0.0",
        "status": "running",
        "dynamic_logs": dynamic_logging_service.is_logging,
        "docs": "/docs",
        "redoc": "/redoc"
    }


@app.get("/health")
async def health_check():
    """
    VÃ©rification de santÃ© de l'application
    """
    try:
        from src.api.utils.data_loader import data_loader
        
        clusters = data_loader.get_all_clusters()
        
        health = {
            "status": "healthy",
            "backend": "running",
            "dynamic_logs": dynamic_logging_service.is_logging,
            "data_access": len(clusters) > 0,
            "total_clusters": len(clusters),
            "current_cluster": dynamic_logging_service.get_current_cluster()
        }
        
        return health
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }


@app.get("/info")
async def get_info():
    """
    Informations sur l'application et la configuration
    """
    return {
        "application": {
            "name": "DoNext 5G Explainability Backend",
            "version": "1.0.0",
            "description": "Microservice d'explainability pour les prÃ©dictions de handover 5G avec logs dynamiques par cluster"
        },
        "configuration": {
            "host": settings.host,
            "port": settings.port,
            "debug": settings.debug,
            "log_level": settings.log_level,
            "dynamic_logs_enabled": settings.dynamic_logs_enabled,
            "cluster_log_interval": settings.cluster_log_interval,
            "shap_samples": settings.shap_samples
        },
        "features": {
            "explainability": settings.explainability_enabled,
            "dynamic_logs": settings.dynamic_logs_enabled,
            "shap_analysis": True,
            "4_labels_predictions": True,
            "real_time_logging": True
        },
        "prediction_labels": settings.labels,
        "current_status": dynamic_logging_service.get_logging_status()
    }


@app.get("/status")
async def get_status():
    """
    Obtenir le statut dÃ©taillÃ© du systÃ¨me
    """
    try:
        from src.api.utils.data_loader import data_loader
        
        # Statut des logs dynamiques
        logging_status = dynamic_logging_service.get_logging_status()
        
        # Statistiques des clusters
        clusters = data_loader.get_all_clusters()
        top_clusters = data_loader.get_top_clusters(10)
        
        # Logs rÃ©cents
        recent_logs = dynamic_logging_service.get_recent_dynamic_logs(10)
        
        status = {
            "backend": {
                "status": "running",
                "uptime": "N/A",  # Ã€ implÃ©menter
                "version": "1.0.0"
            },
            "dynamic_logging": logging_status,
            "data": {
                "total_clusters": len(clusters),
                "top_clusters": len(top_clusters),
                "data_accessible": len(clusters) > 0
            },
            "recent_activity": {
                "recent_logs_count": len(recent_logs),
                "last_log_timestamp": recent_logs[0]["timestamp"] if recent_logs else None
            },
            "explainability": {
                "enabled": settings.explainability_enabled,
                "shap_samples": settings.shap_samples,
                "labels": settings.labels
            }
        }
        
        return status
        
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )

