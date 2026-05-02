"""
SystÃ¨me de logging structurÃ© pour l'explainability des clusters
"""

import json
import logging
import structlog
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path

from src.api.config import settings


class ExplainabilityLogger:
    """Logger spÃ©cialisÃ© pour l'explainability des clusters avec logs dynamiques"""
    
    def __init__(self):
        self.setup_logger()
        self.current_cluster_index = 0
        self.clusters_sequence = []
    
    def setup_logger(self):
        """Configuration du logger structurÃ©"""
        
        # CrÃ©er le rÃ©pertoire de logs
        Path(settings.logs_path).mkdir(exist_ok=True)
        
        # Configuration de structlog
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer()
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
        
        self.logger = structlog.get_logger("explainability")
    
    def log_cluster_explainability(self, cluster_id: int, cluster_kpi: Dict[str, float], 
                                  predictions: Dict[str, float], explainability: Dict[str, Any],
                                  dominant_prediction: str, confidence: float):
        """Logger l'explainability complÃ¨te d'un cluster"""
        
        log_entry = {
            "event_type": "cluster_explainability",
            "timestamp": datetime.utcnow().isoformat(),
            "cluster_id": cluster_id,
            "cluster_kpi": cluster_kpi,
            "predictions": predictions,
            "explainability": explainability,
            "dominant_prediction": dominant_prediction,
            "confidence": confidence,
            "labels": settings.labels
        }
        
        self.logger.info("cluster_explainability_update", **log_entry)
        
        # Sauvegarder dans un fichier sÃ©parÃ© pour ce cluster
        self._save_cluster_log(cluster_id, log_entry)
        
        # Sauvegarder dans le fichier de logs dynamiques
        self._save_dynamic_log(log_entry)
    
    def log_prediction_details(self, cluster_id: int, sample_data: Dict[str, float], 
                             prediction_probs: List[float], shap_values: List[float]):
        """Logger les dÃ©tails de prÃ©diction pour un Ã©chantillon"""
        
        log_entry = {
            "event_type": "prediction_details",
            "timestamp": datetime.utcnow().isoformat(),
            "cluster_id": cluster_id,
            "sample_data": sample_data,
            "prediction_probs": prediction_probs,
            "shap_values": shap_values,
            "labels": settings.labels
        }
        
        self.logger.info("prediction_details", **log_entry)
    
    def log_model_explainability(self, cluster_id: int, feature_importance: Dict[str, float],
                                shap_summary: Dict[str, Any]):
        """Logger l'explainabilitÃ© au niveau du modÃ¨le pour un cluster"""
        
        log_entry = {
            "event_type": "model_explainability",
            "timestamp": datetime.utcnow().isoformat(),
            "cluster_id": cluster_id,
            "feature_importance": feature_importance,
            "shap_summary": shap_summary
        }
        
        self.logger.info("model_explainability", **log_entry)
    
    def log_system_event(self, event_type: str, message: str, **kwargs):
        """Logger un Ã©vÃ©nement systÃ¨me"""
        
        system_entry = {
            "event_type": "system_event",
            "timestamp": datetime.utcnow().isoformat(),
            "event": event_type,
            "message": message,
            **kwargs
        }
        
        self.logger.info("system_event", **{k: v for k, v in system_entry.items() if k != "event"})
    
    def _save_cluster_log(self, cluster_id: int, log_entry: Dict[str, Any]):
        """Sauvegarder le log dans un fichier spÃ©cifique au cluster"""
        
        cluster_log_file = Path(settings.logs_path) / f"cluster_{cluster_id}_explainability.jsonl"
        
        with open(cluster_log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, default=str) + "\n")
    
    def _save_dynamic_log(self, log_entry: Dict[str, Any]):
        """Sauvegarder dans le fichier de logs dynamiques"""
        
        dynamic_log_file = Path(settings.logs_path) / "dynamic_explainability.jsonl"
        
        with open(dynamic_log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, default=str) + "\n")
    
    def get_cluster_logs(self, cluster_id: int, limit: int = 100) -> List[Dict]:
        """RÃ©cupÃ©rer les logs d'explainability d'un cluster"""
        
        cluster_log_file = Path(settings.logs_path) / f"cluster_{cluster_id}_explainability.jsonl"
        
        if not cluster_log_file.exists():
            return []
        
        logs = []
        with open(cluster_log_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    logs.append(json.loads(line.strip()))
                    if len(logs) >= limit:
                        break
        
        return logs[-limit:]  # Retourner les plus rÃ©cents
    
    def get_dynamic_logs(self, limit: int = 100) -> List[Dict]:
        """RÃ©cupÃ©rer les logs dynamiques rÃ©cents"""
        
        dynamic_log_file = Path(settings.logs_path) / "dynamic_explainability.jsonl"
        
        if not dynamic_log_file.exists():
            return []
        
        logs = []
        with open(dynamic_log_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    logs.append(json.loads(line.strip()))
        
        # Trier par timestamp et retourner les plus rÃ©cents
        logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return logs[:limit]
    
    def get_latest_cluster_log(self, cluster_id: int) -> Optional[Dict]:
        """RÃ©cupÃ©rer le log le plus rÃ©cent pour un cluster"""
        
        logs = self.get_cluster_logs(cluster_id, limit=1)
        return logs[0] if logs else None
    
    def clear_logs(self):
        """Vider tous les logs"""
        
        # Vider les logs dynamiques
        dynamic_log_file = Path(settings.logs_path) / "dynamic_explainability.jsonl"
        if dynamic_log_file.exists():
            dynamic_log_file.unlink()
        
        # Vider les logs de clusters
        for log_file in Path(settings.logs_path).glob("cluster_*_explainability.jsonl"):
            log_file.unlink()
        
        self.logger.info("logs_cleared", message="Tous les logs d'explainability ont Ã©tÃ© vidÃ©s")


# Instance globale du logger
explainability_logger = ExplainabilityLogger()


