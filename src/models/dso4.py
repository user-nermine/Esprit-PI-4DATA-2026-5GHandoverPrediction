# src/models/dso4.py
# Converted from NB4_DSO4_V2.ipynb
# Task  : Multiclass classification â€” predict handover TYPE (3GPP TR 38.300)
# Input : PT_output/df_preprocessed.parquet  +  config.json
#         FE_output/df_final_fe.parquet       (labels: handover, ho_type)
# Output: MODEL_output/DSO4/
#           xgb_dso4.pkl        lgbm_dso4.pkl       rf_dso4.pkl
#           lstm_dso4.h5        lstm_dso4_best.h5
#           tabnet_dso4.*
#           cm_xgb_dso4.png     cm_lgbm_dso4.png    cm_rf_dso4.png
#           cm_lstm_dso4.png    cm_tabnet_dso4.png
#           cm_all_dso4.png     dashboard_dso4.png
#           shap_lgbm_dso4.json shap_dso4.png
#           results_dso4.json

import os
import gc
import json
import pickle
import subprocess
import sys
import warnings

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from lightgbm import LGBMClassifier
import lightgbm as lgb
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)
from sklearn.utils.class_weight import compute_class_weight
from xgboost import XGBClassifier

warnings.filterwarnings("ignore")

# â”€â”€ Colour palette (matches DSO1 / DSO3) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
BLUE   = "#4FC3F7"
GREEN  = "#69F0AE"
ORANGE = "#FFB74D"
RED    = "#EF5350"
PURPLE = "#CE93D8"

EXPERIMENT_NAME = "DSO4-HO-Type"

# 8 handover types per 3GPP TR 38.300 (NB2 FE-2 mapping)
HO_TYPE_NAMES = [
    "no_handover",
    "intra_freq",
    "inter_freq",
    "inter_RAT_NR",
    "inter_operator",
    "intra_freq_pci",
    "inter_freq_pci",
    "ho_non_type",
]

HO_TYPE_MAPPING = {name: i for i, name in enumerate(HO_TYPE_NAMES)}

# â”€â”€ Plot style (dark theme, non-interactive) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
plt.rcParams.update({
    "figure.facecolor": "#0F1117", "axes.facecolor": "#1A1D27",
    "axes.edgecolor":  "#3A3D4D",  "axes.labelcolor": "#E0E0E0",
    "axes.titlecolor": "#FFFFFF",  "xtick.color":     "#B0B0B0",
    "ytick.color":     "#B0B0B0",  "text.color":      "#E0E0E0",
    "grid.color":      "#2A2D3A",  "grid.linestyle":  "--",
    "grid.alpha":       0.5,       "font.family":     "monospace",
    "figure.dpi":       130,
})


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Helpers
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _load_data(pt_out_dir: str, fe_out_dir: str):
    """
    Load and prepare data for DSO4.

    Steps:
      1. Read ho_type + handover labels from df_final_fe.parquet (NB2 output).
      2. Re-encode ho_type string â†’ int using HO_TYPE_MAPPING (NB3 PT-3).
      3. Filter rows where handover == 1.
      4. Load feature matrix from df_preprocessed.parquet (NB3 output).
      5. Remap active class indices to [0, N_CLASSES-1].
      6. Temporal 70 / 15 / 15 split (preserves time order â€” no shuffle).
      7. Compute balanced class weights for imbalance handling.
    """
    # â”€â”€ Labels â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print("Chargement labels depuis df_final_fe.parquet...")
    df_labels = pd.read_parquet(
        os.path.join(fe_out_dir, "df_final_fe.parquet"),
        columns=["handover", "ho_type"],
    )

    df_labels["ho_type_enc"] = (
        df_labels["ho_type"]
        .map(HO_TYPE_MAPPING)
        .fillna(-1)
        .astype(int)
    )
    print("ho_type_enc recree depuis ho_type")

    # â”€â”€ Features â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print("\nChargement df_preprocessed.parquet...")
    with open(os.path.join(pt_out_dir, "config.json")) as fh:
        config = json.load(fh)

    COLS_X = [
        c for c in config["cols_X"]
        if c not in ["handover", "ho_type_enc", "ho_type"]
    ]

    print("Verifications config NB3:")
    print(f"  cluster_id dans COLS_X : {'cluster_id' in COLS_X}")
    print(f"  has_no_leakage         : {config.get('has_no_leakage', '?')}")
    print(f"  Total features         : {len(COLS_X)}")
    assert "cluster_id" in COLS_X, \
        " cluster_id absent! Relancer NB3 corrige."

    df = pd.read_parquet(
        os.path.join(pt_out_dir, "df_preprocessed.parquet"),
        columns=COLS_X,
    )

    # Attach labels (aligned by positional index)
    df["handover"]    = df_labels["handover"].values
    df["ho_type_enc"] = df_labels["ho_type_enc"].values
    gc.collect()

    # â”€â”€ Filter: handover events only â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    df_ho4 = df[df["handover"] == 1].copy()
    print(f"\nHandovers retenus : {len(df_ho4):,}")

    ho_dist = df_ho4["ho_type_enc"].value_counts().sort_index()
    for enc, cnt in ho_dist.items():
        name = (HO_TYPE_NAMES[int(enc)]
                if 0 <= int(enc) < len(HO_TYPE_NAMES)
                else f"type_{enc}")
        print(f"  {name:<20}: {cnt:>8,} ({cnt / len(df_ho4) * 100:.1f}%)")

    # â”€â”€ Feature / label arrays â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    ci_mode = os.environ.get("CI", "false").lower() == "true"
    if ci_mode:
        import pyarrow.parquet as pq
        pf = pq.ParquetFile(os.path.join(pt_out_dir, "df_preprocessed.parquet"))
        df_ci = pf.read_row_group(0).to_pandas()
        df_ho4 = df_ci[df_ci["handover"] == 1].copy()
        print(f"  CI mode: {len(df_ho4):,} HO rows")
    X_all = df_ho4[COLS_X].values.astype(np.float32)
    y_raw = df_ho4["ho_type_enc"].values.astype(int)
    del df, df_ho4, df_labels

    # Remap to [0, N_CLASSES-1] to satisfy XGBoost / LGBM / TF requirements
    unique_classes = np.unique(y_raw)
    remap          = {old: new for new, old in enumerate(unique_classes)}
    y_all          = np.array([remap[y] for y in y_raw])
    N_CLASSES      = len(unique_classes)
    CLASS_NAMES    = [
        HO_TYPE_NAMES[int(c)] if 0 <= int(c) < len(HO_TYPE_NAMES)
        else f"type_{c}"
        for c in unique_classes
    ]

    # â”€â”€ Temporal 70 / 15 / 15 split (no shuffle â€” time series) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    n    = len(X_all)
    n_tr = int(n * 0.70)
    n_va = int(n * 0.15)

    X_train, y_train = X_all[:n_tr],          y_all[:n_tr]
    X_val,   y_val   = X_all[n_tr:n_tr+n_va], y_all[n_tr:n_tr+n_va]
    X_test,  y_test  = X_all[n_tr+n_va:],     y_all[n_tr+n_va:]
    del X_all, y_all

    # â”€â”€ Balanced class weights â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    cw_arr  = compute_class_weight(
        "balanced", classes=np.arange(N_CLASSES), y=y_train
    )
    cw_dict = {i: float(cw_arr[i]) for i in range(N_CLASSES)}

    print(f"\nN_CLASSES = {N_CLASSES}")
    print(f"Classes   = {CLASS_NAMES}")
    print(f"Train={len(X_train):,} | Val={len(X_val):,} | Test={len(X_test):,}")
    print(f"X_train {X_train.shape}")

    return (X_train, X_val, X_test,
            y_train, y_val,  y_test,
            COLS_X, N_CLASSES, CLASS_NAMES, cw_dict)


def _save_cm_pct(cm, cm_pct, title, path, class_names, cmap):
    """Save a percentage-normalised confusion matrix (8 Ã— 8 for DSO4)."""
    fig, ax = plt.subplots(figsize=(11, 8))
    sns.heatmap(
        cm_pct, annot=True, fmt=".1f", cmap=cmap,
        xticklabels=class_names, yticklabels=class_names,
        linewidths=0.4, ax=ax,
        annot_kws={"size": 9, "weight": "bold"},
        vmin=0, vmax=100,
    )
    ax.set_xlabel("Predit", fontsize=11)
    ax.set_ylabel("Reel",   fontsize=11)
    ax.tick_params(axis="x", rotation=35, labelsize=8)
    ax.tick_params(axis="y", rotation=0,  labelsize=8)
    ax.set_title(title, fontsize=12, fontweight="bold")
    plt.tight_layout()
    plt.savefig(path, bbox_inches="tight", facecolor="#0F1117")
    plt.close(fig)
    diag_mean = np.diag(cm_pct).mean()
    print(f"  Precision moy. par type HO: {diag_mean:.1f}%")


def _metrics_multiclass(name, y_true, y_pred):
    return {
        "model":       name,
        "accuracy":    round(accuracy_score(y_true, y_pred), 4),
        "f1_macro":    round(f1_score(y_true, y_pred, average="macro",
                                      zero_division=0), 4),
        "f1_weighted": round(f1_score(y_true, y_pred, average="weighted",
                                      zero_division=0), 4),
    }


def _cm_and_pct(y_true, y_pred, n_classes):
    cm     = confusion_matrix(y_true, y_pred, labels=list(range(n_classes)))
    cm_pct = cm.astype("float") / (cm.sum(axis=1, keepdims=True) + 1e-9) * 100
    return cm, cm_pct


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Main training function
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def train_dso4(
    pt_out_dir:    str  = "PT_output",
    fe_out_dir:    str  = "FE_output",
    model_out_dir: str  = os.path.join("MODEL_output", "DSO4"),
    skip_deep:     bool = False,
):
    """
    Train five models (XGBoost, LightGBM, RandomForest, BiLSTM, TabNet)
    to predict the *type* of handover for each HO event.

    Args:
        pt_out_dir:    path to NB3 preprocessing output (parquet + config.json).
        fe_out_dir:    path to NB2 feature-engineering output (df_final_fe.parquet).
        model_out_dir: where to save models, plots and JSON results.
        skip_deep:     if True, skip BiLSTM and TabNet (useful for CI/fast runs).
    """
    os.makedirs(model_out_dir, exist_ok=True)
    assert os.path.exists(pt_out_dir), \
        f"{pt_out_dir} not found â€” run NB3 preprocessing first!"
    assert os.path.exists(fe_out_dir), \
        f"{fe_out_dir} not found â€” run NB2 feature_engineering first!"

    # Optional MLflow
    try:
        from mlflow_utils import log_model_run
        mlflow_available = True
    except Exception:
        mlflow_available = False
        print("  [MLflow] Not available, skipping logging.")

    tags = {
        "dso":       "DSO4",
        "task":      "multiclass_ho_type",
        "skip_deep": str(skip_deep),
    }

    (X_train, X_val, X_test,
     y_train, y_val, y_test,
     COLS_X, N_CLASSES, CLASS_NAMES, cw_dict) = _load_data(
        pt_out_dir, fe_out_dir
    )

    # sample_weight vector from cw_dict (used by XGBoost which has no
    # class_weight param in multiclass mode)
    sw_train = np.array(
        [cw_dict[y] for y in y_train], dtype=np.float32
    )

    all_metrics = []

    # â”€â”€ M1 : XGBoost â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print("=" * 60 + "\n  M1 â€” XGBoost DSO4\n" + "=" * 60)

    xgb_params = dict(
        n_estimators=400, max_depth=7, learning_rate=0.08,
        subsample=0.8, colsample_bytree=0.8,
        objective="multi:softmax", num_class=N_CLASSES,
        eval_metric="mlogloss", early_stopping_rounds=25,
        tree_method="hist", random_state=42, n_jobs=-1,
        use_label_encoder=False,
    )
    xgb_d4 = XGBClassifier(**xgb_params)
    xgb_d4.fit(
        X_train, y_train,
        sample_weight=sw_train,
        eval_set=[(X_val, y_val)], verbose=40,
    )
    print(f" best_iteration={xgb_d4.best_iteration}")

    y_pred_xgb  = xgb_d4.predict(X_test)
    xgb_d4.predict_proba(X_test)
    print(classification_report(
        y_test, y_pred_xgb, target_names=CLASS_NAMES, zero_division=0
    ))

    metrics_xgb = _metrics_multiclass("XGBoost", y_test, y_pred_xgb)
    print(f"  XGBoost Acc={metrics_xgb['accuracy']} "
          f"F1-macro={metrics_xgb['f1_macro']}")
    all_metrics.append(metrics_xgb)

    pkl_xgb = os.path.join(model_out_dir, "xgb_dso4.pkl")
    with open(pkl_xgb, "wb") as fh:
        pickle.dump(xgb_d4, fh)
    print(" xgb_dso4.pkl sauvegarde")

    cm_xgb, cm_xgb_pct = _cm_and_pct(y_test, y_pred_xgb, N_CLASSES)
    cm_xgb_path = os.path.join(model_out_dir, "cm_xgb_dso4.png")
    _save_cm_pct(
        cm_xgb, cm_xgb_pct,
        (f" Matrice de Confusion (%) â€” XGBoost (DSO4)\n"
         f"Acc={metrics_xgb['accuracy']*100:.2f}% "
         f"F1-macro={metrics_xgb['f1_macro']*100:.2f}%"),
        cm_xgb_path, CLASS_NAMES, "Blues",
    )

    if mlflow_available:
        log_model_run(EXPERIMENT_NAME, "XGBoost", xgb_params,
                      {k: v for k, v in metrics_xgb.items() if k != "model"},
                      [cm_xgb_path, pkl_xgb], tags)

    # â”€â”€ M2 : LightGBM â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print("=" * 60 + "\n  M2 â€” LightGBM DSO4\n" + "=" * 60)

    lgbm_params = dict(
        n_estimators=400, max_depth=8, learning_rate=0.08,
        num_leaves=127, subsample=0.8, colsample_bytree=0.8,
        objective="multiclass", num_class=N_CLASSES,
        metric="multi_logloss", class_weight="balanced",
        random_state=42, n_jobs=-1, verbose=-1,
    )
    lgbm_d4 = LGBMClassifier(**lgbm_params)
    lgbm_d4.fit(
        X_train, y_train,
        eval_set=[(X_val, y_val)],
        callbacks=[
            lgb.early_stopping(25, verbose=False),
            lgb.log_evaluation(40),
        ],
    )
    print(" LightGBM entraine")

    y_pred_lgbm  = lgbm_d4.predict(X_test)
    lgbm_d4.predict_proba(X_test)
    print(classification_report(
        y_test, y_pred_lgbm, target_names=CLASS_NAMES, zero_division=0
    ))

    metrics_lgbm = _metrics_multiclass("LightGBM", y_test, y_pred_lgbm)
    print(f"  LightGBM Acc={metrics_lgbm['accuracy']} "
          f"F1-macro={metrics_lgbm['f1_macro']}")
    all_metrics.append(metrics_lgbm)

    pkl_lgbm = os.path.join(model_out_dir, "lgbm_dso4.pkl")
    with open(pkl_lgbm, "wb") as fh:
        pickle.dump(lgbm_d4, fh)
    print(" lgbm_dso4.pkl sauvegarde")

    cm_lgbm, cm_lgbm_pct = _cm_and_pct(y_test, y_pred_lgbm, N_CLASSES)
    cm_lgbm_path = os.path.join(model_out_dir, "cm_lgbm_dso4.png")
    _save_cm_pct(
        cm_lgbm, cm_lgbm_pct,
        (f" Matrice de Confusion (%) â€” LightGBM (DSO4)\n"
         f"Acc={metrics_lgbm['accuracy']*100:.2f}% "
         f"F1-macro={metrics_lgbm['f1_macro']*100:.2f}%"),
        cm_lgbm_path, CLASS_NAMES, "Greens",
    )

    if mlflow_available:
        log_model_run(EXPERIMENT_NAME, "LightGBM", lgbm_params,
                      {k: v for k, v in metrics_lgbm.items() if k != "model"},
                      [cm_lgbm_path, pkl_lgbm], tags)

    # â”€â”€ M3 : Random Forest â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print("=" * 60 + "\n  M3 â€” Random Forest DSO4\n" + "=" * 60)

    rf_params = dict(
        n_estimators=250, max_depth=18, min_samples_leaf=5,
        max_features="sqrt", class_weight="balanced_subsample",
        max_samples=0.4, random_state=42, n_jobs=-1, verbose=1,
    )
    rf_d4 = RandomForestClassifier(**rf_params)
    rf_d4.fit(X_train, y_train)
    print(" Random Forest entraine")

    y_pred_rf  = rf_d4.predict(X_test)
    rf_d4.predict_proba(X_test)
    print(classification_report(
        y_test, y_pred_rf, target_names=CLASS_NAMES, zero_division=0
    ))

    metrics_rf = _metrics_multiclass("Random Forest", y_test, y_pred_rf)
    print(f"  RF Acc={metrics_rf['accuracy']} "
          f"F1-macro={metrics_rf['f1_macro']}")
    all_metrics.append(metrics_rf)

    pkl_rf = os.path.join(model_out_dir, "rf_dso4.pkl")
    with open(pkl_rf, "wb") as fh:
        pickle.dump(rf_d4, fh)
    print(" rf_dso4.pkl sauvegarde")

    cm_rf, cm_rf_pct = _cm_and_pct(y_test, y_pred_rf, N_CLASSES)
    cm_rf_path = os.path.join(model_out_dir, "cm_rf_dso4.png")
    _save_cm_pct(
        cm_rf, cm_rf_pct,
        (f" Matrice de Confusion (%) â€” Random Forest (DSO4)\n"
         f"Acc={metrics_rf['accuracy']*100:.2f}% "
         f"F1-macro={metrics_rf['f1_macro']*100:.2f}%"),
        cm_rf_path, CLASS_NAMES, "Oranges",
    )

    if mlflow_available:
        log_model_run(EXPERIMENT_NAME, "RandomForest", rf_params,
                      {k: v for k, v in metrics_rf.items() if k != "model"},
                      [cm_rf_path, pkl_rf], tags)

    # â”€â”€ M4 : BiLSTM Softmax â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    if not skip_deep:
        print("=" * 60 + "\n  M4 â€” BiLSTM DSO4\n" + "=" * 60)

        import tensorflow as tf
        from tensorflow.keras.callbacks import (
            EarlyStopping, ModelCheckpoint, ReduceLROnPlateau,
        )
        from tensorflow.keras.layers import (
            Bidirectional, BatchNormalization, Dense, Dropout, Input, LSTM,
        )
        from tensorflow.keras.models import Model as KModel
        from tensorflow.keras.optimizers import Adam
        from tensorflow.keras.utils import to_categorical

        # BUG FIX: '_t-{k}' â†’ '_T{k}' (NB2 column format)
        WINDOW_COLS = [
            c for c in COLS_X
            if any(f"_T{k}" in c for k in range(1, 6))
        ]
        print(f"  WINDOW_COLS: {len(WINDOW_COLS)} colonnes")
        print(f"  cluster_id dans WINDOW_COLS: {'cluster_id' in WINDOW_COLS}")
        print("  â†’ Normal: cluster_id est statique, pas temporel")

        T = 5 if WINDOW_COLS else 1
        if WINDOW_COLS:
            w_idx   = [list(COLS_X).index(c) for c in WINDOW_COLS]
            F       = len(w_idx) // T
            X_tr_3d = X_train[:, w_idx].reshape(-1, T, F)
            X_va_3d = X_val[:,   w_idx].reshape(-1, T, F)
            X_te_3d = X_test[:,  w_idx].reshape(-1, T, F)
        else:
            print("  WINDOW_COLS vide â†’ fallback T=1")
            F       = X_train.shape[1]
            T       = 1
            X_tr_3d = X_train.reshape(-1, 1, F)
            X_va_3d = X_val.reshape(-1,   1, F)
            X_te_3d = X_test.reshape(-1,  1, F)

        print(f"  Shape 3D: {X_tr_3d.shape}")

        y_tr_cat = to_categorical(y_train, N_CLASSES)
        y_va_cat = to_categorical(y_val,   N_CLASSES)

        tf.random.set_seed(42)
        inp = Input(shape=(T, F))
        x   = Bidirectional(LSTM(128, return_sequences=True,  dropout=0.2))(inp)
        x   = BatchNormalization()(x)
        x   = Bidirectional(LSTM(64,  return_sequences=False, dropout=0.2))(x)
        x   = BatchNormalization()(x)
        x   = Dense(128, activation="relu")(x)
        x   = Dropout(0.35)(x)
        x   = Dense(64,  activation="relu")(x)
        out = Dense(N_CLASSES, activation="softmax")(x)

        lstm_d4 = KModel(inputs=inp, outputs=out, name="LSTM_DSO4")
        lstm_d4.compile(
            optimizer=Adam(1e-3),
            loss="categorical_crossentropy",
            metrics=["accuracy"],
        )

        print("\n  Entrainement BiLSTM...")
        lstm_d4.fit(
            X_tr_3d, y_tr_cat,
            validation_data=(X_va_3d, y_va_cat),
            class_weight=cw_dict,
            epochs=30, batch_size=1024, verbose=1,
            callbacks=[
                EarlyStopping(
                    monitor="val_accuracy", patience=5,
                    restore_best_weights=True, mode="max",
                ),
                ReduceLROnPlateau(
                    monitor="val_loss", factor=0.5,
                    patience=3, min_lr=1e-6,
                ),
                ModelCheckpoint(
                    os.path.join(model_out_dir, "lstm_dso4_best.h5"),
                    monitor="val_accuracy", save_best_only=True, mode="max",
                ),
            ],
        )
        print("BiLSTM entraine")

        y_proba_lstm = lstm_d4.predict(X_te_3d, batch_size=2048, verbose=0)
        y_pred_lstm  = y_proba_lstm.argmax(axis=1)
        print(classification_report(
            y_test, y_pred_lstm, target_names=CLASS_NAMES, zero_division=0
        ))

        metrics_lstm = _metrics_multiclass("BiLSTM", y_test, y_pred_lstm)
        print(f"  BiLSTM Acc={metrics_lstm['accuracy']} "
              f"F1-macro={metrics_lstm['f1_macro']}")
        all_metrics.append(metrics_lstm)

        lstm_d4.save(os.path.join(model_out_dir, "lstm_dso4.h5"))
        print(" lstm_dso4.h5 sauvegarde")

        cm_lstm, cm_lstm_pct = _cm_and_pct(y_test, y_pred_lstm, N_CLASSES)
        cm_lstm_path = os.path.join(model_out_dir, "cm_lstm_dso4.png")
        _save_cm_pct(
            cm_lstm, cm_lstm_pct,
            (f" Matrice de Confusion (%) â€” BiLSTM (DSO4)\n"
             f"Acc={metrics_lstm['accuracy']*100:.2f}% "
             f"F1-macro={metrics_lstm['f1_macro']*100:.2f}%"),
            cm_lstm_path, CLASS_NAMES, "Reds",
        )

        if mlflow_available:
            log_model_run(EXPERIMENT_NAME, "BiLSTM",
                          {"T": T, "F": F, "units": 128, "epochs": 30},
                          {k: v for k, v in metrics_lstm.items() if k != "model"},
                          [cm_lstm_path], tags)

    # â”€â”€ M5 : TabNet â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    if not skip_deep:
        print("=" * 60 + "\n  M5 â€” TabNet DSO4\n" + "=" * 60)

        import torch
        from pytorch_tabnet.tab_model import TabNetClassifier
        from pytorch_tabnet.pretraining import TabNetPretrainer

        # â”€â”€ 1. Sampling (TabNet is GPU/RAM intensive) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        N_TN       = min(100_000, len(X_train))
        idx_tn     = np.random.choice(len(X_train), N_TN, replace=False)
        X_tr_tn    = X_train[idx_tn].astype(np.float32)
        X_va_tn    = X_val.astype(np.float32)
        X_te_tn    = X_test.astype(np.float32)
        y_train_tn = y_train[idx_tn]
        print(f"Sample train: {len(X_tr_tn):,}")

        # â”€â”€ 2. Unsupervised pretraining â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        print("\nPre-entrainement TabNetPretrainer...")
        pt_d4 = TabNetPretrainer(
            n_d=16, n_a=16, n_steps=3, gamma=1.5,
            n_independent=2, n_shared=2, mask_type="entmax",
            optimizer_fn=torch.optim.Adam,
            optimizer_params={"lr": 2e-3},
            verbose=5, seed=42,
        )
        pt_d4.fit(
            X_train=X_tr_tn,
            eval_set=[X_va_tn],
            max_epochs=30, patience=5,
            batch_size=2048, virtual_batch_size=256,
            pretraining_ratio=0.5,
        )
        print("Pre-entrainement termine")

        # â”€â”€ 3. Supervised model â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        tabnet_d4 = TabNetClassifier(
            n_d=16, n_a=16, n_steps=3, gamma=1.5,
            n_independent=2, n_shared=2, mask_type="entmax",
            optimizer_fn=torch.optim.Adam,
            optimizer_params={"lr": 2e-3},
            verbose=0, seed=42,
        )

        # Mini-fit to initialise network before weight transfer
        tabnet_d4.fit(
            X_train=X_tr_tn[:512],
            y_train=y_train_tn[:512].astype(int),
            max_epochs=1, batch_size=512, virtual_batch_size=512,
        )
        tabnet_d4.load_weights_from_unsupervised(pt_d4)
        print(" Poids pretrainer transferes")

        # â”€â”€ 4. Real supervised training â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        tabnet_d4.verbose = 10
        tabnet_d4.fit(
            X_train=X_tr_tn,
            y_train=y_train_tn.astype(int),
            eval_set=[(X_va_tn, y_val.astype(int))],
            eval_metric=["accuracy"],
            max_epochs=30, patience=5,
            batch_size=2048, virtual_batch_size=256,
            weights=1,
        )
        print("TabNet entraine")

        y_pred_tn  = tabnet_d4.predict(X_te_tn)
        tabnet_d4.predict_proba(X_te_tn)
        print(classification_report(
            y_test, y_pred_tn, target_names=CLASS_NAMES, zero_division=0
        ))

        metrics_tn = _metrics_multiclass("TabNet", y_test, y_pred_tn)
        print(f"  TabNet Acc={metrics_tn['accuracy']} "
              f"F1-macro={metrics_tn['f1_macro']}")
        all_metrics.append(metrics_tn)

        tabnet_d4.save_model(os.path.join(model_out_dir, "tabnet_dso4"))
        print(" tabnet_dso4 sauvegarde")

        cm_tn, cm_tn_pct = _cm_and_pct(y_test, y_pred_tn, N_CLASSES)
        cm_tn_path = os.path.join(model_out_dir, "cm_tabnet_dso4.png")
        _save_cm_pct(
            cm_tn, cm_tn_pct,
            (f" Matrice de Confusion (%) â€” TabNet (DSO4)\n"
             f"Acc={metrics_tn['accuracy']*100:.2f}% "
             f"F1-macro={metrics_tn['f1_macro']*100:.2f}%"),
            cm_tn_path, CLASS_NAMES, "Purples",
        )

        if mlflow_available:
            log_model_run(EXPERIMENT_NAME, "TabNet",
                          {"n_d": 16, "n_a": 16, "n_steps": 3},
                          {k: v for k, v in metrics_tn.items() if k != "model"},
                          [cm_tn_path], tags)

    # â”€â”€ SHAP on LightGBM â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # LightGBM chosen as SHAP reference: native TreeExplainer support,
    # best interpretability/speed tradeoff for 8-class problems.
    print("\nCalcul SHAP sur LightGBM (reference explainability)...")
    try:
        import shap
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "shap", "-q"])
        import shap

    N_SHAP = 5_000
    idx_sh = np.random.choice(len(X_test), min(N_SHAP, len(X_test)), replace=False)
    X_shap = X_test[idx_sh]

    explainer   = shap.TreeExplainer(lgbm_d4)
    shap_values = explainer.shap_values(X_shap)

    # shap_values is a list of arrays â€” one per class. Average across classes.
    if isinstance(shap_values, list):
        sv = np.mean(np.abs(np.stack(shap_values, axis=0)), axis=0)
    else:
        sv = np.abs(shap_values)

    mean_shap = sv.mean(axis=0)
    shap_df   = pd.DataFrame({"feature": COLS_X, "shap": mean_shap}).sort_values(
        "shap", ascending=False
    )

    print("\nTop 20 features SHAP:")
    print(shap_df.head(20).to_string(index=False))

    if "cluster_id" in shap_df["feature"].values:
        rang = shap_df["feature"].tolist().index("cluster_id") + 1
        val  = shap_df[shap_df["feature"] == "cluster_id"]["shap"].values[0]
        print(f"\n   cluster_id: rang #{rang} â€” SHAP={val:.4f}")
    else:
        print("   cluster_id non trouve dans SHAP")

    shap_json_path = os.path.join(model_out_dir, "shap_lgbm_dso4.json")
    shap_df.to_json(shap_json_path, orient="records", indent=2)
    print(" shap_lgbm_dso4.json sauvegarde")

    # SHAP bar chart
    shap_plot_path = os.path.join(model_out_dir, "shap_dso4.png")
    fig, ax = plt.subplots(figsize=(10, 8))
    top20      = shap_df.head(20)
    bar_colors = [RED if f == "cluster_id" else BLUE for f in top20["feature"]]
    ax.barh(top20["feature"][::-1], top20["shap"][::-1], color=bar_colors[::-1])
    ax.set_xlabel("SHAP value (mean |importance|)", fontsize=11)
    ax.set_title(" SHAP Feature Importance â€” LightGBM DSO4",
                 fontsize=12, fontweight="bold")
    if "cluster_id" in top20["feature"].values:
        xv = top20[top20["feature"] == "cluster_id"]["shap"].values[0]
        yv = top20["feature"].tolist()[::-1].index("cluster_id")
        ax.annotate("<- cluster_id (zone NB2)", xy=(xv, yv), fontsize=9, color=RED)
    plt.tight_layout()
    plt.savefig(shap_plot_path, bbox_inches="tight", facecolor="#0F1117")
    plt.close(fig)

    # â”€â”€ All-models CM grid (1 Ã— N) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # Build list dynamically (deep models may be absent when skip_deep=True)
    models_cm = [
        ("XGBoost",       cm_xgb,  cm_xgb_pct,  y_pred_xgb,  "Blues"),
        ("LightGBM",      cm_lgbm, cm_lgbm_pct, y_pred_lgbm, "Greens"),
        ("Random Forest", cm_rf,   cm_rf_pct,   y_pred_rf,   "Oranges"),
    ]
    if not skip_deep:
        models_cm += [
            ("BiLSTM",  cm_lstm, cm_lstm_pct, y_pred_lstm, "Reds"),
            ("TabNet",  cm_tn,   cm_tn_pct,   y_pred_tn,   "Purples"),
        ]

    fig, axes = plt.subplots(1, len(models_cm),
                             figsize=(10 * len(models_cm), 8))
    if len(models_cm) == 1:
        axes = [axes]
    for ax, (name, _, cm_pct, y_pred, cmap) in zip(axes, models_cm):
        sns.heatmap(
            cm_pct, annot=True, fmt=".1f", cmap=cmap,
            xticklabels=CLASS_NAMES, yticklabels=CLASS_NAMES,
            linewidths=0.3, ax=ax,
            annot_kws={"size": 7}, cbar=False,
            vmin=0, vmax=100,
        )
        diag = np.diag(cm_pct).mean()
        ax.set_title(f"{name}\n(diag moy={diag:.1f}%)",
                     fontsize=10, fontweight="bold")
        ax.tick_params(axis="x", rotation=40, labelsize=6)
        ax.tick_params(axis="y", labelsize=6)
        ax.set_xlabel("Predit", fontsize=8)
        ax.set_ylabel("Reel",   fontsize=8)

    plt.suptitle(" Toutes les Matrices de Confusion (%) â€” DSO4 (Type HO)",
                 fontsize=14, fontweight="bold", color="white", y=1.01)
    plt.tight_layout()
    cm_all_path = os.path.join(model_out_dir, "cm_all_dso4.png")
    plt.savefig(cm_all_path, bbox_inches="tight", facecolor="#0F1117")
    plt.close(fig)

    # â”€â”€ Dashboard: Accuracy & F1-weighted per model â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    df_results  = pd.DataFrame(all_metrics).set_index("model")
    models_list = df_results.index.tolist()
    x           = np.arange(len(models_list))

    fig, ax = plt.subplots(figsize=(12, 5))
    bars1 = ax.bar(x - 0.2, df_results["accuracy"],    0.35,
                   label="Accuracy",    color=BLUE,  alpha=0.85)
    bars2 = ax.bar(x + 0.2, df_results["f1_weighted"], 0.35,
                   label="F1-weighted", color=GREEN, alpha=0.85)
    ax.set_xticks(x)
    ax.set_xticklabels(models_list, rotation=15, ha="right")
    ax.set_title(" DSO4 â€” Accuracy & F1-weighted par modele",
                 fontweight="bold")
    ax.legend()
    ax.set_ylim(0, 1.1)
    for bar in bars1:
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.01,
            f"{bar.get_height():.3f}",
            ha="center", va="bottom", fontsize=8, color="white",
        )
    for bar in bars2:
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.01,
            f"{bar.get_height():.3f}",
            ha="center", va="bottom", fontsize=8, color="white",
        )
    plt.tight_layout()
    dash_path = os.path.join(model_out_dir, "dashboard_dso4.png")
    plt.savefig(dash_path, bbox_inches="tight", facecolor="#0F1117")
    plt.close(fig)

    # â”€â”€ Summary â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print("\n=== RÃ‰SULTATS DSO4 ===")
    print(df_results.to_string())

    best = df_results["f1_macro"].idxmax()
    print(f"\n Meilleur (F1-macro) : {best} -> "
          f"{df_results.loc[best, 'f1_macro']:.4f}")

    results_enriched = {
        "models":          all_metrics,
        "best_model":      best,
        "best_accuracy":   float(df_results.loc[best, "accuracy"]),
        "best_f1_macro":   float(df_results.loc[best, "f1_macro"]),
        "best_f1_weighted":float(df_results.loc[best, "f1_weighted"]),
        "n_classes":       N_CLASSES,
        "class_names":     CLASS_NAMES,
        "n_features":      len(COLS_X),
        "has_cluster_id":  "cluster_id" in COLS_X,
        "cluster_id_rank": (
            shap_df["feature"].tolist().index("cluster_id") + 1
            if "cluster_id" in shap_df["feature"].values else -1
        ),
        "n_train":         int(len(X_train)),
        "n_test":          int(len(X_test)),
    }

    json_path = os.path.join(model_out_dir, "results_dso4.json")
    with open(json_path, "w") as fh:
        json.dump(results_enriched, fh, indent=2)

    print("\nresults_dso4.json sauvegarde")
    print(f"   best_model    : {best}")
    print(f"   best_f1_macro : {results_enriched['best_f1_macro']}")
    print(f"   n_classes     : {N_CLASSES}")
    print(f"   class_names   : {CLASS_NAMES}")
    print(f"   has_cluster_id: {results_enriched['has_cluster_id']}")
    print(f"   cluster_id rank: #{results_enriched['cluster_id_rank']}")
    print("\nDSO4 training complete")
    print("Pipeline complet : NB1 -> NB2 -> NB3 -> DSO1 -> DSO2 -> DSO3 -> DSO4")

    return results_enriched


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
if __name__ == "__main__":
    train_dso4()


