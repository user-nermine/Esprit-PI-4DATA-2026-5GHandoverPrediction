"""
Service de logging dynamique pour parcourir les clusters avec explainability
"""

import asyncio
import logging
from typing import Dict, List, Optional

from src.api.config import settings
from src.api.services.explainability_service import explainability_service
from src.api.utils.data_loader import data_loader
from src.api.utils.logger import explainability_logger


class DynamicLoggingService:
    """Service pour les logs dynamiques qui parcourent les clusters"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.is_logging = False
        self.logging_task = None
        self.current_cluster_index = 0
        self.clusters_sequence = []
        self.total_logged = 0
    
    async def start_dynamic_logging(self):
        """DÃ©marrer les logs dynamiques des clusters"""
        
        if self.is_logging:
            self.logger.warning("Les logs dynamiques sont dÃ©jÃ  en cours")
            return
        
        self.is_logging = True
        self.logger.info("DÃ©marrage des logs dynamiques des clusters")
        
        # PrÃ©parer la sÃ©quence de clusters
        self.clusters_sequence = data_loader.get_clusters_sequence()
        self.current_cluster_index = 0
        
        # Logger l'Ã©vÃ©nement
        explainability_logger.log_system_event(
            "dynamic_logging_started",
            "Logs dynamiques dÃ©marrÃ©s",
            total_clusters=len(self.clusters_sequence),
            interval_seconds=settings.cluster_log_interval
        )
        
        # DÃ©marrer la tÃ¢che de logging
        self.logging_task = asyncio.create_task(self._logging_loop())
    
    async def stop_dynamic_logging(self):
        """ArrÃªter les logs dynamiques"""
        
        if not self.is_logging:
            return
        
        self.is_logging = False
        
        if self.logging_task:
            self.logging_task.cancel()
            try:
                await self.logging_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Logs dynamiques arrÃªtÃ©s")
        explainability_logger.log_system_event(
            "dynamic_logging_stopped",
            "Logs dynamiques arrÃªtÃ©s",
            total_logged=self.total_logged
        )
    
    async def _logging_loop(self):
        """Boucle principale de logging dynamique"""
        
        while self.is_logging:
            try:
                await self._log_current_cluster()
                await asyncio.sleep(settings.cluster_log_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Erreur dans la boucle de logging: {e}")
                await asyncio.sleep(5)  # Attendre avant de rÃ©essayer
    
    async def _log_current_cluster(self):
        """Logger le cluster actuel"""
        
        if not self.clusters_sequence:
            self.logger.warning("Aucun cluster Ã  logger")
            return
        
        # Obtenir le cluster actuel
        current_cluster_id = self.clusters_sequence[self.current_cluster_index]
        
        try:
            # Obtenir l'explainability du cluster
            explainability_data = explainability_service.get_cluster_explainability(current_cluster_id)
            
            if explainability_data:
                self.logger.info(f"Cluster {current_cluster_id} loggÃ© avec explainability")
                self.total_logged += 1
                
                # Logger les dÃ©tails de la prÃ©diction
                await self._log_prediction_details(current_cluster_id, explainability_data)
            else:
                self.logger.warning(f"Impossible d'obtenir l'explainability pour le cluster {current_cluster_id}")
            
            # Passer au cluster suivant
            self.current_cluster_index = (self.current_cluster_index + 1) % len(self.clusters_sequence)
            
            # Si on a fait un tour complet, logger un Ã©vÃ©nement
            if self.current_cluster_index == 0:
                explainability_logger.log_system_event(
                    "clusters_cycle_completed",
                    "Cycle complet des clusters terminÃ©",
                    clusters_in_cycle=len(self.clusters_sequence),
                    total_logged=self.total_logged
                )
            
        except Exception as e:
            self.logger.error(f"Erreur lors du logging du cluster {current_cluster_id}: {e}")
            # Passer au cluster suivant mÃªme en cas d'erreur
            self.current_cluster_index = (self.current_cluster_index + 1) % len(self.clusters_sequence)
    
    async def _log_prediction_details(self, cluster_id: int, explainability_data: Dict):
        """Logger les dÃ©tails de prÃ©diction pour un cluster"""
        
        try:
            # Obtenir un Ã©chantillon pour les dÃ©tails
            sample_data = data_loader.get_sample_for_prediction(cluster_id, 10)
            if sample_data is None:
                return
            
            # PrÃ©parer les features
            features = data_loader.prepare_features_for_prediction(sample_data)
            
            # Obtenir les prÃ©dictions et SHAP pour chaque Ã©chantillon
            for i in range(min(len(features), 5)):  # Limiter Ã  5 Ã©chantillons
                sample_features = features[i:i+1]
                sample_dict = sample_data.iloc[i].to_dict()
                
                # PrÃ©dictions
                predictions = explainability_service._predict_with_probabilities(sample_features)
                
                # SHAP values (simplifiÃ©)
                shap_values = list(explainability_data["explainability"]["shap_values"].values())
                
                # Logger les dÃ©tails
                explainability_logger.log_prediction_details(
                    cluster_id=cluster_id,
                    sample_data=sample_dict,
                    prediction_probs=list(predictions.values()),
                    shap_values=shap_values
                )
        
        except Exception as e:
            self.logger.error(f"Erreur lors du logging des dÃ©tails de prÃ©diction: {e}")
    
    def get_current_cluster(self) -> Optional[int]:
        """Obtenir le cluster actuel"""
        
        if not self.clusters_sequence:
            return None
        
        return self.clusters_sequence[self.current_cluster_index]
    
    def get_logging_status(self) -> Dict:
        """Obtenir le statut du logging dynamique"""
        
        return {
            "is_logging": self.is_logging,
            "current_cluster": self.get_current_cluster(),
            "current_index": self.current_cluster_index,
            "total_clusters": len(self.clusters_sequence),
            "total_logged": self.total_logged,
            "interval_seconds": settings.cluster_log_interval,
            "next_cluster_in": settings.cluster_log_interval if self.is_logging else None
        }
    
    def get_recent_dynamic_logs(self, limit: int = 50) -> List[Dict]:
        """Obtenir les logs dynamiques rÃ©cents"""
        
        return explainability_logger.get_dynamic_logs(limit)
    
    def force_log_cluster(self, cluster_id: int) -> bool:
        """Forcer le logging d'un cluster spÃ©cifique"""
        
        try:
            explainability_data = explainability_service.get_cluster_explainability(cluster_id)
            
            if explainability_data:
                self.logger.info(f"Cluster {cluster_id} forcÃ© loggÃ©")
                self.total_logged += 1
                
                # Logger l'Ã©vÃ©nement
                explainability_logger.log_system_event(
                    "cluster_force_logged",
                    f"Cluster {cluster_id} forcÃ© loggÃ©",
                    cluster_id=cluster_id
                )
                
                return True
            else:
                return False
                
        except Exception as e:
            self.logger.error(f"Erreur lors du forÃ§age du logging du cluster {cluster_id}: {e}")
            return False
    
    def set_cluster_sequence(self, cluster_ids: List[int]):
        """DÃ©finir une sÃ©quence personnalisÃ©e de clusters"""
        
        # VÃ©rifier que les clusters existent
        all_clusters = set(data_loader.get_all_clusters())
        valid_clusters = [c for c in cluster_ids if c in all_clusters]
        
        if not valid_clusters:
            self.logger.warning("Aucun cluster valide dans la sÃ©quence")
            return
        
        self.clusters_sequence = valid_clusters
        self.current_cluster_index = 0
        
        self.logger.info(f"SÃ©quence de clusters mise Ã  jour: {len(valid_clusters)} clusters")
        
        explainability_logger.log_system_event(
            "cluster_sequence_updated",
            "SÃ©quence de clusters mise Ã  jour",
            new_sequence=valid_clusters,
            total_clusters=len(valid_clusters)
        )
    
    def jump_to_cluster(self, cluster_id: int) -> bool:
        """Sauter Ã  un cluster spÃ©cifique dans la sÃ©quence"""
        
        if cluster_id not in self.clusters_sequence:
            self.logger.warning(f"Cluster {cluster_id} pas dans la sÃ©quence actuelle")
            return False
        
        self.current_cluster_index = self.clusters_sequence.index(cluster_id)
        
        self.logger.info(f"Saut au cluster {cluster_id} (index {self.current_cluster_index})")
        
        explainability_logger.log_system_event(
            "jump_to_cluster",
            f"Saut au cluster {cluster_id}",
            cluster_id=cluster_id,
            index=self.current_cluster_index
        )
        
        return True
    
    def get_logging_statistics(self) -> Dict:
        """Obtenir des statistiques sur le logging"""
        
        if not self.clusters_sequence:
            return {}
        
        # Obtenir les logs rÃ©cents
        recent_logs = self.get_recent_dynamic_logs(100)
        
        # Analyser les logs
        cluster_counts = {}
        prediction_counts = {}
        
        for log in recent_logs:
            cluster_id = log.get("cluster_id")
            if cluster_id:
                cluster_counts[cluster_id] = cluster_counts.get(cluster_id, 0) + 1
            
            dominant_pred = log.get("dominant_prediction")
            if dominant_pred:
                prediction_counts[dominant_pred] = prediction_counts.get(dominant_pred, 0) + 1
        
        return {
            "total_logged": self.total_logged,
            "clusters_in_sequence": len(self.clusters_sequence),
            "recent_logs_analyzed": len(recent_logs),
            "clusters_logged_recently": len(cluster_counts),
            "prediction_distribution": prediction_counts,
            "most_logged_clusters": sorted(cluster_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        }


# Instance globale du service
dynamic_logging_service = DynamicLoggingService()

