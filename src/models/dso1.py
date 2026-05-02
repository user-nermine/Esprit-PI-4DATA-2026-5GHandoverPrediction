# src/models/dso1.py
# Converted from NB4_DSO1_v2.ipynb
# Task  : Binary classification â€” predict handover (0 / 1)
# Input : PT_output/df_preprocessed.parquet  +  idx / y .npy  +  config.json
# Output: MODEL_output/DSO1/
#           xgb_model.pkl        lgbm_model.pkl       rf_model.pkl
#           lstm_model.h5        lstm_best.h5
#           tabnet_model.*
#           cm_xgb_dso1_pct.png  cm_lgbm_dso1_pct.png cm_rf_dso1_pct.png
#           cm_lstm_dso1_pct.png cm_tabnet_dso1_pct.png
#           cm_all_dso1.png      dashboard_dso1.png
#           shap_lgbm_dso1.json  shap_dso1.png
#           results_dso1.json

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

# â”€â”€ Colour palette (matches notebook) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
BLUE   = "#4FC3F7"
GREEN  = "#69F0AE"
ORANGE = "#FFB74D"
RED    = "#EF5350"
PURPLE = "#CE93D8"

CM_LABELS       = ["No HO", "HO"]
EXPERIMENT_NAME = "DSO1-Handover"

# â”€â”€ Plot style (dark theme, non-interactive) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
plt.rcParams.update({
    "figure.facecolor": "#0F1117", "axes.facecolor": "#1A1D27",
    "axes.edgecolor": "#3A3D4D",   "axes.labelcolor": "#E0E0E0",
    "axes.titlecolor": "#FFFFFF",  "xtick.color": "#B0B0B0",
    "ytick.color": "#B0B0B0",      "text.color": "#E0E0E0",
    "grid.color": "#2A2D3A",       "grid.linestyle": "--",
    "grid.alpha": 0.5,             "font.family": "monospace",
    "figure.dpi": 130,
})


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Helpers
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _load_data(pt_out_dir: str):
    """Load indices, labels, config and the parquet feature matrix."""
    idx_train = np.load(os.path.join(pt_out_dir, "idx_train.npy"), allow_pickle=True)
    idx_val   = np.load(os.path.join(pt_out_dir, "idx_val.npy"),   allow_pickle=True)
    idx_test  = np.load(os.path.join(pt_out_dir, "idx_test.npy"),  allow_pickle=True)
    y_train   = np.load(os.path.join(pt_out_dir, "y_train.npy"))
    y_val     = np.load(os.path.join(pt_out_dir, "y_val.npy"))
    y_test    = np.load(os.path.join(pt_out_dir, "y_test.npy"))

    with open(os.path.join(pt_out_dir, "config.json")) as fh:
        config = json.load(fh)
    cols_x = config["cols_X"]

    #  Assert cluster_id present (NB3 correction)
    print("VÃ©rifications config NB3:")
    print(f"  cluster_id dans COLS_X : {'cluster_id' in cols_x}")
    print(f"  has_no_leakage         : {config.get('has_no_leakage', '?')}")
    print(f"  Total features         : {len(cols_x)}")
    print(f"  idx cluster_id         : "
          f"{cols_x.index('cluster_id') if 'cluster_id' in cols_x else 'ABSENT'}")

    assert "cluster_id" in cols_x, \
        " cluster_id absent! Relancer NB3 corrigÃ©."

    # Load parquet (selected columns only)
    print("\nChargement df_preprocessed.parquet...")
    df = pd.read_parquet(
        os.path.join(pt_out_dir, "df_preprocessed.parquet"),
        columns=cols_x,
    )
    ci_mode = os.environ.get("CI", "false").lower() == "true"
    if ci_mode:
        df = df.iloc[:50_000]
        print(f"  CI mode: sliced to {len(df):,} rows")
    gc.collect()

    X_train = df.loc[idx_train].values.astype(np.float32)
    X_val   = df.loc[idx_val].values.astype(np.float32)
    X_test  = df.loc[idx_test].values.astype(np.float32)
    del df

    ratio = int((1 - y_train.mean()) / max(y_train.mean(), 1e-6))
    print(f"\nX_train {X_train.shape}")
    print(f"   HO%={y_train.mean() * 100:.2f}% | ratio 1:{ratio}")
    print(f"   X_val  {X_val.shape}")
    print(f"   X_test {X_test.shape}")

    return (X_train, X_val, X_test,
            y_train, y_val, y_test,
            cols_x, ratio,
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
    ax.set_xlabel("PrÃ©dit", fontsize=11)
    ax.set_ylabel("RÃ©el", fontsize=11)
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


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Main training function
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def train_dso1(
    pt_out_dir:    str  = "PT_output",
    model_out_dir: str  = os.path.join("MODEL_output", "DSO1"),
    skip_deep:     bool = False,
):
    os.makedirs(model_out_dir, exist_ok=True)
    assert os.path.exists(pt_out_dir), \
        f"{pt_out_dir} not found â€” run preprocessing first!"

    # Optional MLflow
    try:
        from mlflow_utils import log_model_run
        mlflow_available = True
    except Exception:
        mlflow_available = False
        print("  [MLflow] Not available, skipping logging.")

    tags = {
        "dso": "DSO1",
        "task": "binary_handover",
        "skip_deep": str(skip_deep),
    }

    (X_train, X_val, X_test,
     y_train, y_val, y_test,
     COLS_X, ratio,
     idx_train, idx_val, idx_test) = _load_data(pt_out_dir)

    all_metrics = []

    # â”€â”€ M1 : XGBoost â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print("=" * 60 + "\n  M1 â€” XGBoost\n" + "=" * 60)

    # cluster_id is inside X_train (NB3 corrected).
    # XGBoost handles negative integers natively (-2=static, -1=outlier, 0-204=cluster).
    xgb_params = dict(
        n_estimators=500, max_depth=6, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8,
        scale_pos_weight=ratio,
        eval_metric="aucpr", early_stopping_rounds=30,
        tree_method="hist", random_state=42, n_jobs=-1,
        use_label_encoder=False,
    )
    xgb_model = XGBClassifier(**xgb_params)
    xgb_model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=50)
    print(f" best_iteration={xgb_model.best_iteration}")

    y_pred_xgb = xgb_model.predict(X_test)
    y_prob_xgb = xgb_model.predict_proba(X_test)[:, 1]
    print(classification_report(y_test, y_pred_xgb, target_names=CM_LABELS))

    metrics_xgb = _metrics_binary("XGBoost", y_test, y_pred_xgb, y_prob_xgb)
    print(f"\n  XGBoost â†’ F1={metrics_xgb['f1']} AUC-PR={metrics_xgb['auc_pr']}")
    all_metrics.append(metrics_xgb)

    pkl_xgb = os.path.join(model_out_dir, "xgb_model.pkl")
    with open(pkl_xgb, "wb") as fh:
        pickle.dump(xgb_model, fh)
    print(" xgb_model.pkl sauvegardÃ©")

    cm_xgb = confusion_matrix(y_test, y_pred_xgb)
    cm_xgb_path = os.path.join(model_out_dir, "cm_xgb_dso1_pct.png")
    _save_cm_pct(cm_xgb, " Matrice de Confusion (%) â€” XGBoost (DSO1)",
                 cm_xgb_path, CM_LABELS, "Blues")

    if mlflow_available:
        log_model_run(EXPERIMENT_NAME, "XGBoost", xgb_params,
                      {k: v for k, v in metrics_xgb.items() if k != "model"},
                      [cm_xgb_path, pkl_xgb], tags)

    # â”€â”€ M2 : LightGBM â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print("=" * 60 + "\n  M2 â€” LightGBM\n" + "=" * 60)

    # LightGBM supports categorical features natively; cluster_id treated as int.
    lgbm_params = dict(
        n_estimators=500, max_depth=7, learning_rate=0.05,
        num_leaves=63, subsample=0.8, colsample_bytree=0.8,
        is_unbalance=True, metric="average_precision",
        random_state=42, n_jobs=-1, verbose=-1,
    )
    lgbm_model = LGBMClassifier(**lgbm_params)
    lgbm_model.fit(
        X_train, y_train,
        eval_set=[(X_val, y_val)],
        callbacks=[
            lgb.early_stopping(30, verbose=False),
            lgb.log_evaluation(50),
        ],
    )
    print(" LightGBM entraÃ®nÃ©")

    y_pred_lgbm = lgbm_model.predict(X_test)
    y_prob_lgbm = lgbm_model.predict_proba(X_test)[:, 1]
    print(classification_report(y_test, y_pred_lgbm, target_names=CM_LABELS))

    metrics_lgbm = _metrics_binary("LightGBM", y_test, y_pred_lgbm, y_prob_lgbm)
    print(f"\n  LightGBM â†’ F1={metrics_lgbm['f1']} AUC-PR={metrics_lgbm['auc_pr']}")
    all_metrics.append(metrics_lgbm)

    pkl_lgbm = os.path.join(model_out_dir, "lgbm_model.pkl")
    with open(pkl_lgbm, "wb") as fh:
        pickle.dump(lgbm_model, fh)
    print("lgbm_model.pkl sauvegardÃ©")

    cm_lgbm = confusion_matrix(y_test, y_pred_lgbm)
    cm_lgbm_path = os.path.join(model_out_dir, "cm_lgbm_dso1_pct.png")
    _save_cm_pct(cm_lgbm, " Matrice de Confusion (%) â€” LightGBM (DSO1)",
                 cm_lgbm_path, CM_LABELS, "Greens")

    if mlflow_available:
        log_model_run(EXPERIMENT_NAME, "LightGBM", lgbm_params,
                      {k: v for k, v in metrics_lgbm.items() if k != "model"},
                      [cm_lgbm_path, pkl_lgbm], tags)

    # â”€â”€ M3 : Random Forest â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print("=" * 60 + "\n  M3 â€” Random Forest\n" + "=" * 60)

    rf_params = dict(
        n_estimators=300, max_depth=15, min_samples_leaf=20,
        max_features="sqrt", class_weight="balanced_subsample",
        max_samples=0.2, random_state=42, n_jobs=-1, verbose=1,
    )
    rf_model = RandomForestClassifier(**rf_params)
    rf_model.fit(X_train, y_train)
    print(" Random Forest entraÃ®nÃ©")

    y_pred_rf = rf_model.predict(X_test)
    y_prob_rf = rf_model.predict_proba(X_test)[:, 1]
    print(classification_report(y_test, y_pred_rf, target_names=CM_LABELS))

    metrics_rf = _metrics_binary("Random Forest", y_test, y_pred_rf, y_prob_rf)
    print(f"\n  RF â†’ F1={metrics_rf['f1']} AUC-PR={metrics_rf['auc_pr']}")
    all_metrics.append(metrics_rf)

    pkl_rf = os.path.join(model_out_dir, "rf_model.pkl")
    with open(pkl_rf, "wb") as fh:
        pickle.dump(rf_model, fh)
    print(" rf_model.pkl sauvegardÃ©")

    cm_rf = confusion_matrix(y_test, y_pred_rf)
    cm_rf_path = os.path.join(model_out_dir, "cm_rf_dso1_pct.png")
    _save_cm_pct(cm_rf, " Matrice de Confusion (%) â€” Random Forest (DSO1)",
                 cm_rf_path, CM_LABELS, "Oranges")

    if mlflow_available:
        log_model_run(EXPERIMENT_NAME, "RandomForest", rf_params,
                      {k: v for k, v in metrics_rf.items() if k != "model"},
                      [cm_rf_path, pkl_rf], tags)

    # â”€â”€ M4 : BiLSTM â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    if not skip_deep:
        print("=" * 60 + "\n  M4 â€” BiLSTM\n" + "=" * 60)

        import tensorflow as tf
        from tensorflow.keras.callbacks import (
            EarlyStopping, ModelCheckpoint, ReduceLROnPlateau,
        )
        from tensorflow.keras.layers import (
            Bidirectional, BatchNormalization, Dense, Dropout, Input, LSTM,
        )
        from tensorflow.keras.models import Model as KModel
        from tensorflow.keras.optimizers import Adam

        #  BUG FIX: '_t-{k}' â†’ '_T{k}' â€” NB2 generates rsrp_T1, rsrp_T2 ...
        WINDOW_COLS = [
            c for c in COLS_X
            if any(f"_T{k}" in c for k in range(1, 6))
        ]
        print(f"  WINDOW_COLS trouvÃ©es : {len(WINDOW_COLS)}")
        print(f"  Exemples : {WINDOW_COLS[:5]}")
        # cluster_id is NOT in WINDOW_COLS â€” it is static (not temporal)
        print(f"  cluster_id dans WINDOW_COLS: {'cluster_id' in WINDOW_COLS}")
        print("  â†’ Normal: cluster_id est statique, pas temporel")

        T = 5 if WINDOW_COLS else 1

        if WINDOW_COLS:
            w_idx   = [list(COLS_X).index(c) for c in WINDOW_COLS]
            F       = len(w_idx) // T
            print(f"  T={T}, F={F}")
            print(f"  Shape 3D: (n, {T}, {F})")
            X_tr_3d = X_train[:, w_idx].reshape(-1, T, F)
            X_va_3d = X_val[:,   w_idx].reshape(-1, T, F)
            X_te_3d = X_test[:,  w_idx].reshape(-1, T, F)
        else:
            print("   WINDOW_COLS vide â†’ fallback (T=1)")
            F       = X_train.shape[1]
            T       = 1
            X_tr_3d = X_train.reshape(-1, 1, F)
            X_va_3d = X_val.reshape(-1,   1, F)
            X_te_3d = X_test.reshape(-1,  1, F)

        print(f"  X_tr_3d : {X_tr_3d.shape}")
        print(f"  X_va_3d : {X_va_3d.shape}")
        print(f"  X_te_3d : {X_te_3d.shape}")

        tf.random.set_seed(42)
        inp = Input(shape=(T, F))
        x   = Bidirectional(LSTM(128, return_sequences=True,  dropout=0.2))(inp)
        x   = BatchNormalization()(x)
        x   = Bidirectional(LSTM(64,  return_sequences=False, dropout=0.2))(x)
        x   = BatchNormalization()(x)
        x   = Dense(64, activation="relu")(x)
        x   = Dropout(0.3)(x)
        out = Dense(1, activation="sigmoid")(x)

        lstm_model = KModel(inputs=inp, outputs=out, name="BiLSTM_DSO1")
        lstm_model.compile(
            optimizer=Adam(1e-3),
            loss="binary_crossentropy",
            metrics=["AUC"],
        )

        sw = np.where(y_train == 1, ratio, 1).astype(np.float32)
        print("\n  EntraÃ®nement BiLSTM...")
        lstm_model.fit(
            X_tr_3d, y_train,
            validation_data=(X_va_3d, y_val),
            sample_weight=sw,
            epochs=30, batch_size=2048, verbose=1,
            callbacks=[
                EarlyStopping(
                    monitor="val_AUC", patience=5,
                    restore_best_weights=True, mode="max",
                ),
                ReduceLROnPlateau(
                    monitor="val_loss", factor=0.5,
                    patience=3, min_lr=1e-6,
                ),
                ModelCheckpoint(
                    os.path.join(model_out_dir, "lstm_best.h5"),
                    monitor="val_AUC", save_best_only=True, mode="max",
                ),
            ],
        )
        print("BiLSTM entraÃ®nÃ©")

        y_prob_lstm = lstm_model.predict(
            X_te_3d, batch_size=4096, verbose=0
        ).flatten()
        y_pred_lstm = (y_prob_lstm > 0.5).astype(int)
        print(classification_report(y_test, y_pred_lstm, target_names=CM_LABELS))

        metrics_lstm = _metrics_binary("BiLSTM", y_test, y_pred_lstm, y_prob_lstm)
        print(f"\n  BiLSTM â†’ F1={metrics_lstm['f1']} AUC-PR={metrics_lstm['auc_pr']}")
        all_metrics.append(metrics_lstm)

        lstm_model.save(os.path.join(model_out_dir, "lstm_model.h5"))
        print(" lstm_model.h5 sauvegardÃ©")

        cm_lstm = confusion_matrix(y_test, y_pred_lstm)
        cm_lstm_path = os.path.join(model_out_dir, "cm_lstm_dso1_pct.png")
        _save_cm_pct(cm_lstm, " Matrice de Confusion (%) â€” BiLSTM (DSO1)",
                     cm_lstm_path, CM_LABELS, "Blues")

        if mlflow_available:
            log_model_run(EXPERIMENT_NAME, "BiLSTM",
                          {"lstm_units": 128, "epochs": 30, "batch_size": 2048},
                          {k: v for k, v in metrics_lstm.items() if k != "model"},
                          [cm_lstm_path], tags)

    # â”€â”€ M5 : TabNet â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    if not skip_deep:
        print("=" * 60 + "\n  M5 â€” TabNet\n" + "=" * 60)

        import torch
        from pytorch_tabnet.tab_model import TabNetClassifier
        from pytorch_tabnet.pretraining import TabNetPretrainer

        # â”€â”€ 1. Sampling â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        N_TN       = 300_000
        idx_sample = np.random.choice(len(X_train), N_TN, replace=False)
        X_tr_tn    = X_train[idx_sample]
        X_va_tn    = X_val.copy()
        X_te_tn    = X_test.copy()
        y_train_tn = y_train[idx_sample]
        print(f"Sample train : {len(X_tr_tn):,}")

        #  FIX: TabNetPretrainer defined BEFORE use
        print("\nPrÃ©-entraÃ®nement non supervisÃ© (TabNetPretrainer)...")
        pretrainer = TabNetPretrainer(
            n_d=16, n_a=16, n_steps=3, gamma=1.5,
            n_independent=2, n_shared=2,
            optimizer_fn=torch.optim.Adam,
            optimizer_params={"lr": 2e-3},
            mask_type="entmax",
            verbose=5, seed=42,
        )
        pretrainer.fit(
            X_train=X_tr_tn,
            eval_set=[X_va_tn],
            max_epochs=20, patience=5,
            batch_size=4096, virtual_batch_size=512,
            pretraining_ratio=0.8,
        )
        print("PrÃ©-entraÃ®nement terminÃ©")

        # â”€â”€ 2. Supervised model â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        tabnet_model = TabNetClassifier(
            n_d=16, n_a=16, n_steps=3, gamma=1.5,
            n_independent=2, n_shared=2,
            mask_type="entmax",
            optimizer_fn=torch.optim.Adam,
            optimizer_params={"lr": 2e-3},
            verbose=0, seed=42,
        )

        # Mini-fit to initialise the network before weight transfer
        tabnet_model.fit(
            X_train=X_tr_tn[:512],
            y_train=y_train_tn[:512].astype(int),
            max_epochs=1, batch_size=512, virtual_batch_size=512,
        )
        tabnet_model.load_weights_from_unsupervised(pretrainer)
        print(" Poids pretrainer transfÃ©rÃ©s")

        # â”€â”€ 3. Real supervised training â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        tabnet_model.verbose = 10
        tabnet_model.fit(
            X_train=X_tr_tn,
            y_train=y_train_tn.astype(int),
            eval_set=[(X_va_tn, y_val.astype(int))],
            eval_metric=["auc"],
            max_epochs=30, patience=5,
            batch_size=4096, virtual_batch_size=512,
            weights=1,
        )
        print("TabNet entraÃ®nÃ©")

        y_pred_tn = tabnet_model.predict(X_te_tn)
        y_prob_tn = tabnet_model.predict_proba(X_te_tn)[:, 1]
        print(classification_report(y_test, y_pred_tn, target_names=CM_LABELS))

        metrics_tn = _metrics_binary("TabNet", y_test, y_pred_tn, y_prob_tn)
        print(f"\n  TabNet â†’ F1={metrics_tn['f1']} AUC-PR={metrics_tn['auc_pr']}")
        all_metrics.append(metrics_tn)

        tabnet_model.save_model(os.path.join(model_out_dir, "tabnet_model"))
        print(" tabnet_model sauvegardÃ©")

        cm_tn = confusion_matrix(y_test, y_pred_tn)
        cm_tn_path = os.path.join(model_out_dir, "cm_tabnet_dso1_pct.png")
        _save_cm_pct(cm_tn, " Matrice de Confusion (%) â€” TabNet (DSO1)",
                     cm_tn_path, CM_LABELS, "Blues")

        if mlflow_available:
            log_model_run(EXPERIMENT_NAME, "TabNet",
                          {"n_d": 16, "n_a": 16, "n_steps": 3},
                          {k: v for k, v in metrics_tn.items() if k != "model"},
                          [cm_tn_path], tags)

    # â”€â”€ SHAP on LightGBM â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print("\nCalcul SHAP sur LightGBM (meilleur modÃ¨le)...")
    try:
        import shap
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "shap", "-q"])
        import shap

    N_SHAP  = 5_000
    idx_sh  = np.random.choice(len(X_test), N_SHAP, replace=False)
    X_shap  = X_test[idx_sh]

    explainer   = shap.TreeExplainer(lgbm_model)
    shap_values = explainer.shap_values(X_shap)

    # shap_values may be a list [class0, class1]
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
        print(f"\n   cluster_id: rang #{rang} â€” SHAP={val:.4f}")
    else:
        print("   cluster_id non trouvÃ© dans SHAP")

    shap_json_path = os.path.join(model_out_dir, "shap_lgbm_dso1.json")
    shap_df.to_json(shap_json_path, orient="records", indent=2)
    print(" shap_lgbm_dso1.json sauvegardÃ©")

    # SHAP bar chart
    shap_plot_path = os.path.join(model_out_dir, "shap_dso1.png")
    fig, ax = plt.subplots(figsize=(10, 8))
    top20      = shap_df.head(20)
    bar_colors = [RED if f == "cluster_id" else BLUE for f in top20["feature"]]
    ax.barh(top20["feature"][::-1], top20["shap"][::-1], color=bar_colors[::-1])
    ax.set_xlabel("SHAP value (mean |importance|)", fontsize=11)
    ax.set_title(" SHAP Feature Importance â€” LightGBM DSO1",
                 fontsize=12, fontweight="bold")
    if "cluster_id" in top20["feature"].values:
        xv  = top20[top20["feature"] == "cluster_id"]["shap"].values[0]
        yv  = top20["feature"].tolist()[::-1].index("cluster_id")
        ax.annotate("â† cluster_id (zone NB2)", xy=(xv, yv), fontsize=9, color=RED)
    plt.tight_layout()
    plt.savefig(shap_plot_path, bbox_inches="tight", facecolor="#0F1117")
    plt.close(fig)

    # â”€â”€ All confusion matrices side-by-side â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # Build the list dynamically (deep models may be absent when skip_deep=True)
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
        ax.set_xlabel("PrÃ©dit")
        ax.set_ylabel("RÃ©el")
    plt.suptitle(" Toutes les Matrices de Confusion (%) â€” DSO1",
                 fontsize=14, fontweight="bold", color="white", y=1.02)
    plt.tight_layout()
    cm_all_path = os.path.join(model_out_dir, "cm_all_dso1.png")
    plt.savefig(cm_all_path, bbox_inches="tight", facecolor="#0F1117")
    plt.close(fig)

    # â”€â”€ Dashboard ROC + PR â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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
    axes[0].set_title("Courbes ROC", fontweight="bold")
    axes[0].plot([0, 1], [0, 1], "--", color="gray", lw=0.8)

    for name, prob, color in zip(models_list, probs_list, colors_list):
        PrecisionRecallDisplay.from_predictions(
            y_test, prob, name=name, ax=axes[1], color=color
        )
    axes[1].set_title("Precision-Recall", fontweight="bold")

    plt.suptitle(" DSO1 â€” Dashboard Final",
                 fontsize=14, fontweight="bold", color="white")
    plt.tight_layout()
    dash_path = os.path.join(model_out_dir, "dashboard_dso1.png")
    plt.savefig(dash_path, bbox_inches="tight", facecolor="#0F1117")
    plt.close(fig)

    # â”€â”€ Summary â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    df_results = pd.DataFrame(all_metrics).set_index("model")
    print("\n=== RÃ‰SULTATS DSO1 ===")
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
        "n_train":      int(len(idx_train)),
        "n_test":       int(len(idx_test)),
        "ho_rate_test": float(y_test.mean()),
    }

    json_path = os.path.join(model_out_dir, "results_dso1.json")
    with open(json_path, "w") as fh:
        json.dump(results_enriched, fh, indent=2)

    print("\nresults_dso1.json sauvegardÃ©")
    print(f"   best_model    : {best}")
    print(f"   best_f1       : {results_enriched['best_f1']}")
    print(f"   has_cluster_id: {results_enriched['has_cluster_id']}")
    print(f"   cluster_id rank: #{results_enriched['cluster_id_rank']}")
    print("\nDSO1 training complete")

    return results_enriched


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
if __name__ == "__main__":
    train_dso1()


