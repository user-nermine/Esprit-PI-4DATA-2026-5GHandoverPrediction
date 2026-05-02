# src/models/dso3.py
# Converted from NB4_DSO3_V2.ipynb
# Task  : Multiclass classification â€” predict next best cell (Top-N)
# Input : PT_output/df_preprocessed.parquet  +  config.json
#         FE_data/df_ho.parquet              (handover events for label)
# Output: MODEL_output/DSO3/
#           xgb_dso3.pkl        lgbm_dso3.pkl       rf_dso3.pkl
#           lstm_dso3.h5        lstm_dso3_best.h5
#           tabnet_dso3.*
#           label_encoder_cells.pkl
#           cm_xgb_dso3.png     cm_lgbm_dso3.png    cm_rf_dso3.png
#           cm_lstm_dso3.png    cm_tabnet_dso3.png
#           cm_all_dso3.png     dashboard_dso3.png
#           shap_lgbm_dso3.json shap_dso3.png
#           results_dso3.json

import os
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
import pyarrow.parquet as pq
import seaborn as sns

from lightgbm import LGBMClassifier
import lightgbm as lgb
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    top_k_accuracy_score,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.utils.class_weight import compute_class_weight
from xgboost import XGBClassifier

warnings.filterwarnings("ignore")

# -- Colour palette -----------------------------------------------------------
BLUE   = "#4FC3F7"
GREEN  = "#69F0AE"
ORANGE = "#FFB74D"
RED    = "#EF5350"
PURPLE = "#CE93D8"

EXPERIMENT_NAME = "DSO3-Next-Cell"
TOP_N_CELLS     = 50
TOP_K_EVAL      = 3
CONFIGS         = {"static": "session_id", "mobile": "device", "hbahn": "device"}

# -- Plot style ---------------------------------------------------------------
plt.rcParams.update({
    "figure.facecolor": "#0F1117", "axes.facecolor": "#1A1D27",
    "axes.edgecolor": "#3A3D4D",   "axes.labelcolor": "#E0E0E0",
    "axes.titlecolor": "#FFFFFF",  "xtick.color": "#B0B0B0",
    "ytick.color": "#B0B0B0",      "text.color": "#E0E0E0",
    "grid.color": "#2A2D3A",       "grid.linestyle": "--",
    "grid.alpha": 0.5,             "font.family": "monospace",
    "figure.dpi": 130,
})


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def _build_next_cell_label(fe_data_dir: str, model_out_dir: str):
    """
    Build next_cell multiclass label from df_ho.parquet.
    Returns df_filtered, le (LabelEncoder on top-N cells).
    """
    print("Chargement df_ho.parquet pour label next_cell...")
    df_ho = pd.read_parquet(
        os.path.join(fe_data_dir, "df_ho.parquet"),
        columns=["session_id", "device", "source_folder",
                 "cell_index", "handover"],
    )
    df_ho["next_cell"] = np.nan

    for env, cle in CONFIGS.items():
        if cle not in df_ho.columns:
            continue
        mask_env = df_ho["source_folder"] == env
        for _, grp in df_ho[mask_env].groupby(cle):
            df_ho.loc[grp.index, "next_cell"] = grp["cell_index"].shift(-1)

    df_ho_only = df_ho[df_ho["handover"] == 1].dropna(subset=["next_cell"])
    print(f"Handovers avec next_cell : {len(df_ho_only):,}")

    cell_counts = df_ho_only["next_cell"].value_counts()
    top_cells   = cell_counts.head(TOP_N_CELLS).index.tolist()
    coverage    = cell_counts.head(TOP_N_CELLS).sum() / cell_counts.sum() * 100
    print(f"Top-{TOP_N_CELLS} couvre {coverage:.1f}% des HO")

    df_filtered = df_ho_only[df_ho_only["next_cell"].isin(top_cells)].copy()

    le = LabelEncoder()
    df_filtered["next_cell_enc"] = le.fit_transform(
        df_filtered["next_cell"].astype(str)
    )
    print(f"{len(le.classes_)} classes | {len(df_filtered):,} handovers retenus")

    return df_filtered, le


def _load_data(pt_out_dir: str, fe_data_dir: str,
               model_out_dir: str, dry_run: bool = False):
    """Build label, load features, stratified split."""

    df_filtered, _le = _build_next_cell_label(fe_data_dir, model_out_dir)

    # -- Load preprocessed features -------------------------------------------
    print("\nChargement df_preprocessed.parquet...")
    with open(os.path.join(pt_out_dir, "config.json")) as fh:
        config = json.load(fh)

    pf         = pq.ParquetFile(os.path.join(pt_out_dir, "df_preprocessed.parquet"))
    schema_cols = pf.schema_arrow.names
    COLS_X      = [c for c in config["cols_X"] if c in schema_cols]

    print("Verifications:")
    print(f"  cluster_id dans COLS_X : {'cluster_id' in COLS_X}")
    print(f"  Total features         : {len(COLS_X)}")
    assert "cluster_id" in COLS_X, \
        " cluster_id absent! Relancer NB3 corrige."

    df_pre      = pd.read_parquet(
        os.path.join(pt_out_dir, "df_preprocessed.parquet"),
        columns=COLS_X,
    )
    common_idx  = df_filtered.index[df_filtered.index.isin(df_pre.index)]
    df_filtered = df_filtered.loc[common_idx]
    ci_mode = os.environ.get("CI", "false").lower() == "true"
    if ci_mode:
        import pyarrow.parquet as pq
        pf = pq.ParquetFile(os.path.join(pt_out_dir, "df_preprocessed.parquet"))
        df_pre = pf.read_row_group(0, columns=COLS_X + ["next_cell_enc"]).to_pandas()
        common_idx = df_pre.index
        print(f"  CI mode: {len(df_pre):,} rows")
    X_all = df_pre.loc[common_idx, COLS_X].values.astype(np.float32)
    y_all       = df_filtered["next_cell_enc"].values
    del df_pre

    # -- CI dry-run: slice before split ---------------------------------------
    if dry_run:
        n     = min(10_000, len(X_all))
        X_all = X_all[:n]
        y_all = y_all[:n]

    # -- Stratified split -----------------------------------------------------
    X_temp, X_test, y_temp, y_test = train_test_split(
        X_all, y_all, test_size=0.15, random_state=42, stratify=y_all
    )
    X_train, X_val, y_train, y_val = train_test_split(
        X_temp, y_temp,
        test_size=0.15 / 0.85, random_state=42, stratify=y_temp
    )
    del X_temp, y_temp

    # -- Re-encode cleanly on y_train classes ---------------------------------
    le2     = LabelEncoder()
    y_train = le2.fit_transform(y_train)

    def align_labels(y_raw, le):
        mapping = {c: i for i, c in enumerate(le.classes_)}
        return np.array([mapping.get(c, -1) for c in y_raw])

    y_val  = align_labels(y_val,  le2)
    y_test = align_labels(y_test, le2)

    mask_val  = y_val  != -1
    mask_test = y_test != -1
    X_val,  y_val  = X_val[mask_val],   y_val[mask_val]
    X_test, y_test = X_test[mask_test], y_test[mask_test]

    N_CLASSES = len(le2.classes_)
    with open(os.path.join(model_out_dir, "label_encoder_cells.pkl"), "wb") as fh:
        pickle.dump(le2, fh)

    print(f"Split stratifie | {N_CLASSES} classes")
    print(f"   train={len(X_train):,} | val={len(X_val):,} | test={len(X_test):,}")
    print(f"   X_train {X_train.shape}")

    # Labels for top-15 CM plots
    top15_cls   = pd.Series(y_test).value_counts().head(15).index.tolist()
    mask_top    = np.isin(y_test, top15_cls)
    cell_labels = [str(le2.classes_[i])[:8] for i in top15_cls]

    return (X_train, X_val, X_test,
            y_train, y_val, y_test,
            COLS_X, N_CLASSES, le2,
            top15_cls, mask_top, cell_labels)


def _save_cm_top15(cm, cm_pct, title, path, cell_labels, cmap,
                   acc, topk):
    """Save a percentage-normalised confusion matrix for top-15 cells."""
    fig, ax = plt.subplots(figsize=(12, 9))
    sns.heatmap(
        cm_pct, annot=True, fmt=".1f", cmap=cmap,
        xticklabels=cell_labels, yticklabels=cell_labels,
        linewidths=0.3, ax=ax,
        annot_kws={"size": 8}, vmin=0, vmax=100,
    )
    ax.set_xlabel("Predit", fontsize=10)
    ax.set_ylabel("Reel", fontsize=10)
    ax.tick_params(axis="x", rotation=45, labelsize=7)
    ax.tick_params(axis="y", labelsize=7)
    ax.set_title(
        f"{title}\n"
        f"Acc={acc * 100:.2f}% | Top-{TOP_K_EVAL}={topk * 100:.2f}%",
        fontsize=11, fontweight="bold",
    )
    plt.tight_layout()
    plt.savefig(path, bbox_inches="tight", facecolor="#0F1117")
    plt.close(fig)
    diag_mean = np.diag(cm_pct).mean()
    print(f"  Precision moyenne par cellule (diagonale): {diag_mean:.1f}%")


def _metrics_multiclass(name, y_true, y_pred, y_proba, n_classes):
    acc  = accuracy_score(y_true, y_pred)
    topk = top_k_accuracy_score(
        y_true, y_proba, k=TOP_K_EVAL, labels=np.arange(n_classes)
    )
    f1   = f1_score(y_true, y_pred, average="macro", zero_division=0)
    return {
        "model":                    name,
        "accuracy":                 round(acc,  4),
        f"top{TOP_K_EVAL}_acc":     round(topk, 4),
        "f1_macro":                 round(f1,   4),
    }


# -----------------------------------------------------------------------------
# Main training function
# -----------------------------------------------------------------------------

def train_dso3(
    pt_out_dir:    str  = "PT_output",
    fe_data_dir:   str  = "FE_data",
    model_out_dir: str  = os.path.join("MODEL_output", "DSO3"),
    skip_deep:     bool = False,
):
    os.makedirs(model_out_dir, exist_ok=True)
    assert os.path.exists(pt_out_dir), \
        f"{pt_out_dir} not found â€” run preprocessing first!"
    assert os.path.exists(fe_data_dir), \
        f"{fe_data_dir} not found â€” run feature_engineering first!"

    # Optional MLflow
    try:
        from mlflow_utils import log_model_run
        mlflow_available = True
    except Exception:
        mlflow_available = False
        print("  [MLflow] Not available, skipping logging.")

    tags = {
        "dso": "DSO3",
        "task": "multiclass_next_cell",
        "skip_deep": str(skip_deep),
    }

    (X_train, X_val, X_test,
     y_train, y_val, y_test,
     COLS_X, N_CLASSES, le2,
     top15_cls, mask_top, cell_labels) = _load_data(
        pt_out_dir, fe_data_dir, model_out_dir, dry_run=skip_deep
    )

    all_metrics = []

    # -- M1 : XGBoost ---------------------------------------------------------
    print("=" * 60 + "\n  M1 â€” XGBoost DSO3\n" + "=" * 60)

    xgb_params = dict(
        n_estimators=300, max_depth=6, learning_rate=0.1,
        subsample=0.8, colsample_bytree=0.8,
        objective="multi:softmax", num_class=N_CLASSES,
        eval_metric="mlogloss", early_stopping_rounds=20,
        tree_method="hist", random_state=42, n_jobs=-1,
        use_label_encoder=False,
    )
    xgb_d3 = XGBClassifier(**xgb_params)
    xgb_d3.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=30)

    y_pred_xgb  = xgb_d3.predict(X_test)
    y_proba_xgb = xgb_d3.predict_proba(X_test)

    metrics_xgb = _metrics_multiclass(
        "XGBoost", y_test, y_pred_xgb, y_proba_xgb, N_CLASSES
    )
    print(f"  Acc={metrics_xgb['accuracy']:.4f} | "
          f"Top-{TOP_K_EVAL}={metrics_xgb[f'top{TOP_K_EVAL}_acc']:.4f} | "
          f"F1={metrics_xgb['f1_macro']:.4f}")
    all_metrics.append(metrics_xgb)

    pkl_xgb = os.path.join(model_out_dir, "xgb_dso3.pkl")
    with open(pkl_xgb, "wb") as fh:
        pickle.dump(xgb_d3, fh)
    print(" xgb_dso3.pkl sauvegarde")

    cm_xgb = confusion_matrix(
        y_test[mask_top], y_pred_xgb[mask_top], labels=top15_cls
    )
    cm_xgb_pct = cm_xgb.astype("float") / (
        cm_xgb.sum(axis=1, keepdims=True) + 1e-9
    ) * 100
    cm_xgb_path = os.path.join(model_out_dir, "cm_xgb_dso3.png")
    _save_cm_top15(
        cm_xgb, cm_xgb_pct,
        " Matrice de Confusion (%) â€” XGBoost DSO3 (Top-15 cellules)",
        cm_xgb_path, cell_labels, "Blues",
        metrics_xgb["accuracy"], metrics_xgb[f"top{TOP_K_EVAL}_acc"],
    )

    if mlflow_available:
        log_model_run(EXPERIMENT_NAME, "XGBoost", xgb_params,
                      {k: v for k, v in metrics_xgb.items() if k != "model"},
                      [cm_xgb_path, pkl_xgb], tags)

    # -- M2 : LightGBM --------------------------------------------------------
    print("=" * 60 + "\n  M2 â€” LightGBM DSO3\n" + "=" * 60)

    lgbm_params = dict(
        n_estimators=300, max_depth=7, learning_rate=0.1,
        num_leaves=63, subsample=0.8, colsample_bytree=0.8,
        objective="multiclass", num_class=N_CLASSES,
        metric="multi_logloss", class_weight="balanced",
        random_state=42, n_jobs=-1, verbose=-1,
    )
    lgbm_d3 = LGBMClassifier(**lgbm_params)
    lgbm_d3.fit(
        X_train, y_train,
        eval_set=[(X_val, y_val)],
        callbacks=[
            lgb.early_stopping(20, verbose=False),
            lgb.log_evaluation(30),
        ],
    )

    y_pred_lgbm  = lgbm_d3.predict(X_test)
    y_proba_lgbm = lgbm_d3.predict_proba(X_test)

    metrics_lgbm = _metrics_multiclass(
        "LightGBM", y_test, y_pred_lgbm, y_proba_lgbm, N_CLASSES
    )
    print(f"  Acc={metrics_lgbm['accuracy']:.4f} | "
          f"Top-{TOP_K_EVAL}={metrics_lgbm[f'top{TOP_K_EVAL}_acc']:.4f} | "
          f"F1={metrics_lgbm['f1_macro']:.4f}")
    all_metrics.append(metrics_lgbm)

    pkl_lgbm = os.path.join(model_out_dir, "lgbm_dso3.pkl")
    with open(pkl_lgbm, "wb") as fh:
        pickle.dump(lgbm_d3, fh)
    print(" lgbm_dso3.pkl sauvegarde")

    cm_lgbm = confusion_matrix(
        y_test[mask_top], y_pred_lgbm[mask_top], labels=top15_cls
    )
    cm_lgbm_pct = cm_lgbm.astype("float") / (
        cm_lgbm.sum(axis=1, keepdims=True) + 1e-9
    ) * 100
    cm_lgbm_path = os.path.join(model_out_dir, "cm_lgbm_dso3.png")
    _save_cm_top15(
        cm_lgbm, cm_lgbm_pct,
        " Matrice de Confusion (%) â€” LightGBM DSO3 (Top-15)",
        cm_lgbm_path, cell_labels, "Greens",
        metrics_lgbm["accuracy"], metrics_lgbm[f"top{TOP_K_EVAL}_acc"],
    )

    if mlflow_available:
        log_model_run(EXPERIMENT_NAME, "LightGBM", lgbm_params,
                      {k: v for k, v in metrics_lgbm.items() if k != "model"},
                      [cm_lgbm_path, pkl_lgbm], tags)

    # -- M3 : Random Forest ---------------------------------------------------
    print("=" * 60 + "\n  M3 â€” Random Forest DSO3\n" + "=" * 60)

    rf_params = dict(
        n_estimators=200, max_depth=15, min_samples_leaf=10,
        max_features="sqrt", class_weight="balanced_subsample",
        max_samples=0.3, random_state=42, n_jobs=-1, verbose=1,
    )
    rf_d3 = RandomForestClassifier(**rf_params)
    rf_d3.fit(X_train, y_train)

    y_pred_rf  = rf_d3.predict(X_test)
    y_proba_rf = rf_d3.predict_proba(X_test)

    metrics_rf = _metrics_multiclass(
        "Random Forest", y_test, y_pred_rf, y_proba_rf, N_CLASSES
    )
    print(f"  Acc={metrics_rf['accuracy']:.4f} | "
          f"Top-{TOP_K_EVAL}={metrics_rf[f'top{TOP_K_EVAL}_acc']:.4f} | "
          f"F1={metrics_rf['f1_macro']:.4f}")
    all_metrics.append(metrics_rf)

    pkl_rf = os.path.join(model_out_dir, "rf_dso3.pkl")
    with open(pkl_rf, "wb") as fh:
        pickle.dump(rf_d3, fh)
    print(" rf_dso3.pkl sauvegarde")

    cm_rf = confusion_matrix(
        y_test[mask_top], y_pred_rf[mask_top], labels=top15_cls
    )
    cm_rf_pct = cm_rf.astype("float") / (
        cm_rf.sum(axis=1, keepdims=True) + 1e-9
    ) * 100
    cm_rf_path = os.path.join(model_out_dir, "cm_rf_dso3.png")
    _save_cm_top15(
        cm_rf, cm_rf_pct,
        " Matrice de Confusion (%) â€” Random Forest DSO3 (Top-15)",
        cm_rf_path, cell_labels, "Oranges",
        metrics_rf["accuracy"], metrics_rf[f"top{TOP_K_EVAL}_acc"],
    )

    if mlflow_available:
        log_model_run(EXPERIMENT_NAME, "RandomForest", rf_params,
                      {k: v for k, v in metrics_rf.items() if k != "model"},
                      [cm_rf_path, pkl_rf], tags)

    # -- M4 : BiLSTM Softmax --------------------------------------------------
    if not skip_deep:
        print("=" * 60 + "\n  M4 â€” LSTM Softmax DSO3\n" + "=" * 60)

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

        # BUG FIX: '_t-{k}' -> '_T{k}'
        WINDOW_COLS = [
            c for c in COLS_X
            if any(f"_T{k}" in c for k in range(1, 6))
        ]
        print(f"  WINDOW_COLS: {len(WINDOW_COLS)} colonnes")

        T = 5 if WINDOW_COLS else 1
        if WINDOW_COLS:
            w_idx   = [list(COLS_X).index(c) for c in WINDOW_COLS]
            F       = len(w_idx) // T
            X_tr_3d = X_train[:, w_idx].reshape(-1, T, F)
            X_va_3d = X_val[:,   w_idx].reshape(-1, T, F)
            X_te_3d = X_test[:,  w_idx].reshape(-1, T, F)
        else:
            print("  WINDOW_COLS vide -> fallback T=1")
            F       = X_train.shape[1]
            T       = 1
            X_tr_3d = X_train.reshape(-1, 1, F)
            X_va_3d = X_val.reshape(-1,   1, F)
            X_te_3d = X_test.reshape(-1,  1, F)

        print(f"  Shape 3D: {X_tr_3d.shape}")

        y_tr_cat = to_categorical(y_train, N_CLASSES)
        y_va_cat = to_categorical(y_val,   N_CLASSES)

        cw_arr  = compute_class_weight(
            "balanced", classes=np.arange(N_CLASSES), y=y_train
        )
        cw_dict = {i: cw_arr[i] for i in range(N_CLASSES)}

        tf.random.set_seed(42)
        inp = Input(shape=(T, F))
        x   = Bidirectional(LSTM(128, return_sequences=True, dropout=0.2))(inp)
        x   = BatchNormalization()(x)
        x   = Bidirectional(LSTM(64, return_sequences=False, dropout=0.2))(x)
        x   = BatchNormalization()(x)
        x   = Dense(128, activation="relu")(x)
        x   = Dropout(0.3)(x)
        x   = Dense(64, activation="relu")(x)
        out = Dense(N_CLASSES, activation="softmax")(x)

        lstm_d3 = KModel(inputs=inp, outputs=out, name="LSTM_DSO3")
        lstm_d3.compile(
            optimizer=Adam(1e-3),
            loss="categorical_crossentropy",
            metrics=[
                "accuracy",
                tf.keras.metrics.TopKCategoricalAccuracy(k=TOP_K_EVAL),
            ],
        )

        lstm_d3.fit(
            X_tr_3d, y_tr_cat,
            validation_data=(X_va_3d, y_va_cat),
            class_weight=cw_dict,
            epochs=30, batch_size=1024, verbose=1,
            callbacks=[
                EarlyStopping(monitor="val_accuracy", patience=5,
                              restore_best_weights=True, mode="max"),
                ReduceLROnPlateau(monitor="val_loss", factor=0.5,
                                  patience=3, min_lr=1e-6),
                ModelCheckpoint(
                    os.path.join(model_out_dir, "lstm_dso3_best.h5"),
                    monitor="val_accuracy", save_best_only=True, mode="max",
                ),
            ],
        )

        y_proba_lstm = lstm_d3.predict(X_te_3d, batch_size=2048, verbose=0)
        y_pred_lstm  = y_proba_lstm.argmax(axis=1)

        metrics_lstm = _metrics_multiclass(
            "BiLSTM", y_test, y_pred_lstm, y_proba_lstm, N_CLASSES
        )
        print(f"  Acc={metrics_lstm['accuracy']:.4f} | "
              f"Top-{TOP_K_EVAL}={metrics_lstm[f'top{TOP_K_EVAL}_acc']:.4f} | "
              f"F1={metrics_lstm['f1_macro']:.4f}")
        all_metrics.append(metrics_lstm)

        lstm_d3.save(os.path.join(model_out_dir, "lstm_dso3.h5"))
        print(" lstm_dso3.h5 sauvegarde")

        cm_lstm = confusion_matrix(
            y_test[mask_top], y_pred_lstm[mask_top], labels=top15_cls
        )
        cm_lstm_pct = cm_lstm.astype("float") / (
            cm_lstm.sum(axis=1, keepdims=True) + 1e-9
        ) * 100
        cm_lstm_path = os.path.join(model_out_dir, "cm_lstm_dso3.png")
        _save_cm_top15(
            cm_lstm, cm_lstm_pct,
            " Matrice de Confusion (%) â€” BiLSTM DSO3 (Top-15)",
            cm_lstm_path, cell_labels, "Reds",
            metrics_lstm["accuracy"], metrics_lstm[f"top{TOP_K_EVAL}_acc"],
        )

        if mlflow_available:
            log_model_run(EXPERIMENT_NAME, "BiLSTM",
                          {"T": T, "F": F, "units": 128},
                          {k: v for k, v in metrics_lstm.items() if k != "model"},
                          [cm_lstm_path], tags)

    # -- M5 : TabNet ----------------------------------------------------------
    if not skip_deep:
        print("=" * 60 + "\n  M5 â€” TabNet DSO3\n" + "=" * 60)

        import torch
        from pytorch_tabnet.tab_model import TabNetClassifier
        from pytorch_tabnet.pretraining import TabNetPretrainer

        N_TN       = min(100_000, len(X_train))
        idx_tn     = np.random.choice(len(X_train), N_TN, replace=False)
        X_tr_tn    = X_train[idx_tn].astype(np.float32)
        X_va_tn    = X_val.astype(np.float32)
        X_te_tn    = X_test.astype(np.float32)
        y_train_tn = y_train[idx_tn]
        print(f"Sample train: {len(X_tr_tn):,}")

        # 1. Pretraining
        pt_d3 = TabNetPretrainer(
            n_d=16, n_a=16, n_steps=3, gamma=1.5,
            n_independent=2, n_shared=2, mask_type="entmax",
            optimizer_fn=torch.optim.Adam,
            optimizer_params={"lr": 2e-3},
            verbose=5, seed=42,
        )
        pt_d3.fit(
            X_train=X_tr_tn, eval_set=[X_va_tn],
            max_epochs=30, patience=5,
            batch_size=2048, virtual_batch_size=256,
            pretraining_ratio=0.5,
        )

        # 2. Supervised model
        tabnet_d3 = TabNetClassifier(
            n_d=16, n_a=16, n_steps=3, gamma=1.5,
            n_independent=2, n_shared=2, mask_type="entmax",
            optimizer_fn=torch.optim.Adam,
            optimizer_params={"lr": 2e-3},
            verbose=0, seed=42,
        )
        tabnet_d3.fit(
            X_train=X_tr_tn[:512],
            y_train=y_train_tn[:512].astype(int),
            max_epochs=1, batch_size=512, virtual_batch_size=512,
        )
        tabnet_d3.load_weights_from_unsupervised(pt_d3)
        print(" Poids pretrainer transferes")

        # 3. Real supervised training
        tabnet_d3.verbose = 10
        tabnet_d3.fit(
            X_train=X_tr_tn,
            y_train=y_train_tn.astype(int),
            eval_set=[(X_va_tn, y_val.astype(int))],
            eval_metric=["accuracy"],
            max_epochs=30, patience=5,
            batch_size=2048, virtual_batch_size=256,
            weights=1,
        )
        print("TabNet entraine")

        y_pred_tn  = tabnet_d3.predict(X_te_tn)
        y_proba_tn = tabnet_d3.predict_proba(X_te_tn)

        metrics_tn = _metrics_multiclass(
            "TabNet", y_test, y_pred_tn, y_proba_tn, N_CLASSES
        )
        print(f"  Acc={metrics_tn['accuracy']:.4f} | "
              f"Top-{TOP_K_EVAL}={metrics_tn[f'top{TOP_K_EVAL}_acc']:.4f} | "
              f"F1={metrics_tn['f1_macro']:.4f}")
        all_metrics.append(metrics_tn)

        tabnet_d3.save_model(os.path.join(model_out_dir, "tabnet_dso3"))
        print(" tabnet_dso3 sauvegarde")

        cm_tn = confusion_matrix(
            y_test[mask_top], y_pred_tn[mask_top], labels=top15_cls
        )
        cm_tn_pct = cm_tn.astype("float") / (
            cm_tn.sum(axis=1, keepdims=True) + 1e-9
        ) * 100
        cm_tn_path = os.path.join(model_out_dir, "cm_tabnet_dso3.png")
        _save_cm_top15(
            cm_tn, cm_tn_pct,
            " Matrice de Confusion (%) â€” TabNet DSO3 (Top-15)",
            cm_tn_path, cell_labels, "Purples",
            metrics_tn["accuracy"], metrics_tn[f"top{TOP_K_EVAL}_acc"],
        )

        if mlflow_available:
            log_model_run(EXPERIMENT_NAME, "TabNet",
                          {"n_d": 16, "n_a": 16, "n_steps": 3},
                          {k: v for k, v in metrics_tn.items() if k != "model"},
                          [cm_tn_path], tags)

    # -- SHAP on LightGBM -----------------------------------------------------
    print("\nCalcul SHAP sur LightGBM...")
    try:
        import shap
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "shap", "-q"])
        import shap

    N_SHAP  = 5_000
    idx_sh  = np.random.choice(len(X_test), min(N_SHAP, len(X_test)), replace=False)
    X_shap  = X_test[idx_sh]

    explainer   = shap.TreeExplainer(lgbm_d3)
    shap_values = explainer.shap_values(X_shap)
    # shap_values is a list of arrays (one per class) â€” average across classes
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

    shap_json_path = os.path.join(model_out_dir, "shap_lgbm_dso3.json")
    shap_df.to_json(shap_json_path, orient="records", indent=2)
    print(" shap_lgbm_dso3.json sauvegarde")

    shap_plot_path = os.path.join(model_out_dir, "shap_dso3.png")
    fig, ax = plt.subplots(figsize=(10, 8))
    top20      = shap_df.head(20)
    bar_colors = [RED if f == "cluster_id" else BLUE for f in top20["feature"]]
    ax.barh(top20["feature"][::-1], top20["shap"][::-1], color=bar_colors[::-1])
    ax.set_xlabel("SHAP value (mean |importance|)", fontsize=11)
    ax.set_title(" SHAP Feature Importance â€” LightGBM DSO3",
                 fontsize=12, fontweight="bold")
    if "cluster_id" in top20["feature"].values:
        xv = top20[top20["feature"] == "cluster_id"]["shap"].values[0]
        yv = top20["feature"].tolist()[::-1].index("cluster_id")
        ax.annotate("<- cluster_id (zone NB2)", xy=(xv, yv), fontsize=9, color=RED)
    plt.tight_layout()
    plt.savefig(shap_plot_path, bbox_inches="tight", facecolor="#0F1117")
    plt.close(fig)

    # -- All-models summary grid (Top-1 vs Top-K bar chart) -------------------
    df_results  = pd.DataFrame(all_metrics).set_index("model")
    models_list = df_results.index.tolist()
    x           = np.arange(len(models_list))

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.bar(x - 0.2, df_results["accuracy"], 0.35,
           label="Top-1 Accuracy", color=BLUE, alpha=0.85)
    ax.bar(x + 0.2, df_results[f"top{TOP_K_EVAL}_acc"], 0.35,
           label=f"Top-{TOP_K_EVAL} Accuracy", color=GREEN, alpha=0.85)
    ax.set_xticks(x)
    ax.set_xticklabels(models_list, rotation=15, ha="right")
    ax.set_title(
        f" DSO3 â€” Accuracy Top-1 vs Top-{TOP_K_EVAL}",
        fontweight="bold",
    )
    ax.legend()
    ax.set_ylim(0, 1.1)
    for i, (acc, topk) in enumerate(zip(
        df_results["accuracy"], df_results[f"top{TOP_K_EVAL}_acc"]
    )):
        ax.text(i - 0.2, acc  + 0.01, f"{acc:.3f}",
                ha="center", va="bottom", fontsize=8, color="white")
        ax.text(i + 0.2, topk + 0.01, f"{topk:.3f}",
                ha="center", va="bottom", fontsize=8, color="white")

    plt.tight_layout()
    dash_path = os.path.join(model_out_dir, "dashboard_dso3.png")
    plt.savefig(dash_path, bbox_inches="tight", facecolor="#0F1117")
    plt.close(fig)

    # Individual CM side-by-side (small thumbnails)
    cms = [
        ("XGBoost",       cm_xgb,  y_pred_xgb),
        ("LightGBM",      cm_lgbm, y_pred_lgbm),
        ("Random Forest", cm_rf,   y_pred_rf),
    ]
    if not skip_deep:
        cms += [
            ("BiLSTM",  cm_lstm, y_pred_lstm),
            ("TabNet",  cm_tn,   y_pred_tn),
        ]

    fig, axes = plt.subplots(1, len(cms), figsize=(6 * len(cms), 5))
    if len(cms) == 1:
        axes = [axes]
    for ax, (name, cm, y_pred) in zip(axes, cms):
        cm_pct = cm.astype("float") / (cm.sum(axis=1, keepdims=True) + 1e-9) * 100
        acc    = accuracy_score(y_test[mask_top],
                                y_pred[mask_top]) * 100
        sns.heatmap(
            cm_pct, annot=False, cmap="Blues",
            linewidths=0.2, ax=ax, cbar=False,
            vmin=0, vmax=100,
        )
        ax.set_title(f"{name}\nAcc={acc:.1f}%",
                     fontsize=9, fontweight="bold")
        ax.set_xlabel("Predit", fontsize=7)
        ax.set_ylabel("Reel", fontsize=7)
        ax.tick_params(labelsize=5)
    plt.suptitle(" Toutes les Matrices de Confusion (%) â€” DSO3 (Top-15)",
                 fontsize=12, fontweight="bold", color="white", y=1.02)
    plt.tight_layout()
    cm_all_path = os.path.join(model_out_dir, "cm_all_dso3.png")
    plt.savefig(cm_all_path, bbox_inches="tight", facecolor="#0F1117")
    plt.close(fig)

    # -- Summary --------------------------------------------------------------
    print("\n=== RÃ‰SULTATS DSO3 ===")
    print(df_results.to_string())

    best = df_results["accuracy"].idxmax()
    print(f"\n Meilleur (Accuracy) : {best} -> "
          f"{df_results.loc[best, 'accuracy']:.4f}")

    results_enriched = {
        "models":          all_metrics,
        "best_model":      best,
        "best_accuracy":   float(df_results.loc[best, "accuracy"]),
        "best_top3_acc":   float(df_results.loc[best, f"top{TOP_K_EVAL}_acc"]),
        "best_f1_macro":   float(df_results.loc[best, "f1_macro"]),
        "n_classes":       N_CLASSES,
        "top_n_cells":     TOP_N_CELLS,
        "top_k_eval":      TOP_K_EVAL,
        "n_features":      len(COLS_X),
        "has_cluster_id":  "cluster_id" in COLS_X,
        "cluster_id_rank": (
            shap_df["feature"].tolist().index("cluster_id") + 1
            if "cluster_id" in shap_df["feature"].values else -1
        ),
        "n_train":  int(len(X_train)),
        "n_test":   int(len(X_test)),
    }

    json_path = os.path.join(model_out_dir, "results_dso3.json")
    with open(json_path, "w") as fh:
        json.dump(results_enriched, fh, indent=2)

    print("\nresults_dso3.json sauvegarde")
    print(f"   best_model    : {best}")
    print(f"   best_accuracy : {results_enriched['best_accuracy']}")
    print(f"   best_top3_acc : {results_enriched['best_top3_acc']}")
    print(f"   n_classes     : {N_CLASSES}")
    print(f"   has_cluster_id: {results_enriched['has_cluster_id']}")
    print(f"   cluster_id rank: #{results_enriched['cluster_id_rank']}")
    print("\nDSO3 training complete")

    return results_enriched


# -----------------------------------------------------------------------------
if __name__ == "__main__":
    train_dso3()


