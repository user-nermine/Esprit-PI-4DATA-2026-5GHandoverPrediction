# Esprit-PI-4DATA-2026-5GHandoverPrediction

> This project was developed as part of the **PI – 4th Year Engineering Program** at **Esprit School of Engineering** (Academic Year 2025–2026).
> Predictive ML/DL framework for 5G handover management using the DoNext dataset.

---

# 🛰️ Nexovera — 5G Handover Intelligence Platform

## Overview

This project was developed as part of the **PI – 4th Year Engineering Program** at **Esprit School of Engineering** (Academic Year 2025–2026).

In 5G networks, handover is one of the most critical operations for service continuity. Traditional networks react *after* degradation occurs — **Nexovera predicts it before it happens**.

Built on **12.6M real 5G measurements** from Dortmund, Germany (DoNext dataset), Nexovera is a complete end-to-end 5G Handover Intelligence Platform combining a CRISP-DM ML pipeline, FastAPI microservices, an Angular multi-role dashboard, and a full MLOps stack.

---

## Features

- **4 Prediction Objectives (DSO1–DSO4)**
  - DSO1 — Handover event binary classification
  - DSO2 — Signal drop detection
  - DSO3 — Next best cell selection (multi-class)
  - DSO4 — Handover type classification
- **ST-DBSCAN spatial clustering** — 205 network zones identified, 101 features
- **8-step data preprocessing pipeline** with 3GPP-compliant filtering
- **Feature engineering** (rsrp_delta, rsrp_roll5, sinr_roll5, rsrp_degrading, ...)
- **Temporal train/val/test split** (70/15/15) — zero data leakage
- **Correlation analysis** across 5 datasets (Mobile, Hbahn, Static environments)
- **3 FastAPI microservices** — real-time prediction, monitoring & SHAP explainability
- **Angular dashboard** — 5 user roles with P1/P2/P3 alerts, live Leaflet map & automated PDF reports
- **Full MLOps pipeline** — HuggingFace + DVC · Airflow DAG (every 6h) · MLflow registry · GitHub Actions CI/CD · Prometheus + Grafana + ELK stack

---

## Tech Stack

### Data & ML

- Python
- Pandas / NumPy
- Scikit-learn
- LightGBM / XGBoost
- BiLSTM (TensorFlow/Keras) / TabNet (PyTorch)

### Visualization & Explainability

- Matplotlib / Seaborn
- Plotly
- SHAP

### Backend & Services

- FastAPI (3 microservices: prediction, monitoring, explainability)
- Spring Boot (user-service, ms-reporting, gateway-service, discovery-service)
- PostgreSQL

### Frontend

- Angular
- Leaflet (live map)
- ApexCharts

### MLOps & Infrastructure

- HuggingFace Hub + DVC (data & model versioning)
- Apache Airflow (DAG retraining every 6h)
- MLflow (experiment tracking & model registry)
- GitHub Actions CI/CD (71 runs · 40/40 Pytest · Score 13/13)
- Docker / Docker Hub
- Prometheus + Grafana + ELK Stack (Elasticsearch, Logstash, Kibana)

---

## Architecture

### ML Pipeline (CRISP-DM)

The pipeline consists of:

1. Drop dead columns (32 removed)
2. 3GPP physical range filtering (853 835 outliers corrected)
3. Intelligent imputation (GPS conserved)
4. ST-DBSCAN spatial clustering → 205 network zones, 101 features
5. Handover label generation — DSO1 binary · DSO2 signal drop · DSO3 next cell · DSO4 type
6. Feature engineering (rsrp_delta, rsrp_roll5, sinr_roll5, rsrp_degrading, ...)
7. Memory optimization (float32/int32)
8. Temporal split — no shuffle, no leakage

### Microservices Architecture

```
Angular Dashboard (5 roles: NOC · RAN · Core Engineer · Data Scientist · Admin)
        │
        ▼
Spring Gateway Service  ──→  Eureka Discovery Service
        │
        ├──→ User Service (Spring Boot · JWT · PostgreSQL)
        ├──→ Reporting Service (Spring Boot · PostgreSQL)
        │
        ├──→ Prediction API (FastAPI · LightGBM · XGBoost · BiLSTM · TabNet)
        ├──→ Monitoring API (FastAPI · Prometheus · drift detection)
        └──→ Explainability API (FastAPI · SHAP)
```

### MLOps Pipeline

```
DoNext Dataset (HuggingFace Hub + DVC)
        │
        ▼
Airflow DAG (every 6h retraining)
        │
        ├──→ Preprocessing & Feature Engineering
        ├──→ Model Training (DSO1–DSO4)
        ├──→ MLflow Experiment Tracking & Registry
        └──→ GitHub Actions CI/CD
                │
                ├──→ Pytest (40/40) · Score 13/13
                ├──→ Docker Build & Push (Docker Hub)
                └──→ Deployment
                        │
                        └──→ Prometheus + Grafana + ELK Stack (monitoring & observability)
```

---

## Repository Structure

```
📦 Esprit-PI-4DATA-2026-5GHandoverPrediction
│
├── 📁 .dvc/                        # DVC configuration
├── 📁 .github/                     # GitHub Actions CI/CD workflows
├── 📁 dags/                        # Airflow DAGs (retraining pipeline)
│
├── 📁 src/                         # Core ML source code
│   ├── preprocessing.py
│   ├── feature_engineering.py
│   ├── train.py
│   ├── mlflow_utils.py
│   ├── 📁 data/                    # HuggingFace data loader
│   └── 📁 models/                  # DSO1–DSO4 model definitions
│
├── 📁 notebooks/
│   ├── NB1_EDA.ipynb
│   ├── NB2_Handover_FE.ipynb
│   ├── NB3_Preprocessing.ipynb
│   ├── NB4_DSO1_v2.ipynb
│   ├── NB4_DSO2_v2.ipynb
│   ├── NB4_DSO3_V2.ipynb
│   └── NB4_DSO4_V2.ipynb
│
├── 📁 prediction/                  # FastAPI microservice — real-time prediction
├── 📁 monitoring/                  # FastAPI microservice — drift monitoring
├── 📁 explainability/              # FastAPI microservice — SHAP explainability
│
├── 📁 microservices_final/         # Spring Boot backend
│   ├── gateway-service/
│   ├── discovery-service/
│   ├── user-service/
│   ├── ms_reporting/
│   ├── simulator/
│   └── docker-compose.yml
│
├── 📁 Nexovera_App/                # Angular frontend
│   └── src/app/
│       ├── 📁 roles/               # Role-based modules (NOC · RAN · Core · DS · Admin)
│       ├── 📁 services/            # API service layer
│       └── 📁 theme/               # Layout, navigation, shared components
│
├── 📁 MODEL_output/                # Trained models & evaluation outputs (DSO1–DSO4)
├── 📁 mlruns/                      # MLflow experiment runs
├── 📁 FE_data/                     # Feature-engineered data (DVC tracked)
├── 📁 PT_output/                   # Preprocessed tensors (DVC tracked)
│
├── 📁 scripts/                     # Utility scripts (CI/CD, data download, validation)
├── 📁 tests/                       # Pytest test suite (40/40 passing)
├── 📁 logs/ · logstash/            # ELK stack configuration
│
├── FE_data.dvc
├── FE_output.dvc
├── MODEL_output.dvc
├── PT_output.dvc
├── docker-compose.yml
├── prometheus.yml
├── requirements.txt
└── 📄 README.md
```

---

## Getting Started

```bash
# Clone the repository
git clone https://github.com/user-nermine/Esprit-PI-4DATA-2026-5GHandoverPrediction.git
cd Esprit-PI-4DATA-2026-5GHandoverPrediction

# Install dependencies
pip install -r requirements.txt

# Pull DVC-tracked data (requires HuggingFace access)
dvc pull

# Run preprocessing
python src/preprocessing.py

# Run feature engineering
python src/feature_engineering.py

# Train models (DSO1–DSO4)
python src/train.py

# Launch microservices
docker-compose up --build
```

---

## Contributors

| Name |
|---|
| **Med Dhia Selmi** |
| **Nermine Rahali** |
| **Manel Aloui** |
| **Manel Magdouli** |
| **Wiem Tanazefti** |

---

## Academic Context

Developed at **Esprit School of Engineering – Tunisia**
PI Final Year Engineering | 2025–2026
Team: **INVICTUS**

Supervisors: **Bouraoui Rahma** & **Safa Chérif** — Esprit School of Engineering

---

## Acknowledgments

- **Dataset**: DoNext – 12.6M real-world 4G/5G measurements, Dortmund, Germany
- **Esprit School of Engineering** – Tunisia
- **SDGs aligned**: #7 Affordable and Clean Energy · #9 Industry Innovation · #11 Sustainable Cities
