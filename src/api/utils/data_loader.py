"""
Utilitaire de chargement des donnÃ©es pour l'explainability des clusters
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor
import logging

from src.api.config import settings


class ExplainabilityDataLoader:
    """Chargeur de donnÃ©es optimisÃ© pour l'explainability des clusters - Version 100 lignes"""
    
    def __init__(self):
        self.data_path = Path(settings.data_path)
        self.logger = logging.getLogger(__name__)
        
        # Cache pour les donnÃ©es frÃ©quemment accessÃ©es
        self._cluster_cache = {}
        self._kpi_cache = {}
        self._all_clusters = None
        
        # Optimisation : limiter pour les logs dynamiques
        self.max_samples_per_cluster = 20  # RÃ©duit Ã  20 pour les logs dynamiques
        self.max_clusters = 5  # Limiter Ã  5 clusters pour les logs dynamiques
    
    def load_cluster_data(self, cluster_id: int) -> Optional[pd.DataFrame]:
        """Charger les donnÃ©es d'un cluster spÃ©cifique pour explainability"""
        
        # VÃ©rifier le cache
        if cluster_id in self._cluster_cache:
            return self._cluster_cache[cluster_id]
        
        try:
            # Charger le dataset principal avec limitation stricte pour Ã©viter les erreurs malloc
            file_path = self.data_path / "FE_output" / "df_final_fe.parquet"
            
            # Utiliser chunk loading pour les gros fichiers
            try:
                # Essayer de charger avec chunk size limitÃ©
                df = pd.read_parquet(file_path)
                
                # RÃ©duction drastique de la taille pour Ã©viter les erreurs de mÃ©moire
                if len(df) > 500:
                    df = df.sample(n=500, random_state=42)
                    self.logger.info(f"Dataset rÃ©duit Ã  {len(df)} lignes pour Ã©viter les erreurs mÃ©moire")
                
                # Conversion en types plus lÃ©gers
                for col in df.select_dtypes(include=['float64']).columns:
                    df[col] = df[col].astype('float32')
                for col in df.select_dtypes(include=['int64']).columns:
                    df[col] = df[col].astype('int32')
                    
            except MemoryError:
                self.logger.error("Erreur mÃ©moire, utilisation de dataset minimal")
                # CrÃ©er un dataset minimal si erreur mÃ©moire
                return None
            
            # Filtrer par cluster_id (physical_cellid)
            cluster_data = df[df['physical_cellid'] == cluster_id].copy()
            
            if cluster_data.empty:
                self.logger.warning(f"Aucune donnÃ©e trouvÃ©e pour le cluster {cluster_id}")
                return None
            
            # Limiter Ã  max_samples_per_cluster Ã©chantillons
            if len(cluster_data) > self.max_samples_per_cluster:
                cluster_data = cluster_data.sample(n=self.max_samples_per_cluster, random_state=42)
            
            # PrÃ©parer les features pour le modÃ¨le
            feature_cols = self._get_feature_columns(df)
            cluster_data = cluster_data[feature_cols + ['handover']].copy()
            
            # Mettre en cache
            self._cluster_cache[cluster_id] = cluster_data
            
            self.logger.info(f"ChargÃ© {len(cluster_data)} enregistrements pour le cluster {cluster_id}")
            return cluster_data
            
        except Exception as e:
            self.logger.error(f"Erreur lors du chargement du cluster {cluster_id}: {e}")
            return None
    
    def _get_feature_columns(self, df: pd.DataFrame) -> List[str]:
        """Obtenir les colonnes de features pour le modÃ¨le"""
        
        # Colonnes de base pour les prÃ©dictions de handover
        base_features = [
            'rsrp', 'rsrq', 'sinr', 'cqi', 'tx_power', 'velocity',
            'latitude', 'longitude', 'day_of_week', 'week_of_year'
        ]
        
        # Filtrer les colonnes disponibles
        available_features = [col for col in base_features if col in df.columns]
        
        # Ajouter des features supplÃ©mentaires si disponibles
        additional_features = [
            'lte_mcs', 'lte_ri', 'nr_mcs', 'nr_ri', 'ta',
            'primary_bandwidth', 'cellbandwidths', 'ul_bandwidth'
        ]
        
        for feature in additional_features:
            if feature in df.columns:
                available_features.append(feature)
        
        return available_features
    
    def get_cluster_kpi(self, cluster_id: int) -> Optional[Dict[str, float]]:
        """Calculer les KPI moyens pour un cluster"""
        
        # VÃ©rifier le cache
        if cluster_id in self._kpi_cache:
            return self._kpi_cache[cluster_id]
        
        cluster_data = self.load_cluster_data(cluster_id)
        if cluster_data is None:
            return None
        
        # KPI principaux
        kpi_data = {}
        
        # KPI de signal
        for kpi in ['rsrp', 'rsrq', 'sinr', 'cqi', 'tx_power']:
            if kpi in cluster_data.columns:
                kpi_data[kpi] = cluster_data[kpi].mean()
        
        # KPI de mobilitÃ©
        if 'velocity' in cluster_data.columns:
            kpi_data['velocity'] = cluster_data['velocity'].mean()
        
        # KPI de localisation
        if 'latitude' in cluster_data.columns and 'longitude' in cluster_data.columns:
            kpi_data['latitude'] = cluster_data['latitude'].mean()
            kpi_data['longitude'] = cluster_data['longitude'].mean()
        
        # KPI temporels
        if 'day_of_week' in cluster_data.columns:
            kpi_data['day_of_week'] = cluster_data['day_of_week'].mean()
        if 'week_of_year' in cluster_data.columns:
            kpi_data['week_of_year'] = cluster_data['week_of_year'].mean()
        
        # MÃ©triques supplÃ©mentaires
        kpi_data['n_records'] = len(cluster_data)
        kpi_data['ho_rate'] = cluster_data['handover'].mean() * 100 if 'handover' in cluster_data.columns else 0
        
        # Mettre en cache
        self._kpi_cache[cluster_id] = kpi_data
        
        return kpi_data
    
    def get_all_clusters(self) -> List[int]:
        """RÃ©cupÃ©rer les cluster_id disponibles - Version optimisÃ©e"""
        
        if self._all_clusters is not None:
            return self._all_clusters
        
        try:
            file_path = self.data_path / "FE_output" / "df_final_fe.parquet"
            
            # Chargement avec optimisation mÃ©moire
            try:
                df = pd.read_parquet(file_path)
                
                # RÃ©duction immÃ©diate de la taille
                if len(df) > 200:
                    df = df.sample(n=200, random_state=42)
                    self.logger.info(f"Dataset rÃ©duit Ã  {len(df)} lignes pour la recherche de clusters")
                
                # Conversion en types plus lÃ©gers
                for col in df.select_dtypes(include=['float64']).columns:
                    df[col] = df[col].astype('float32')
                for col in df.select_dtypes(include=['int64']).columns:
                    df[col] = df[col].astype('int32')
                    
            except (MemoryError, Exception) as e:
                self.logger.error(f"Erreur lors du chargement pour clusters: {e}")
                # Retourner quelques clusters par dÃ©faut si erreur mÃ©moire
                self._all_clusters = [77, 476, 129, 274]
                return self._all_clusters
            
            if 'physical_cellid' not in df.columns:
                self.logger.error("Colonne 'physical_cellid' non trouvÃ©e")
                return []
            
            clusters = sorted(df['physical_cellid'].dropna().unique().astype(int))
            
            # Limiter Ã  max_clusters pour Ã©viter la surcharge
            if len(clusters) > self.max_clusters:
                clusters = clusters[:self.max_clusters]
                self.logger.info(f"LimitÃ© Ã  {len(clusters)} clusters pour optimisation")
            
            self._all_clusters = clusters
            
            self.logger.info(f"TrouvÃ© {len(clusters)} clusters")
            return clusters
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la rÃ©cupÃ©ration des clusters: {e}")
            return []
    
    def get_top_clusters(self, n: int = 20) -> List[Tuple[int, int]]:
        """RÃ©cupÃ©rer les n plus grands clusters"""
        
        try:
            df = pd.read_parquet(self.data_path / "FE_output" / "df_final_fe.parquet")
            
            if 'physical_cellid' not in df.columns:
                return []
            
            cluster_counts = df['physical_cellid'].value_counts().head(n)
            
            return [(int(cluster_id), count) for cluster_id, count in cluster_counts.items()]
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la rÃ©cupÃ©ration des top clusters: {e}")
            return []
    
    def get_sample_for_prediction(self, cluster_id: int, n_samples: int = None) -> Optional[pd.DataFrame]:
        """Obtenir un Ã©chantillon du cluster pour la prÃ©diction et l'explainability - Version optimisÃ©e"""
        
        if n_samples is None:
            n_samples = min(settings.shap_samples, 20)  # Limiter Ã  20 Ã©chantillons max
        
        cluster_data = self.load_cluster_data(cluster_id)
        if cluster_data is None or len(cluster_data) == 0:
            return None
        
        # Ã‰chantillonnage alÃ©atoire avec limitation stricte
        n_samples = min(n_samples, len(cluster_data), 20)
        sample_data = cluster_data.sample(n=n_samples, random_state=42)
        
        return sample_data
    
    def prepare_features_for_prediction(self, data: pd.DataFrame) -> np.ndarray:
        """PrÃ©parer les features pour la prÃ©diction"""
        
        feature_cols = self._get_feature_columns(data)
        
        # SÃ©lectionner uniquement les colonnes de features
        features = data[feature_cols].copy()
        
        # GÃ©rer les valeurs manquantes
        for col in features.columns:
            if features[col].isna().any():
                median_val = features[col].median()
                features[col].fillna(median_val, inplace=True)
        
        return features.values
    
    def get_clusters_sequence(self) -> List[int]:
        """Obtenir la sÃ©quence de clusters pour les logs dynamiques"""
        
        all_clusters = self.get_all_clusters()
        
        # Pour les logs dynamiques, on peut vouloir un ordre spÃ©cifique
        # Par exemple: les plus grands clusters en premier
        top_clusters = self.get_top_clusters(50)
        top_cluster_ids = [cluster_id for cluster_id, _ in top_clusters]
        
        # Ajouter les autres clusters
        other_clusters = [c for c in all_clusters if c not in top_cluster_ids]
        
        return top_cluster_ids + other_clusters
    
    def get_next_cluster(self, current_index: int) -> Optional[int]:
        """Obtenir le cluster suivant dans la sÃ©quence"""
        
        clusters_sequence = self.get_clusters_sequence()
        
        if current_index >= len(clusters_sequence):
            # Revenir au dÃ©but
            return clusters_sequence[0] if clusters_sequence else None
        
        return clusters_sequence[current_index]
    
    def clear_cache(self):
        """Vider le cache"""
        self._cluster_cache.clear()
        self._kpi_cache.clear()
        self._all_clusters = None
        self.logger.info("Cache vidÃ©")
    
    def preload_top_clusters(self, n: int = 20):
        """PrÃ©charger les donnÃ©es des plus grands clusters"""
        
        top_clusters = self.get_top_clusters(n)
        
        with ThreadPoolExecutor(max_workers=settings.max_workers) as executor:
            futures = []
            
            for cluster_id, _ in top_clusters:
                future = executor.submit(self.get_cluster_kpi, cluster_id)
                futures.append(future)
            
            # Attendre la fin du chargement
            for future in futures:
                future.result()
        
        self.logger.info(f"PrÃ©chargÃ© {len(top_clusters)} clusters")


# Instance globale du chargeur de donnÃ©es
data_loader = ExplainabilityDataLoader()

