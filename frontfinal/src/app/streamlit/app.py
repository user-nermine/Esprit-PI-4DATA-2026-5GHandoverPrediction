"""
Frontend Streamlit pour le Backend Explainability DoNext 5G
Affichage des logs dynamiques des clusters avec KPI, prédictions et explainability SHAP
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import json
from datetime import datetime
import time
import shap
import matplotlib.pyplot as plt
import seaborn as sns

# Configuration de la page
st.set_page_config(
    page_title="DoNext 5G Explainability Dashboard",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configuration du backend
BACKEND_URL = "http://localhost:8000"

# Styles CSS personnalisés
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
        margin: 0.5rem 0;
    }
    .cluster-highlight {
        background-color: #e8f4fd;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #ff7f0e;
        margin: 1rem 0;
    }
    .prediction-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 1rem;
        font-size: 0.875rem;
        font-weight: bold;
        margin: 0.25rem;
    }
    .prediction-no-handover { background-color: #d4edda; color: #155724; }
    .prediction-intra-freq { background-color: #fff3cd; color: #856404; }
    .prediction-inter-freq { background-color: #f8d7da; color: #721c24; }
    .prediction-inter-rat { background-color: #d1ecf1; color: #0c5460; }
</style>
""", unsafe_allow_html=True)

class APIManager:
    """Gestionnaire des appels API au backend"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
    
    def get(self, endpoint: str):
        """Appel GET à l'API"""
        try:
            response = requests.get(f"{self.base_url}{endpoint}")
            if response.status_code == 200:
                return response.json()
            else:
                st.error(f"Erreur API: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            st.error(f"Erreur de connexion au backend: {e}")
            return None
    
    def post(self, endpoint: str, data: dict = None):
        """Appel POST à l'API"""
        try:
            response = requests.post(f"{self.base_url}{endpoint}", json=data)
            if response.status_code == 200:
                return response.json()
            else:
                st.error(f"Erreur API: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            st.error(f"Erreur de connexion au backend: {e}")
            return None

# Initialisation du gestionnaire API
api = APIManager(BACKEND_URL)

def main():
    """Fonction principale de l'application"""
    
    # Header
    st.markdown('<h1 class="main-header">📡 DoNext 5G Explainability Dashboard</h1>', unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Vérification de la connexion au backend
        if st.button("🔄 Vérifier la connexion"):
            check_backend_connection()
        
        # Contrôle des logs dynamiques
        st.subheader("📊 Logs Dynamiques")
        
        # Statut actuel
        status = api.get("/api/v1/logs/dynamic/status")
        if status:
            is_logging = status.get("is_logging", False)
            current_cluster = status.get("current_cluster")
            total_logged = status.get("total_logged", 0)
            
            if is_logging:
                st.success("🟢 Logs dynamiques ACTIFS")
                st.info(f"Cluster actuel: {current_cluster}")
                st.info(f"Total loggé: {total_logged}")
            else:
                st.warning("🔴 Logs dynamiques INACTIFS")
        else:
            st.error("❌ Impossible de vérifier le statut")
        
        # Boutons de contrôle
        col1, col2 = st.columns(2)
        with col1:
            if st.button("▶️ Démarrer"):
                start_dynamic_logs()
        with col2:
            if st.button("⏹️ Arrêter"):
                stop_dynamic_logs()
        
        # Intervalle de logging
        interval = st.slider("Intervalle (secondes)", 1, 30, 5)
        
        # Sélection de cluster
        st.subheader("🎯 Sélection de Cluster")
        
        # Obtenir la liste des clusters
        clusters_info = api.get("/api/v1/explainability/summary")
        if clusters_info:
            total_clusters = clusters_info.get("total_clusters", 0)
            st.info(f"Total clusters: {total_clusters}")
            
            # Top clusters
            top_clusters = api.get("/api/v1/explainability/clusters/top-explainability?limit=10")
            if top_clusters and top_clusters.get("clusters"):
                cluster_options = [f"Cluster {c['cluster_id']}" for c in top_clusters["clusters"]]
                selected_cluster = st.selectbox("Choisir un cluster", cluster_options)
                if selected_cluster:
                    cluster_id = int(selected_cluster.split()[1])
                    st.session_state.selected_cluster = cluster_id
        
        # Rafraîchissement automatique
        auto_refresh = st.checkbox("🔄 Rafraîchissement auto", value=True)
        refresh_interval = st.slider("Intervalle (secondes)", 5, 60, 10) if auto_refresh else None
    
    # Onglets principaux
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Dashboard", 
        "🔍 Logs Dynamiques", 
        "🎯 Cluster Details", 
        "📈 Explainability", 
        "⚙️ API Status"
    ])
    
    with tab1:
        show_dashboard()
    
    with tab2:
        show_dynamic_logs()
    
    with tab3:
        show_cluster_details()
    
    with tab4:
        show_explainability()
    
    with tab5:
        show_api_status()
    
    # Rafraîchissement automatique
    if auto_refresh and refresh_interval:
        time.sleep(refresh_interval)
        st.rerun()

def check_backend_connection():
    """Vérifier la connexion au backend"""
    health = api.get("/health")
    if health:
        if health.get("status") == "healthy":
            st.success("✅ Connexion au backend établie")
            st.json(health)
        else:
            st.error("❌ Backend non sain")
            st.json(health)
    else:
        st.error("❌ Impossible de se connecter au backend")

def start_dynamic_logs():
    """Démarrer les logs dynamiques"""
    result = api.post("/api/v1/logs/dynamic/start")
    if result:
        st.success("✅ Logs dynamiques démarrés")
        st.rerun()

def stop_dynamic_logs():
    """Arrêter les logs dynamiques"""
    result = api.post("/api/v1/logs/dynamic/stop")
    if result:
        st.success("✅ Logs dynamiques arrêtés")
        st.rerun()

def show_dashboard():
    """Afficher le dashboard principal"""
    
    st.header("📊 Dashboard Principal")
    
    # Statistiques générales
    col1, col2, col3, col4 = st.columns(4)
    
    # Obtenir le statut
    status = api.get("/api/v1/logs/dynamic/status")
    if status:
        with col1:
            st.metric("Clusters Total", status.get("total_clusters", 0))
        with col2:
            st.metric("Clusters Loggés", status.get("total_logged", 0))
        with col3:
            st.metric("Cluster Actuel", status.get("current_cluster", "N/A"))
        with col4:
            is_logging = "Oui" if status.get("is_logging", False) else "Non"
            st.metric("Logs Actifs", is_logging)
    
    # Résumé des prédictions
    predictions_summary = api.get("/api/v1/predictions/summary")
    if predictions_summary:
        st.subheader("📈 Résumé des Prédictions")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Distribution des prédictions
            pred_dist = predictions_summary.get("prediction_distribution", {})
            if pred_dist:
                fig = px.pie(
                    values=list(pred_dist.values()),
                    names=list(pred_dist.keys()),
                    title="Distribution des Prédictions"
                )
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Confiance moyenne
            avg_confidence = predictions_summary.get("average_confidence", 0)
            st.metric("Confiance Moyenne", f"{avg_confidence:.2%}")
            
            # Prédiction la plus commune
            most_common = predictions_summary.get("most_common_prediction", "N/A")
            st.metric("Prédiction la Plus Commune", most_common)
    
    # Logs récents
    st.subheader("📋 Logs Récents")
    
    recent_logs = api.get("/api/v1/logs/dynamic/limit/10")
    if recent_logs and isinstance(recent_logs, list):
        # Formater les logs pour l'affichage
        logs_df = []
        for log in recent_logs:
            if isinstance(log, dict):
                logs_df.append({
                    "Timestamp": log.get("timestamp", ""),
                    "Cluster ID": log.get("cluster_id", ""),
                    "Prédiction": log.get("dominant_prediction", ""),
                    "Confiance": f"{log.get('confidence', 0):.2%}",
                    "HO Rate": f"{log.get('cluster_kpi', {}).get('ho_rate', 0):.1f}%"
                })
            else:
                st.warning(f"Format de log invalide: {type(log)}")
        
        if logs_df:
            df = pd.DataFrame(logs_df)
            st.dataframe(df, use_container_width=True)
    else:
        st.info("Aucun log récent trouvé")

def show_dynamic_logs():
    """Afficher les logs dynamiques"""
    
    st.header("🔍 Logs Dynamiques des Clusters")
    
    # Filtres
    col1, col2 = st.columns(2)
    
    with col1:
        limit = st.selectbox("Nombre de logs", [10, 25, 50, 100, 200], index=1)
    
    with col2:
        cluster_filter = st.text_input("Filtrer par cluster ID (ex: 274,476)")
    
    # Obtenir les logs
    endpoint = f"/api/v1/logs/dynamic/limit/{limit}"
    
    if cluster_filter:
        try:
            cluster_ids = [int(x.strip()) for x in cluster_filter.split(",")]
            # Pour l'instant, on affiche tous les logs puis on filtre
            pass
        except:
            st.error("Format de cluster ID invalide")
            cluster_filter = None
    
    logs = api.get(endpoint)
    
    if logs and isinstance(logs, list):
        st.success(f"✅ {len(logs)} logs trouvés")
        
        # Afficher les logs
        for i, log in enumerate(logs):
            if isinstance(log, dict):
                cluster_id = log.get("cluster_id", "N/A")
                timestamp = log.get("timestamp", "")
                dominant_pred = log.get("dominant_prediction", "")
                confidence = log.get("confidence", 0)
            else:
                st.error(f"Format de log invalide à l'index {i}: {type(log)}")
                continue
            
            # Carte de log
            with st.container():
                st.markdown(f"""
                <div class="cluster-highlight">
                    <h3>📍 Cluster {cluster_id}</h3>
                    <p><strong>Timestamp:</strong> {timestamp}</p>
                    <p><strong>Prédiction:</strong> <span class="prediction-badge prediction-{dominant_pred.replace('_', '-')}">{dominant_pred}</span></p>
                    <p><strong>Confiance:</strong> {confidence:.2%}</p>
                </div>
                """, unsafe_allow_html=True)
                
                # KPI du cluster
                cluster_kpi = log.get("cluster_kpi", {})
                if cluster_kpi:
                    kpi_cols = st.columns(4)
                    
                    with kpi_cols[0]:
                        st.metric("RSRP", f"{cluster_kpi.get('rsrp', 0):.1f} dBm")
                    with kpi_cols[1]:
                        st.metric("RSRQ", f"{cluster_kpi.get('rsrq', 0):.1f} dB")
                    with kpi_cols[2]:
                        st.metric("SINR", f"{cluster_kpi.get('sinr', 0):.1f} dB")
                    with kpi_cols[3]:
                        st.metric("HO Rate", f"{cluster_kpi.get('ho_rate', 0):.1f}%")
                
                # Prédictions détaillées
                predictions = log.get("predictions", {})
                if predictions:
                    st.subheader("📊 Probabilités de Prédiction")
                    
                    pred_cols = st.columns(4)
                    labels = ["no_handover", "intra_freq_handover", "inter_freq_handover", "inter_rat_handover"]
                    
                    for i, label in enumerate(labels):
                        with pred_cols[i]:
                            prob = predictions.get(label, 0)
                            st.metric(label.replace("_", " ").title(), f"{prob:.2%}")
                
                # Explainability SHAP
                explainability = log.get("explainability", {})
                shap_values = explainability.get("shap_values", {})
                
                if shap_values:
                    st.subheader("🔍 Explainability SHAP")
                    
                    # Graphique des valeurs SHAP
                    shap_df = pd.DataFrame(list(shap_values.items()), columns=["Feature", "SHAP Value"])
                    
                    fig = px.bar(
                        shap_df, 
                        x="SHAP Value", 
                        y="Feature",
                        orientation='h',
                        title="Valeurs SHAP par Feature"
                    )
                    st.plotly_chart(fig, use_container_width=True)
                
                st.divider()
    else:
        st.warning("⚠️ Aucun log trouvé. Vérifiez que les logs dynamiques sont actifs.")

def show_cluster_details():
    """Afficher les détails d'un cluster spécifique"""
    
    st.header("🎯 Détails du Cluster")
    
    # Sélection de cluster
    cluster_id = st.session_state.get("selected_cluster")
    
    if not cluster_id:
        st.warning("⚠️ Veuillez sélectionner un cluster dans la sidebar")
        return
    
    # Obtenir les détails du cluster
    cluster_data = api.get(f"/api/v1/explainability/cluster/{cluster_id}")
    
    if cluster_data:
        st.success(f"✅ Détails du Cluster {cluster_id}")
        
        # Informations générales
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📊 Informations Générales")
            
            cluster_kpi = cluster_data.get("cluster_kpi", {})
            
            st.metric("Nombre d'enregistrements", cluster_kpi.get("n_records", 0))
            st.metric("HO Rate", f"{cluster_kpi.get('ho_rate', 0):.1f}%")
            st.metric("Dernière mise à jour", cluster_data.get("timestamp", ""))
        
        with col2:
            st.subheader("🎯 Prédictions")
            
            predictions = cluster_data.get("predictions", {})
            dominant_pred = cluster_data.get("dominant_prediction", "")
            confidence = cluster_data.get("confidence", 0)
            
            # Afficher les prédictions
            for label, prob in predictions.items():
                label_display = label.replace("_", " ").title()
                if label == dominant_pred:
                    st.metric(label_display, f"{prob:.2%}", "🎯 Dominant")
                else:
                    st.metric(label_display, f"{prob:.2%}")
            
            st.metric("Confiance", f"{confidence:.2%}")
        
        # KPI détaillés
        st.subheader("📈 KPI Détaillés")
        
        kpi_data = []
        for kpi, value in cluster_kpi.items():
            if kpi != "n_records" and isinstance(value, (int, float)):
                kpi_data.append({"KPI": kpi.upper(), "Valeur": value})
        
        if kpi_data:
            kpi_df = pd.DataFrame(kpi_data)
            
            # Graphique des KPI
            fig = px.bar(
                kpi_df, 
                x="KPI", 
                y="Valeur",
                title="KPI du Cluster"
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # Logs spécifiques au cluster
        st.subheader("📋 Logs du Cluster")
        
        cluster_logs = api.get(f"/api/v1/logs/cluster/{cluster_id}?limit=20")
        if cluster_logs and cluster_logs.get("logs"):
            logs_df = []
            for log in cluster_logs["logs"]:
                logs_df.append({
                    "Timestamp": log.get("timestamp", ""),
                    "Prédiction": log.get("dominant_prediction", ""),
                    "Confiance": f"{log.get('confidence', 0):.2%}"
                })
            
            df = pd.DataFrame(logs_df)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("Aucun log spécifique trouvé pour ce cluster")
    
    else:
        st.error(f"❌ Impossible d'obtenir les détails du cluster {cluster_id}")

def show_explainability():
    """Afficher l'explainability SHAP"""
    
    st.header("🔍 Explainability SHAP")
    
    # Options
    col1, col2 = st.columns(2)
    
    with col1:
        cluster_id = st.number_input("ID du Cluster", min_value=0, value=274)
    
    with col2:
        analysis_type = st.selectbox("Type d'analyse", ["SHAP Values", "Feature Importance", "Comparaison"])
    
    # Obtenir les données d'explainability
    explainability_data = api.get(f"/api/v1/explainability/cluster/{cluster_id}")
    
    if explainability_data:
        st.success(f"✅ Explainability du Cluster {cluster_id}")
        
        explainability = explainability_data.get("explainability", {})
        
        if analysis_type == "SHAP Values":
            shap_values = explainability.get("shap_values", {})
            
            if shap_values:
                st.subheader("📊 Valeurs SHAP")
                
                # DataFrame pour le graphique
                shap_df = pd.DataFrame(list(shap_values.items()), columns=["Feature", "SHAP Value"])
                shap_df = shap_df.sort_values("SHAP Value", ascending=True)
                
                # Graphique
                fig = px.bar(
                    shap_df, 
                    x="SHAP Value", 
                    y="Feature",
                    orientation='h',
                    title=f"Valeurs SHAP - Cluster {cluster_id}",
                    color="SHAP Value",
                    color_continuous_scale="RdYlBu"
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # Tableau des valeurs
                st.subheader("📋 Tableau des Valeurs")
                st.dataframe(shap_df, use_container_width=True)
        
        elif analysis_type == "Feature Importance":
            feature_importance = explainability.get("feature_importance", {})
            
            if feature_importance:
                st.subheader("🎯 Importance des Features")
                
                # DataFrame pour le graphique
                importance_df = pd.DataFrame(list(feature_importance.items()), columns=["Feature", "Importance"])
                importance_df = importance_df.sort_values("Importance", ascending=True)
                
                # Graphique
                fig = px.bar(
                    importance_df, 
                    x="Importance", 
                    y="Feature",
                    orientation='h',
                    title=f"Importance des Features - Cluster {cluster_id}",
                    color="Importance",
                    color_continuous_scale="Viridis"
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # Top features
                st.subheader("🏆 Top Features")
                top_features = importance_df.tail(10)
                st.dataframe(top_features, use_container_width=True)
        
        elif analysis_type == "Comparaison":
            st.subheader("🔄 Comparaison de Clusters")
            
            # Sélection de clusters pour la comparaison
            cluster_ids_input = st.text_input("IDs des clusters à comparer (séparés par des virgules)", 
                                           value="274,476,77")
            
            if cluster_ids_input:
                try:
                    cluster_ids = [int(x.strip()) for x in cluster_ids_input.split(",")]
                    
                    if len(cluster_ids) >= 2:
                        comparison = api.post("/api/v1/explainability/compare", cluster_ids)
                        
                        if comparison and comparison.get("results"):
                            # Graphique de comparaison
                            comparison_data = []
                            
                            for result in comparison["results"]:
                                cluster_id = result["cluster_id"]
                                predictions = result["predictions"]
                                
                                for label, prob in predictions.items():
                                    comparison_data.append({
                                        "Cluster": f"Cluster {cluster_id}",
                                        "Label": label.replace("_", " ").title(),
                                        "Probabilité": prob
                                    })
                            
                            comp_df = pd.DataFrame(comparison_data)
                            
                            fig = px.bar(
                                comp_df, 
                                x="Label", 
                                y="Probabilité",
                                color="Cluster",
                                barmode="group",
                                title="Comparaison des Prédictions"
                            )
                            st.plotly_chart(fig, use_container_width=True)
                            
                            # Résumé de la comparaison
                            summary = comparison.get("summary", {})
                            if summary:
                                st.subheader("📊 Résumé de la Comparaison")
                                
                                avg_predictions = summary.get("average_predictions", {})
                                most_common = summary.get("most_common_prediction", "")
                                
                                col1, col2 = st.columns(2)
                                
                                with col1:
                                    st.metric("Prédiction la Plus Commune", most_common)
                                
                                with col2:
                                    if avg_predictions:
                                        avg_prob = avg_predictions.get(most_common, 0)
                                        st.metric("Probabilité Moyenne", f"{avg_prob:.2%}")
                
                except ValueError:
                    st.error("Format d'IDs de clusters invalide")
    
    else:
        st.error(f"❌ Impossible d'obtenir l'explainability du cluster {cluster_id}")

def show_api_status():
    """Afficher le statut de l'API"""
    
    st.header("⚙️ Statut de l'API")
    
    # Health check
    health = api.get("/health")
    if health:
        st.subheader("🏥 Health Check")
        st.json(health)
    
    # Info de l'application
    info = api.get("/info")
    if info:
        st.subheader("ℹ️ Information de l'Application")
        st.json(info)
    
    # Statut détaillé
    status = api.get("/status")
    if status:
        st.subheader("📊 Statut Détaillé")
        st.json(status)
    
    # Statistiques des logs
    logging_stats = api.get("/api/v1/logs/dynamic/statistics")
    if logging_stats:
        st.subheader("📈 Statistiques des Logs")
        st.json(logging_stats)

if __name__ == "__main__":
    main()
