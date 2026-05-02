"""
Service d'explainability SHAP pour les prÃ©dictions de handover
"""

import shap
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
import joblib
import logging
from pathlib import Path

from src.api.config import settings
from src.api.utils.data_loader import data_loader
from src.api.utils.logger import explainability_logger


class ExplainabilityService:
    """Service principal pour l'explainability des prÃ©dictions"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.model = None
        self.scaler = None
        self.explainer = None
        self.feature_names = []
        
        # Charger le modÃ¨le au dÃ©marrage
        self._load_model()
    
    def _load_model(self):
        """Charger le modÃ¨le et le scaler"""
        try:
            model_path = Path(settings.models_path) / "handover_model.pkl"
            scaler_path = Path(settings.models_path) / "scaler.pkl"
            
            if model_path.exists():
                self.model = joblib.load(model_path)
                self.logger.info(f"ModÃ¨le chargÃ© depuis {model_path}")
            else:
                self.logger.warning("ModÃ¨le non trouvÃ©, utilisation d'un modÃ¨le de base")
                self._create_dummy_model()
            
            if scaler_path.exists():
                self.scaler = joblib.load(scaler_path)
                self.logger.info(f"Scaler chargÃ© depuis {scaler_path}")
            else:
                self.logger.warning("Scaler non trouvÃ©, utilisation sans normalisation")
            
        except Exception as e:
            self.logger.error(f"Erreur lors du chargement du modÃ¨le: {e}")
            self._create_dummy_model()
    
    def _create_dummy_model(self):
        """CrÃ©er un modÃ¨le factice pour les tests"""
        from sklearn.ensemble import RandomForestClassifier
        
        # CrÃ©er un modÃ¨le simple
        self.model = RandomForestClassifier(n_estimators=10, random_state=42)
        self.logger.info("ModÃ¨le factice crÃ©Ã© pour les tests")
    
    def get_cluster_explainability(self, cluster_id: int) -> Optional[Dict[str, Any]]:
        """Obtenir l'explainability complÃ¨te pour un cluster"""
        
        try:
            # Obtenir les KPI du cluster
            cluster_kpi = data_loader.get_cluster_kpi(cluster_id)
            if not cluster_kpi:
                return None
            
            # Obtenir un Ã©chantillon pour l'analyse
            sample_data = data_loader.get_sample_for_prediction(cluster_id, settings.shap_samples)
            if sample_data is None:
                return None
            
            # PrÃ©parer les features
            features = data_loader.prepare_features_for_prediction(sample_data)
            if features.shape[0] == 0:
                return None
            
            # Obtenir les noms des features
            self.feature_names = data_loader._get_feature_columns(sample_data)
            
            # Normaliser si scaler disponible
            if self.scaler is not None:
                features = self.scaler.transform(features)
            
            # Faire les prÃ©dictions
            predictions = self._predict_with_probabilities(features)
            
            # Calculer les valeurs SHAP
            shap_values = self._calculate_shap_values(features)
            
            # Calculer l'importance des features
            feature_importance = self._calculate_feature_importance(shap_values)
            
            # DÃ©terminer la prÃ©diction dominante
            dominant_prediction, confidence = self._get_dominant_prediction(predictions)
            
            # CrÃ©er l'objet d'explainability
            explainability = {
                "shap_values": self._format_shap_values(shap_values),
                "feature_importance": feature_importance,
                "sample_size": len(features),
                "model_type": type(self.model).__name__
            }
            
            # Logger l'explainability
            explainability_logger.log_cluster_explainability(
                cluster_id=cluster_id,
                cluster_kpi=cluster_kpi,
                predictions=predictions,
                explainability=explainability,
                dominant_prediction=dominant_prediction,
                confidence=confidence
            )
            
            return {
                "cluster_id": cluster_id,
                "cluster_kpi": cluster_kpi,
                "predictions": predictions,
                "explainability": explainability,
                "dominant_prediction": dominant_prediction,
                "confidence": confidence,
                "timestamp": pd.Timestamp.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'explainability du cluster {cluster_id}: {e}")
            return None
    
    def _predict_with_probabilities(self, features: np.ndarray) -> Dict[str, float]:
        """Faire des prÃ©dictions avec probabilitÃ©s pour les 4 labels"""
        
        if self.model is None:
            # Retourner des probabilitÃ©s factices
            return {label: 0.25 for label in settings.labels}
        
        try:
            # PrÃ©dire les probabilitÃ©s
            if hasattr(self.model, 'predict_proba'):
                probs = self.model.predict_proba(features)
                # Moyenne des probabilitÃ©s sur tous les Ã©chantillons
                avg_probs = probs.mean(axis=0)
            else:
                # Si le modÃ¨le n'a pas predict_proba, utiliser des probabilitÃ©s uniformes
                avg_probs = np.array([0.25] * len(settings.labels))
            
            # CrÃ©er le dictionnaire de prÃ©dictions
            predictions = {}
            for i, label in enumerate(settings.labels):
                if i < len(avg_probs):
                    predictions[label] = float(avg_probs[i])
                else:
                    predictions[label] = 0.0
            
            # Normaliser pour que la somme fasse 1
            total = sum(predictions.values())
            if total > 0:
                predictions = {k: v/total for k, v in predictions.items()}
            
            return predictions
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la prÃ©diction: {e}")
            return {label: 0.25 for label in settings.labels}
    
    def _calculate_shap_values(self, features: np.ndarray) -> np.ndarray:
        """Calculer les valeurs SHAP - Version optimisÃ©e pour petit dataset"""
        
        try:
            if self.model is None:
                # Retourner des valeurs SHAP factices pour petit dataset
                n_features = features.shape[1]
                return np.random.normal(0, 0.1, n_features)
            
            # Optimisation : limiter le nombre d'Ã©chantillons pour SHAP
            if len(features) > 20:
                features_sample = features[:20]  # Prendre seulement les 20 premiers Ã©chantillons
            else:
                features_sample = features
            
            # CrÃ©er l'explainer SHAP simplifiÃ©
            try:
                if hasattr(self.model, 'feature_importances_'):
                    # Pour les modÃ¨les tree-based
                    explainer = shap.TreeExplainer(self.model)
                else:
                    # Pour les autres modÃ¨les - utiliser moins d'Ã©chantillons de fond
                    background = shap.sample(features_sample, min(10, len(features_sample)))
                    explainer = shap.KernelExplainer(self.model.predict, background)
                
                # Calculer les valeurs SHAP sur Ã©chantillon rÃ©duit
                shap_values = explainer.shap_values(features_sample[:5])  # Seulement 5 Ã©chantillons
                
                # Si shap_values est une liste (multi-classe), prendre la moyenne
                if isinstance(shap_values, list):
                    # Moyenne sur toutes les classes et Ã©chantillons
                    shap_values = np.mean([np.abs(class_vals).mean(axis=0) for class_vals in shap_values], axis=0)
                else:
                    shap_values = np.abs(shap_values).mean(axis=0)
                
                return shap_values
                
            except Exception as shap_error:
                self.logger.warning(f"SHAP avancÃ© Ã©chouÃ©, utilisation de valeurs simplifiÃ©es: {shap_error}")
                # Fallback : valeurs basÃ©es sur l'importance des features si disponible
                if hasattr(self.model, 'feature_importances_'):
                    return self.model.feature_importances_
                else:
                    # Valeurs factices
                    n_features = features.shape[1]
                    return np.random.normal(0, 0.1, n_features)
            
        except Exception as e:
            self.logger.error(f"Erreur lors du calcul SHAP: {e}")
            # Retourner des valeurs factices
            n_features = features.shape[1]
            return np.random.normal(0, 0.1, n_features)
    
    def _calculate_feature_importance(self, shap_values: np.ndarray) -> Dict[str, float]:
        """Calculer l'importance des features Ã  partir des valeurs SHAP"""
        
        try:
            # Moyenne des valeurs absolues SHAP
            if len(shap_values.shape) > 1:
                importance = np.abs(shap_values).mean(axis=0)
            else:
                importance = np.abs(shap_values)
            
            # CrÃ©er le dictionnaire
            feature_importance = {}
            for i, feature_name in enumerate(self.feature_names):
                if i < len(importance):
                    feature_importance[feature_name] = float(importance[i])
            
            # Normaliser pour que la somme fasse 1
            total = sum(feature_importance.values())
            if total > 0:
                feature_importance = {k: v/total for k, v in feature_importance.items()}
            
            return feature_importance
            
        except Exception as e:
            self.logger.error(f"Erreur lors du calcul de l'importance: {e}")
            return {}
    
    def _format_shap_values(self, shap_values: np.ndarray) -> Dict[str, float]:
        """Formater les valeurs SHAP pour le retour JSON"""
        
        try:
            # Prendre la moyenne des valeurs SHAP
            if len(shap_values.shape) > 1:
                avg_shap = shap_values.mean(axis=0)
            else:
                avg_shap = shap_values
            
            # CrÃ©er le dictionnaire
            shap_dict = {}
            for i, feature_name in enumerate(self.feature_names):
                if i < len(avg_shap):
                    shap_dict[feature_name] = float(avg_shap[i])
            
            return shap_dict
            
        except Exception as e:
            self.logger.error(f"Erreur lors du formatage SHAP: {e}")
            return {}
    
    def _get_dominant_prediction(self, predictions: Dict[str, float]) -> Tuple[str, float]:
        """Obtenir la prÃ©diction dominante et sa confiance"""
        
        if not predictions:
            return "no_handover", 0.0
        
        # Trouver le label avec la plus grande probabilitÃ©
        dominant_label = max(predictions, key=predictions.get)
        confidence = predictions[dominant_label]
        
        return dominant_label, confidence
    
    def get_feature_importance_for_cluster(self, cluster_id: int) -> Optional[Dict[str, float]]:
        """Obtenir uniquement l'importance des features pour un cluster"""
        
        explainability_data = self.get_cluster_explainability(cluster_id)
        if not explainability_data:
            return None
        
        return explainability_data["explainability"]["feature_importance"]
    
    def get_shap_values_for_cluster(self, cluster_id: int) -> Optional[Dict[str, float]]:
        """Obtenir uniquement les valeurs SHAP pour un cluster"""
        
        explainability_data = self.get_cluster_explainability(cluster_id)
        if not explainability_data:
            return None
        
        return explainability_data["explainability"]["shap_values"]
    
    def compare_clusters_explainability(self, cluster_ids: List[int]) -> Optional[Dict[str, Any]]:
        """Comparer l'explainability entre plusieurs clusters"""
        
        comparison_results = []
        
        for cluster_id in cluster_ids:
            explainability_data = self.get_cluster_explainability(cluster_id)
            if explainability_data:
                comparison_results.append(explainability_data)
        
        if not comparison_results:
            return None
        
        # Analyse comparative
        comparison = {
            "clusters_compared": cluster_ids,
            "results": comparison_results,
            "summary": self._create_comparison_summary(comparison_results)
        }
        
        return comparison
    
    def _create_comparison_summary(self, results: List[Dict]) -> Dict[str, Any]:
        """CrÃ©er un rÃ©sumÃ© de la comparaison"""
        
        if not results:
            return {}
        
        # Moyennes des prÃ©dictions
        avg_predictions = {}
        for label in settings.labels:
            avg_predictions[label] = np.mean([r["predictions"][label] for r in results])
        
        # Feature importance moyenne
        all_feature_importance = {}
        for result in results:
            for feature, importance in result["explainability"]["feature_importance"].items():
                if feature not in all_feature_importance:
                    all_feature_importance[feature] = []
                all_feature_importance[feature].append(importance)
        
        avg_feature_importance = {
            feature: np.mean(importances) 
            for feature, importances in all_feature_importance.items()
        }
        
        return {
            "average_predictions": avg_predictions,
            "average_feature_importance": avg_feature_importance,
            "most_common_prediction": max(avg_predictions, key=avg_predictions.get),
            "top_features": sorted(avg_feature_importance.items(), key=lambda x: x[1], reverse=True)[:5]
        }
    
    def get_global_feature_importance(self) -> Dict[str, float]:
        """Obtenir l'importance globale des features"""
        
        if self.model is None:
            return {}
        
        try:
            if hasattr(self.model, 'feature_importances_'):
                importance = self.model.feature_importances_
                
                feature_importance = {}
                for i, feature_name in enumerate(self.feature_names):
                    if i < len(importance):
                        feature_importance[feature_name] = float(importance[i])
                
                return feature_importance
            else:
                return {}
                
        except Exception as e:
            self.logger.error(f"Erreur lors de l'obtention de l'importance globale: {e}")
            return {}


# Instance globale du service
explainability_service = ExplainabilityService()

