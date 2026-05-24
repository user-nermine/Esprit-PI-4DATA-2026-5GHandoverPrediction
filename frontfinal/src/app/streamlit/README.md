# Frontend Streamlit - DoNext 5G Explainability Dashboard

## 🎯 Objectif

Interface Streamlit pour visualiser les résultats du backend d'explainability avec logs dynamiques des clusters.

## 🚀 Fonctionnalités

### 1. **Dashboard Principal**
- Statistiques en temps réel des clusters
- Distribution des prédictions des 4 labels
- Logs récents avec KPI et explainability

### 2. **Logs Dynamiques**
- Affichage en temps réel des logs qui parcourent les clusters
- Filtres par cluster ID
- Visualisation des KPI et prédictions

### 3. **Détails de Cluster**
- Analyse détaillée d'un cluster spécifique
- KPI complets (RSRP, RSRQ, SINR, CQI, etc.)
- Historique des logs du cluster

### 4. **Explainability SHAP**
- Valeurs SHAP par feature
- Importance des features
- Comparaison entre clusters

### 5. **Statut API**
- Health check du backend
- Statut des logs dynamiques
- Statistiques d'utilisation

## 📊 Visualisations

- **Graphiques en barres** : Distribution des prédictions, valeurs SHAP
- **Métriques** : KPI des clusters, confiance des prédictions
- **Tableaux** : Logs détaillés, comparaisons
- **Badges** : Types de prédictions avec couleurs

## 🎨 Interface

### Sidebar
- Contrôle des logs dynamiques (démarrer/arrêter)
- Sélection de cluster
- Configuration du rafraîchissement

### Onglets Principaux
1. **Dashboard** : Vue d'ensemble
2. **Logs Dynamiques** : Logs en temps réel
3. **Cluster Details** : Analyse par cluster
4. **Explainability** : SHAP et feature importance
5. **API Status** : État du système

## 🔧 Installation

```bash
# Installation des dépendances
pip install -r requirements.txt

# Lancement de l'application
streamlit run app.py
```

## 📡 Connexion Backend

L'application se connecte automatiquement au backend sur `http://localhost:8000`.

Assurez-vous que le backend est démarré avant de lancer l'interface :

```bash
# Dans le dossier backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 🎯 Cas d'Usage

1. **RAN Engineer** : Surveiller les prédictions de handover par cellule
2. **Performance Analyst** : Analyser les facteurs influents via SHAP
3. **Network Optimizer** : Comparer les clusters pour optimisation
4. **Data Scientist** : Explorer le comportement du modèle

## 📈 Fonctionnalités Clés

### Logs Dynamiques
- Parcourt automatiquement les clusters `physical_cellid`
- Chaque log contient : KPI, prédictions des 4 labels, SHAP
- Transition fluide entre clusters

### Prédictions des 4 Labels
- `no_handover` : Pas de handover (vert)
- `intra_freq_handover` : Handover intra-fréquence (jaune)
- `inter_freq_handover` : Handover inter-fréquence (rouge)
- `inter_rat_handover` : Handover inter-RAT (bleu)

### Explainability SHAP
- Valeurs SHAP pour chaque feature
- Feature importance par cluster
- Comparaison visuelle entre clusters

## 🔍 Visualisation des Logs

Chaque log affiche :
- **Cluster ID** et timestamp
- **KPI** : RSRP, RSRQ, SINR, CQI, HO Rate
- **Prédictions** : Probabilités pour les 4 labels
- **SHAP** : Graphique des valeurs d'explainability
- **Confiance** : Score de confiance de la prédiction

## 🎨 Personnalisation

### Styles CSS
- Badges colorés pour les prédictions
- Cartes mises en évidence pour les clusters
- Design responsive et moderne

### Interactivité
- Rafraîchissement automatique configurable
- Filtres dynamiques
- Navigation entre clusters

## 🚀 Utilisation

1. **Démarrer le backend** : `uvicorn app.main:app --reload`
2. **Lancer Streamlit** : `streamlit run app.py`
3. **Ouvrir le navigateur** : `http://localhost:8501`
4. **Démarrer les logs** : Bouton "▶️ Démarrer" dans la sidebar
5. **Explorer** : Naviguer entre les onglets pour analyser les données
