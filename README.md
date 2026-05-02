# Esprit-PI-4DATA-2026-5GHandoverPrediction
This project was developed as part of the PI – 4th Year Engineering Program at Esprit School of Engineering (Academic Year 2025–2026). Predictive ML/DL framework for 5G handover management using the DoNext dataset.

# 5G Handover Prediction – Predictive ML/DL Framework

## Overview
This project was developed as part of the PI – 4th Year Engineering Program at **Esprit School of Engineering** (Academic Year 2025–2026).

It consists of a predictive machine learning and deep learning framework for 5G handover management. The system anticipates connection loss and ensures seamless cell-to-cell switching before disruptions occur, targeting a 35% improvement in handover success rate.

## Features
- Handover event binary classification (Label 1)
- Network latency regression prediction (Label 2)
- 8-step data preprocessing pipeline
- Feature engineering (rsrp_delta, rsrp_roll5, sinr_roll5, rsrp_degrading...)
- Temporal train/val/test split (70/15/15) with no data leakage
- Correlation analysis across 5 datasets
- Multi-environment support: Mobile, Hbahn (high-speed transit), Static

## Tech Stack

### Data & ML
- Python
- Pandas / NumPy
- Scikit-learn
- TensorFlow / PyTorch

### Visualization
- Matplotlib / Seaborn
- Plotly

## Architecture
The pipeline consists of:
1. Drop dead columns (32 removed)
2. 3GPP physical range filtering (853 835 outliers corrected)
3. Intelligent imputation (GPS conserved)
4. Handover label generation (20 616 events, 0.16% rate)
5. Latency label (avg 42ms target)
6. Feature engineering
7. Memory optimization (float32/int32)
8. Temporal split (no shuffle)

## Contributors
- Nermine Rahali
- Manel Aloui
- Manel Magdouli
- Wiem Tanazefti
- Dhia Selmi

## Academic Context
Developed at **Esprit School of Engineering – Tunisia**
PIML – Final Year Engineering | 2025–2026
Team: **INVICTUS**

## Getting Started
```bash
# Clone the repository
git clone https://github.com/[your-username]/Esprit-PIML-[Classe]-2026-5GHandoverPrediction.git

# Install dependencies
pip install -r requirements.txt

# Run preprocessing
python pipeline/preprocessing.py

# Train model
python models/train.py
```

## Acknowledgments
- Dataset: **DoNext** – 100GB+ real-world 4G/5G measurements, Dortmund, Germany
- Esprit School of Engineering – Tunisia
- SDGs aligned: #7 Affordable and Clean Energy, #9 Industry Innovation, #11 Sustainable Cities
```

---

## 📁 Step 5 — Structure des Fichiers à Push

Organise ton repo comme ça:
```
📦 Esprit-PIML-[Classe]-2026-5GHandoverPrediction
├── 📁 data/
│   └── README.md  (expliquer le DoNext dataset, pas upload les 100GB!)
├── 📁 notebooks/
│   ├── 01_EDA.ipynb
│   ├── 02_Preprocessing.ipynb
│   └── 03_Modeling.ipynb
├── 📁 pipeline/
│   └── preprocessing.py
├── 📁 models/
│   └── train.py
├── 📄 requirements.txt
└── 📄 README.md

<!-- webhook test -->

<!-- webhook test -->
