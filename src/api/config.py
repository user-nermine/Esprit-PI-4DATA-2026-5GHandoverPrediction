"""
Configuration du backend Explainability DoNext 5G
"""

from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    """Configuration principale de l'application"""
    
    # Serveur
    host: str = "0.0.0.0"  # nosec B104
    port: int = 8000
    debug: bool = True
    log_level: str = "INFO"
    
    # Paths
    data_path: str = "/app"
    logs_path: str = "./logs"
    models_path: str = "./models"
    
    # Explainability
    explainability_enabled: bool = False  # Reste dÃ©sactivÃ© pour Ã©viter la surcharge
    dynamic_logs_enabled: bool = True  # RÃ©activÃ© avec optimisation
    cluster_log_interval: int = 60  # AugmentÃ© Ã  60 secondes pour rÃ©duire la charge
    shap_samples: int = 5  # RÃ©duit Ã  5 Ã©chantillons minimum
    
    # Model
    model_path: str = "./models/handover_model.pkl"
    scaler_path: str = "./models/scaler.pkl"
    
    # 4 Labels de prÃ©diction
    labels: List[str] = ["no_handover", "intra_freq_handover", "inter_freq_handover", "inter_rat_handover"]
    
    # Performance
    max_workers: int = 1  # RÃ©duit Ã  1 pour Ã©viter la surcharge
    batch_size: int = 100  # RÃ©duit Ã  100
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "protected_namespaces": ("settings_",)
    }
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # CrÃ©er les rÃ©pertoires nÃ©cessaires
        os.makedirs(self.logs_path, exist_ok=True)
        os.makedirs(self.models_path, exist_ok=True)


# Instance globale des settings
settings = Settings()



