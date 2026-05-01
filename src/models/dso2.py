# src/models/dso2.py
# Converted from NB4_DSO2_v2.ipynb
# Task  : Binary classification — predict RSRP drop > 6 dBm in next 5 measures
# Input : PT_output/df_preprocessed.parquet  +  idx / y .npy  +  config.json
#         FE_output/df_final_fe.parquet       (raw RSRP for label construction)
# Output: MODEL_output/DSO2/
#           xgb_dso2.pkl        lgbm_dso2.pkl       rf_dso2.pkl
#           lstm_dso2.h5        lstm_dso2_best.h5
#           tabnet_dso2.*
#           cm_xgb_dso2_pct.png cm_lgbm_dso2_pct.png cm_rf_dso2_pct.png
#           cm_lstm_dso2_pct.png cm_tabnet_dso2_pct.png
#           cm_all_dso2.png     dashboard_dso2.png
#           shap_lgbm_dso2.json shap_dso2.png
#           results_dso2.json

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
    average_precision_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
    RocCurveDisplay,
    PrecisionRecallDisplay,
)
from xgboost import XGBClassifier

warnings.filterwarnings("ignore")

# -- Colour palette -----------------------------------------------------------
BLUE   = "#4FC3F7"
GREEN  = "#69F0AE"
ORANGE = "#FFB74D"
RED    = "#EF5350"
PURPLE = "#CE93D8"

CM_LABELS       = ["No Drop", "Drop"]
EXPERIMENT_NAME = "DSO2-RSRP-Drop"

# -- DSO2 label parameters ----------------------------------------------------
SEUIL_DBM = -6.0   # RSRP drop threshold (3GPP TS 38.331 Event A2)
HORIZON   = 5      # prediction horizon (next N measures)
CONFIGS   = {"static": "session_id", "mobile": "device", "hbahn": "device"}

# -- Plot style (dark theme, non-interactive) ---------------------------------
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

def _build_rsrp_drop_label(fe_out_dir: str) -> pd.Series:
    """
    Build rsrp_drop binary label from raw RSRP in df_final_fe.parquet.
    Must use raw RSRP (NB2 output) — NOT normalised values from NB3.
    rsrp_drop = 1  if  min(rsrp[t+1..t+5]) - rsrp[t] < -6 dBm
    """
    print("Chargement rsrp brut depuis df_final_fe.parquet...")
    df_fe = pd.read_parquet(
        os.path.join(fe_out_dir, "df_final_fe.parquet"),
        columns=["rsrp", "session_id", "source_folder", "device"],
    )
    df_fe = df_fe.reset_index(drop=True)
    df_fe["rsrp_drop"] = 0

    print(f"\nSeuil={SEUIL_DBM} dBm | Horizon={HORIZON}")
    print(f"RSRP brut: min={df_fe['rsrp'].min():.1f} max={df_fe['rsrp'].max():.1f}")

    for env, cle in CONFIGS.items():
        if cle not in df_fe.columns:
            continue
        mask_env = df_fe["source_folder"] == env
        for _, grp in df_fe[mask_env].groupby(cle):
            rsrp_v = grp["rsrp"].values
            idxs   = grp.index
            n      = len(rsrp_v)
            for i in range(n - HORIZON):
                futur = rsrp_v[i + 1: i + 1 + HORIZON]
                if (futur.min() - rsrp_v[i]) < SEUIL_DBM:
                    df_fe.at[idxs[i], "rsrp_drop"] = 1
        nd = df_fe.loc[mask_env, "rsrp_drop"].sum()
        nt = mask_env.sum()
        print(f"  {env}: {nd:,} drops ({nd / nt * 100:.1f}%)")

    total_drop = df_fe["rsrp_drop"].sum()
    total      = len(df_fe)
    ratio_drop = int((total - total_drop) / max(total_drop, 1))
    print(f"\nTOTAL {total_drop:,}/{total:,} ({total_drop / total * 100:.2f}%)")
    print(f"Ratio 1:{ratio_drop}")
    print("Label rsrp_drop cree")

    return df_fe["rsrp_drop"]


def _load_data(pt_out_dir: str, fe_out_dir: str, dry_run: bool = False):
    """Load features, indices and DSO2 label."""
    # -- Build label from raw RSRP --------------------------------------------
    rsrp_drop_series = _build_rsrp_drop_label(fe_out_dir)

    # -- Load preprocessed features -------------------------------------------
    print("\nChargement df_preprocessed.parquet...")
    import pyarrow.parquet as pq
    with open(os.path.join(pt_out_dir, "config.json")) as fh:
        config = json.load(fh)

    pf = pq.ParquetFile(os.path.join(pt_out_dir, "df_preprocessed.parquet"))
    chunks = []
    for batch in pf.iter_batches(batch_size=100_000, columns=config["cols_X"]):
        chunks.append(batch.to_pandas().astype(np.float32))
    df = pd.concat(chunks, ignore_index=True)
    gc.collect()

    # Assign label
    df["rsrp_drop"] = rsrp_drop_series.values

    # -- Load split indices ---------------------------------------------------
    idx_train = np.load(os.path.join(pt_out_dir, "idx_train.npy"), allow_pickle=True)
    idx_val   = np.load(os.path.join(pt_out_dir, "idx_val.npy"),   allow_pickle=True)
    idx_test  = np.load(os.path.join(pt_out_dir, "idx_test.npy"),  allow_pickle=True)

    # -- CI dry-run: slice to 10k rows ----------------------------------------
    if dry_run:
        n         = 10_000
        idx_train = idx_train[:n]
        idx_val   = idx_val[:int(n * 0.2)]
        idx_test  = idx_test[:int(n * 0.2)]

    COLS_X = [
        c for c in config["cols_X"]
        if c in df.columns and c != "rsrp_drop"
    ]

    print(f"Verifications:")
    print(f"  cluster_id dans COLS_X : {'cluster_id' in COLS_X}")
    print(f"  Total features         : {len(COLS_X)}")
    assert "cluster_id" in COLS_X, \
        " cluster_id absent! Relancer NB3 corrige."

    y_train = df.loc[idx_train, "rsrp_drop"].values
    y_val   = df.loc[idx_val,   "rsrp_drop"].values
    y_test  = df.loc[idx_test,  "rsrp_drop"].values

    X_train = df.loc[idx_train, COLS_X].values.astype(np.float32); gc.collect()
    X_val   = df.loc[idx_val,   COLS_X].values.astype(np.float32); gc.collect()
    X_test  = df.loc[idx_test,  COLS_X].values.astype(np.float32)
    del df; gc.collect()

    ratio = int((1 - y_train.mean()) / max(y_train.mean(), 1e-6))
    print(f"\nX_train {X_train.shape}")
    print(f"   Drop%={y_train.mean() * 100:.2f}% | ratio 1:{ratio}")
    print(f"   X_val  {X_val.shape}")
    print(f"   X_test {X_test.shape}")

    return (X_train, X_val, X_test,
            y_train, y_val, y_test,
            COLS_X, ratio,
            idx_train, idx_val, idx_test)


def _save_cm_pct(cm, title, path, labels, cmap="Blues"):
    """Save a percentage-normalised confusion matrix."""
    cm_pct = cm.astype("float") / (cm.sum(axis=1, keepdims=True) + 1e-9) * 100
    fig, ax = plt.subplots(figsize=(6, 5))
    sns.heatmap(
        cm_pct, annot=True, fmt=".2f", cmap=cmap,
        xticklabels=labels, yticklabels=labels,
        linewidths=0.5, ax=ax,
        annot_kws={"size": 14, "weight": "bold"},
        cbar_kws={"label": "%"},
        vmin=0, vmax=100,
    )
    ax.set_xlabel("Predit", fontsize=11)
    ax.set_ylabel("Reel", fontsize=11)
    ax.set_title(title, fontsize=12, fontweight="bold")
    plt.tight_layout()
    plt.savefig(path, bbox_inches="tight", facecolor="#0F1117")
    plt.close(fig)
    print(f"VN: {cm_pct[0, 0]:.2f}% | FP: {cm_pct[0, 1]:.2f}%")
    print(f"FN: {cm_pct[1, 0]:.2f}% | VP: {cm_pct[1, 1]:.2f}%")


def _metrics_binary(name, y_true, y_pred, y_prob):
    return {
        "model":     name,
        "f1":        round(f1_score(y_true, y_pred), 4),
        "precision": round(precision_score(y_true, y_pred), 4),
        "recall":    round(recall_score(y_true, y_pred), 4),
        "auc_roc":   round(roc_auc_score(y_true, y_prob), 4),
        "auc_pr":    round(average_precision_score(y_true, y_prob), 4),
    }


# -----------------------------------------------------------------------------
# Main training function
# -----------------------------------------------------------------------------

def train_dso2(
    pt_out_dir:    str  = "PT_output",
    fe_out_dir:    str  = "FE_output",
    model_out_dir: str  = os.path.join("MODEL_output", "DSO2"),
    skip_deep:     bool = False,
):
    os.makedirs(model_out_dir, exist_ok=True)
    assert os.path.exists(pt_out_dir), \
        f"{pt_out_dir} not found — run preprocessing first!"
    assert os.path.exists(fe_out_dir), \
        f"{fe_out_dir} not found — run feature_engineering first!"

    # Optional MLflow
    try:
        from mlflow_utils import log_model_run
        mlflow_available = True
    except Exception:
        mlflow_available = False
        print("  [MLflow] Not available, skipping logging.")

    tags = {
        "dso": "DSO2",
        "task": "binary_rsrp_drop",
        "skip_deep": str(skip_deep),
    }

    (X_train, X_val, X_test,
     y_train, y_val, y_test,
     COLS_X, ratio,
     idx_train, idx_val, idx_test) = _load_data(
        pt_out_dir, fe_out_dir, dry_run=skip_deep
    )

    all_metrics = []

    # -- M1 : XGBoost ---------------------------------------------------------
    print("=" * 60 + "\n  M1 — XGBoost DSO2\n" + "=" * 60)

    xgb_params = dict(
        n_estimators=500, max_depth=6, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8,
        scale_pos_weight=ratio,
        eval_metric="aucpr", early_stopping_rounds=30,
        tree_method="hist", random_state=42, n_jobs=-1,
        use_label_encoder=False,
    )
    xgb_d2 = XGBClassifier(**xgb_params)
    xgb_d2.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=50)

    y_pred_xgb = xgb_d2.predict(X_test)
    y_prob_xgb = xgb_d2.predict_proba(X_test)[:, 1]
    print(classification_report(y_test, y_pred_xgb, target_names=CM_LABELS))

    metrics_xgb = _metrics_binary("XGBoost", y_test, y_pred_xgb, y_prob_xgb)
    print(f"\n  XGBoost -> F1={metrics_xgb['f1']} AUC-PR={metrics_xgb['auc_pr']}")
    all_metrics.append(metrics_xgb)

    pkl_xgb = os.path.join(model_out_dir, "xgb_dso2.pkl")
    with open(pkl_xgb, "wb") as fh:
        pickle.dump(xgb_d2, fh)
    print(" xgb_dso2.pkl sauvegarde")

    cm_xgb      = confusion_matrix(y_test, y_pred_xgb)
    cm_xgb_path = os.path.join(model_out_dir, "cm_xgb_dso2_pct.png")
    _save_cm_pct(cm_xgb, " Matrice de Confusion (%) — XGBoost (DSO2)",
                 cm_xgb_path, CM_LABELS, "Blues")

    if mlflow_available:
        log_model_run(EXPERIMENT_NAME, "XGBoost", xgb_params,
                      {k: v for k, v in metrics_xgb.items() if k != "model"},
                      [cm_xgb_path, pkl_xgb], tags)

    # -- M2 : LightGBM --------------------------------------------------------
    print("=" * 60 + "\n  M2 — LightGBM DSO2\n" + "=" * 60)

    lgbm_params = dict(
        n_estimators=500, max_depth=7, learning_rate=0.05,
        num_leaves=63, subsample=0.8, colsample_bytree=0.8,
        is_unbalance=True, metric="average_precision",
        random_state=42, n_jobs=-1, verbose=-1,
    )
    lgbm_d2 = LGBMClassifier(**lgbm_params)
    lgbm_d2.fit(
        X_train, y_train,
        eval_set=[(X_val, y_val)],
        callbacks=[
            lgb.early_stopping(30, verbose=False),
            lgb.log_evaluation(50),
        ],
    )

    y_pred_lgbm = lgbm_d2.predict(X_test)
    y_prob_lgbm = lgbm_d2.predict_proba(X_test)[:, 1]
    print(classification_report(y_test, y_pred_lgbm, target_names=CM_LABELS))

    metrics_lgbm = _metrics_binary("LightGBM", y_test, y_pred_lgbm, y_prob_lgbm)
    print(f"\n  LightGBM -> F1={metrics_lgbm['f1']} AUC-PR={metrics_lgbm['auc_pr']}")
    all_metrics.append(metrics_lgbm)

    pkl_lgbm = os.path.join(model_out_dir, "lgbm_dso2.pkl")
    with open(pkl_lgbm, "wb") as fh:
        pickle.dump(lgbm_d2, fh)
    print(" lgbm_dso2.pkl sauvegarde")

    cm_lgbm      = confusion_matrix(y_test, y_pred_lgbm)
    cm_lgbm_path = os.path.join(model_out_dir, "cm_lgbm_dso2_pct.png")
    _save_cm_pct(cm_lgbm, " Matrice de Confusion (%) — LightGBM (DSO2)",
                 cm_lgbm_path, CM_LABELS, "Greens")

    if mlflow_available:
        log_model_run(EXPERIMENT_NAME, "LightGBM", lgbm_params,
                      {k: v for k, v in metrics_lgbm.items() if k != "model"},
                      [cm_lgbm_path, pkl_lgbm], tags)

    # -- M3 : Random Forest ---------------------------------------------------
    print("=" * 60 + "\n  M3 — Random Forest DSO2\n" + "=" * 60)

    rf_params = dict(
        n_estimators=300, max_depth=15, min_samples_leaf=20,
        max_features="sqrt", class_weight="balanced_subsample",
        max_samples=0.2, random_state=42, n_jobs=-1, verbose=1,
    )
    rf_d2 = RandomForestClassifier(**rf_params)
    rf_d2.fit(X_train, y_train)

    y_pred_rf = rf_d2.predict(X_test)
    y_prob_rf = rf_d2.predict_proba(X_test)[:, 1]
    print(classification_report(y_test, y_pred_rf, target_names=CM_LABELS))

    metrics_rf = _metrics_binary("Random Forest", y_test, y_pred_rf, y_prob_rf)
    print(f"\n  RF -> F1={metrics_rf['f1']} AUC-PR={metrics_rf['auc_pr']}")
    all_metrics.append(metrics_rf)

    pkl_rf = os.path.join(model_out_dir, "rf_dso2.pkl")
    with open(pkl_rf, "wb") as fh:
        pickle.dump(rf_d2, fh)
    print(" rf_dso2.pkl sauvegarde")

    cm_rf      = confusion_matrix(y_test, y_pred_rf)
    cm_rf_path = os.path.join(model_out_dir, "cm_rf_dso2_pct.png")
    _save_cm_pct(cm_rf, " Matrice de Confusion (%) — Random Forest (DSO2)",
                 cm_rf_path, CM_LABELS, "Oranges")

    if mlflow_available:
        log_model_run(EXPERIMENT_NAME, "RandomForest", rf_params,
                      {k: v for k, v in metrics_rf.items() if k != "model"},
                      [cm_rf_path, pkl_rf], tags)

    # -- M4 : BiLSTM ----------------------------------------------------------
    if not skip_deep:
        print("=" * 60 + "\n  M4 — BiLSTM DSO2\n" + "=" * 60)

        import tensorflow as tf
        from tensorflow.keras.callbacks import (
            EarlyStopping, ModelCheckpoint, ReduceLROnPlateau,
        )
        from tensorflow.keras.layers import (
            Bidirectional, BatchNormalization, Dense, Dropout, Input, LSTM,
        )
        from tensorflow.keras.models import Model as KModel
        from tensorflow.keras.optimizers import Adam

        # BUG FIX: '_t-{k}' -> '_T{k}' — NB2 generates rsrp_T1, rsrp_T2 ...
        WINDOW_COLS = [
            c for c in COLS_X
            if any(f"_T{k}" in c for k in range(1, 6))
        ]
        print(f"  WINDOW_COLS trouvees : {len(WINDOW_COLS)}")
        print(f"  Exemples : {WINDOW_COLS[:5]}")
        print(f"  cluster_id dans WINDOW_COLS: {'cluster_id' in WINDOW_COLS}")
        print("  -> Normal: cluster_id est statique, pas temporel")

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

        tf.random.set_seed(42)
        inp = Input(shape=(T, F))
        x   = Bidirectional(LSTM(128, return_sequences=True, dropout=0.2))(inp)
        x   = BatchNormalization()(x)
        x   = Bidirectional(LSTM(64, return_sequences=False, dropout=0.2))(x)
        x   = BatchNormalization()(x)
        x   = Dense(64, activation="relu")(x)
        x   = Dropout(0.3)(x)
        out = Dense(1, activation="sigmoid")(x)

        lstm_d2 = KModel(inputs=inp, outputs=out, name="BiLSTM_DSO2")
        lstm_d2.compile(
            optimizer=Adam(1e-3),
            loss="binary_crossentropy",
            metrics=["AUC"],
        )

        sw = np.where(y_train == 1, ratio, 1).astype(np.float32)
        lstm_d2.fit(
            X_tr_3d, y_train,
            validation_data=(X_va_3d, y_val),
            sample_weight=sw,
            epochs=30, batch_size=2048, verbose=1,
            callbacks=[
                EarlyStopping(monitor="val_AUC", patience=5,
                              restore_best_weights=True, mode="max"),
                ReduceLROnPlateau(monitor="val_loss", factor=0.5,
                                  patience=3, min_lr=1e-6),
                ModelCheckpoint(
                    os.path.join(model_out_dir, "lstm_dso2_best.h5"),
                    monitor="val_AUC", save_best_only=True, mode="max",
                ),
            ],
        )

        y_prob_lstm = lstm_d2.predict(X_te_3d, batch_size=4096, verbose=0).flatten()
        y_pred_lstm = (y_prob_lstm > 0.5).astype(int)
        print(classification_report(y_test, y_pred_lstm, target_names=CM_LABELS))

        metrics_lstm = _metrics_binary("BiLSTM", y_test, y_pred_lstm, y_prob_lstm)
        print(f"\n  BiLSTM -> F1={metrics_lstm['f1']} AUC-PR={metrics_lstm['auc_pr']}")
        all_metrics.append(metrics_lstm)

        lstm_d2.save(os.path.join(model_out_dir, "lstm_dso2.h5"))
        print(" lstm_dso2.h5 sauvegarde")

        cm_lstm      = confusion_matrix(y_test, y_pred_lstm)
        cm_lstm_path = os.path.join(model_out_dir, "cm_lstm_dso2_pct.png")
        _save_cm_pct(cm_lstm, " Matrice de Confusion (%) — BiLSTM (DSO2)",
                     cm_lstm_path, CM_LABELS, "Blues")

        if mlflow_available:
            log_model_run(EXPERIMENT_NAME, "BiLSTM",
                          {"T": T, "F": F, "units": 128},
                          {k: v for k, v in metrics_lstm.items() if k != "model"},
                          [cm_lstm_path], tags)

    # -- M5 : TabNet ----------------------------------------------------------
    if not skip_deep:
        print("=" * 60 + "\n  M5 — TabNet DSO2\n" + "=" * 60)

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
        pt_d2 = TabNetPretrainer(
            n_d=16, n_a=16, n_steps=3, gamma=1.5,
            n_independent=2, n_shared=2, mask_type="entmax",
            optimizer_fn=torch.optim.Adam,
            optimizer_params={"lr": 2e-3},
            verbose=5, seed=42,
        )
        pt_d2.fit(
            X_train=X_tr_tn, eval_set=[X_va_tn],
            max_epochs=30, patience=5,
            batch_size=2048, virtual_batch_size=256,
            pretraining_ratio=0.5,
        )

        # 2. Supervised model
        tabnet_d2 = TabNetClassifier(
            n_d=16, n_a=16, n_steps=3, gamma=1.5,
            n_independent=2, n_shared=2, mask_type="entmax",
            optimizer_fn=torch.optim.Adam,
            optimizer_params={"lr": 2e-3},
            verbose=0, seed=42,
        )
        tabnet_d2.fit(
            X_train=X_tr_tn[:512],
            y_train=y_train_tn[:512].astype(int),
            max_epochs=1, batch_size=512, virtual_batch_size=512,
        )
        tabnet_d2.load_weights_from_unsupervised(pt_d2)
        print(" Poids pretrainer transferes")

        # 3. Real supervised training
        tabnet_d2.verbose = 10
        tabnet_d2.fit(
            X_train=X_tr_tn,
            y_train=y_train_tn.astype(int),
            eval_set=[(X_va_tn, y_val.astype(int))],
            eval_metric=["auc"],
            max_epochs=30, patience=5,
            batch_size=2048, virtual_batch_size=256,
            weights=1,
        )
        print("TabNet entraine")

        y_pred_tn = tabnet_d2.predict(X_te_tn)
        y_prob_tn = tabnet_d2.predict_proba(X_te_tn)[:, 1]
        print(classification_report(y_test, y_pred_tn, target_names=CM_LABELS))

        metrics_tn = _metrics_binary("TabNet", y_test, y_pred_tn, y_prob_tn)
        print(f"\n  TabNet -> F1={metrics_tn['f1']} AUC-PR={metrics_tn['auc_pr']}")
        all_metrics.append(metrics_tn)

        tabnet_d2.save_model(os.path.join(model_out_dir, "tabnet_dso2"))
        print(" tabnet_dso2 sauvegarde")

        cm_tn      = confusion_matrix(y_test, y_pred_tn)
        cm_tn_path = os.path.join(model_out_dir, "cm_tabnet_dso2_pct.png")
        _save_cm_pct(cm_tn, " Matrice de Confusion (%) — TabNet (DSO2)",
                     cm_tn_path, CM_LABELS, "Blues")

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
    idx_sh  = np.random.choice(len(X_test), N_SHAP, replace=False)
    X_shap  = X_test[idx_sh]

    explainer   = shap.TreeExplainer(lgbm_d2)
    shap_values = explainer.shap_values(X_shap)
    sv = shap_values[1] if isinstance(shap_values, list) else shap_values

    mean_shap = np.abs(sv).mean(axis=0)
    shap_df   = pd.DataFrame({"feature": COLS_X, "shap": mean_shap}).sort_values(
        "shap", ascending=False
    )

    print("\nTop 20 features SHAP:")
    print(shap_df.head(20).to_string(index=False))

    if "cluster_id" in shap_df["feature"].values:
        rang = shap_df["feature"].tolist().index("cluster_id") + 1
        val  = shap_df[shap_df["feature"] == "cluster_id"]["shap"].values[0]
        print(f"\n   cluster_id: rang #{rang} — SHAP={val:.4f}")

    shap_json_path = os.path.join(model_out_dir, "shap_lgbm_dso2.json")
    shap_df.to_json(shap_json_path, orient="records", indent=2)
    print(" shap_lgbm_dso2.json sauvegarde")

    shap_plot_path = os.path.join(model_out_dir, "shap_dso2.png")
    fig, ax = plt.subplots(figsize=(10, 8))
    top20      = shap_df.head(20)
    bar_colors = [RED if f == "cluster_id" else BLUE for f in top20["feature"]]
    ax.barh(top20["feature"][::-1], top20["shap"][::-1], color=bar_colors[::-1])
    ax.set_xlabel("SHAP value (mean |importance|)", fontsize=11)
    ax.set_title(" SHAP Feature Importance — LightGBM DSO2",
                 fontsize=12, fontweight="bold")
    if "cluster_id" in top20["feature"].values:
        xv = top20[top20["feature"] == "cluster_id"]["shap"].values[0]
        yv = top20["feature"].tolist()[::-1].index("cluster_id")
        ax.annotate("<- cluster_id (zone NB2)", xy=(xv, yv), fontsize=9, color=RED)
    plt.tight_layout()
    plt.savefig(shap_plot_path, bbox_inches="tight", facecolor="#0F1117")
    plt.close(fig)

    # -- All confusion matrices side-by-side ----------------------------------
    models_cm = [
        ("XGBoost",       cm_xgb,  y_pred_xgb),
        ("LightGBM",      cm_lgbm, y_pred_lgbm),
        ("Random Forest", cm_rf,   y_pred_rf),
    ]
    if not skip_deep:
        models_cm += [
            ("BiLSTM",  cm_lstm, y_pred_lstm),
            ("TabNet",  cm_tn,   y_pred_tn),
        ]

    fig, axes = plt.subplots(1, len(models_cm), figsize=(6 * len(models_cm), 5))
    if len(models_cm) == 1:
        axes = [axes]
    for ax, (name, cm, y_pred) in zip(axes, models_cm):
        cm_pct = cm.astype("float") / (cm.sum(axis=1, keepdims=True) + 1e-9) * 100
        f1  = f1_score(y_test, y_pred, zero_division=0)
        acc = np.diag(cm).sum() / cm.sum() * 100
        sns.heatmap(
            cm_pct, annot=True, fmt=".1f", cmap="Blues",
            xticklabels=CM_LABELS, yticklabels=CM_LABELS,
            linewidths=0.5, ax=ax,
            annot_kws={"size": 13, "weight": "bold"},
            cbar=False, vmin=0, vmax=100,
        )
        ax.set_title(f"{name}\nAcc={acc:.1f}% F1={f1:.3f}",
                     fontsize=10, fontweight="bold")
        ax.set_xlabel("Predit")
        ax.set_ylabel("Reel")
    plt.suptitle(" Toutes les Matrices de Confusion (%) — DSO2 (RSRP Drop)",
                 fontsize=14, fontweight="bold", color="white", y=1.02)
    plt.tight_layout()
    cm_all_path = os.path.join(model_out_dir, "cm_all_dso2.png")
    plt.savefig(cm_all_path, bbox_inches="tight", facecolor="#0F1117")
    plt.close(fig)

    # -- Dashboard ROC + PR ---------------------------------------------------
    models_list = [m[0] for m in models_cm]
    probs_list  = [y_prob_xgb, y_prob_lgbm, y_prob_rf]
    if not skip_deep:
        probs_list += [y_prob_lstm, y_prob_tn]
    colors_list = [BLUE, GREEN, ORANGE, RED, PURPLE][: len(models_list)]

    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    for name, prob, color in zip(models_list, probs_list, colors_list):
        RocCurveDisplay.from_predictions(
            y_test, prob, name=name, ax=axes[0], color=color
        )
    axes[0].set_title("Courbes ROC — DSO2", fontweight="bold")
    axes[0].plot([0, 1], [0, 1], "--", color="gray", lw=0.8)

    for name, prob, color in zip(models_list, probs_list, colors_list):
        PrecisionRecallDisplay.from_predictions(
            y_test, prob, name=name, ax=axes[1], color=color
        )
    axes[1].set_title("Precision-Recall — DSO2", fontweight="bold")

    plt.suptitle(" DSO2 — Dashboard Final",
                 fontsize=14, fontweight="bold", color="white")
    plt.tight_layout()
    dash_path = os.path.join(model_out_dir, "dashboard_dso2.png")
    plt.savefig(dash_path, bbox_inches="tight", facecolor="#0F1117")
    plt.close(fig)

    # -- Summary --------------------------------------------------------------
    df_results = pd.DataFrame(all_metrics).set_index("model")
    print("\n=== RÉSULTATS DSO2 ===")
    print(df_results.to_string())

    best = df_results["f1"].idxmax()
    print(f"\n Meilleur (F1) : {best} -> {df_results.loc[best, 'f1']:.4f}")

    results_enriched = {
        "models":          all_metrics,
        "best_model":      best,
        "best_f1":         float(df_results.loc[best, "f1"]),
        "best_auc_pr":     float(df_results.loc[best, "auc_pr"]),
        "n_features":      len(COLS_X),
        "has_cluster_id":  "cluster_id" in COLS_X,
        "cluster_id_rank": (
            shap_df["feature"].tolist().index("cluster_id") + 1
            if "cluster_id" in shap_df["feature"].values else -1
        ),
        "n_train":         int(len(idx_train)),
        "n_test":          int(len(idx_test)),
        "drop_rate_test":  float(y_test.mean()),
        "seuil_dbm":       SEUIL_DBM,
        "horizon":         HORIZON,
    }

    json_path = os.path.join(model_out_dir, "results_dso2.json")
    with open(json_path, "w") as fh:
        json.dump(results_enriched, fh, indent=2)

    print("\nresults_dso2.json sauvegarde")
    print(f"   best_model    : {best}")
    print(f"   best_f1       : {results_enriched['best_f1']}")
    print(f"   has_cluster_id: {results_enriched['has_cluster_id']}")
    print(f"   cluster_id rank: #{results_enriched['cluster_id_rank']}")
    print("\nDSO2 training complete")

    return results_enriched


# -----------------------------------------------------------------------------
if __name__ == "__main__":
    train_dso2()