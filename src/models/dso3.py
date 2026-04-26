# src/models/dso3.py
# Converted from NB4_DSO3_Next_Cell_F.ipynb
# Task: Multiclass classification -- predict next best cell (Top-N)
# Input:  PT_output/ + FE_data/df_ho.parquet  (for label construction)
# Output: MODEL_output/DSO3/ -> xgb_dso3.pkl, lgbm_dso3.pkl, rf_dso3.pkl,
#                               lstm_dso3.h5, tabnet_dso3.*,
#                               label_encoder_cells.pkl,
#                               results_dso3.json, cm_*.png

import os
import gc
import json
import pickle
import warnings

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.utils.class_weight import compute_class_weight
from sklearn.metrics import (
    confusion_matrix,
    f1_score, accuracy_score, top_k_accuracy_score,
)
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier
import lightgbm as lgb
from sklearn.ensemble import RandomForestClassifier

warnings.filterwarnings("ignore")

CONFIGS     = {"static": "session_id", "mobile": "device", "hbahn": "device"}
TOP_N_CELLS = 50
TOP_K_EVAL  = 3


def _build_next_cell_label(fe_data_dir: str, model_out_dir: str):
    """
    Build next_cell multiclass label from df_ho.parquet.
    Returns X_all, y_all (re-encoded), le2 (LabelEncoder), N_CLASSES.
    """
    df_ho = pd.read_parquet(
        os.path.join(fe_data_dir, "df_ho.parquet"),
        columns=["session_id", "device", "source_folder", "cell_index", "handover"],
    )
    df_ho["next_cell"] = np.nan

    for env, cle in CONFIGS.items():
        if cle not in df_ho.columns:
            continue
        mask_env = df_ho["source_folder"] == env
        for _, grp in df_ho[mask_env].groupby(cle):
            df_ho.loc[grp.index, "next_cell"] = grp["cell_index"].shift(-1)

    df_ho_only   = df_ho[df_ho["handover"] == 1].dropna(subset=["next_cell"])
    cell_counts  = df_ho_only["next_cell"].value_counts()
    top_cells    = cell_counts.head(TOP_N_CELLS).index.tolist()
    coverage     = cell_counts.head(TOP_N_CELLS).sum() / cell_counts.sum() * 100
    print(f"  Top-{TOP_N_CELLS} covers {coverage:.1f}% of handovers")

    df_filtered = df_ho_only[df_ho_only["next_cell"].isin(top_cells)].copy()
    le          = LabelEncoder()
    df_filtered["next_cell_enc"] = le.fit_transform(
        df_filtered["next_cell"].astype(str)
    )
    print(f"  {len(le.classes_)} classes | {len(df_filtered):,} handovers retained")
    return df_filtered, le


def _save_cm(cm, title, path, labels, cmap="Blues"):
    fig, ax = plt.subplots(figsize=(10, 8))
    sns.heatmap(cm, annot=True, fmt="d", cmap=cmap,
                xticklabels=labels, yticklabels=labels,
                linewidths=0.3, ax=ax, annot_kws={"size": 8})
    ax.set_xlabel("Predit", fontsize=10)
    ax.set_ylabel("Reel", fontsize=10)
    ax.tick_params(axis="x", rotation=45, labelsize=7)
    ax.tick_params(axis="y", labelsize=7)
    ax.set_title(title, fontsize=11, fontweight="bold")
    plt.tight_layout()
    plt.savefig(path, bbox_inches="tight")
    plt.close(fig)


def _metrics_multiclass(name, y_true, y_pred, y_proba, n_classes, k=TOP_K_EVAL):
    return {
        "model":       name,
        "accuracy":    round(accuracy_score(y_true, y_pred), 4),
        f"top{k}_acc": round(
            top_k_accuracy_score(y_true, y_proba, k=k,
                                 labels=np.arange(n_classes)), 4
        ),
        "f1_macro":    round(f1_score(y_true, y_pred, average="macro",
                                      zero_division=0), 4),
    }


def train_dso3(
    pt_out_dir:    str = "PT_output",
    fe_data_dir:   str = "FE_data",
    model_out_dir: str = os.path.join("MODEL_output", "DSO3"),
    skip_deep:     bool = False,
):
    """
    Train all 5 models for DSO3 (next best cell prediction).

    Models:
        M1  XGBoost        (multi:softmax)
        M2  LightGBM       (multiclass)
        M3  Random Forest
        M4  LSTM Softmax    (skipped if skip_deep=True)
        M5  TabNet          (skipped if skip_deep=True)

    Args:
        pt_out_dir:    folder produced by preprocessing.py
        fe_data_dir:   folder containing df_ho.parquet (from feature_engineering)
        model_out_dir: output folder for models + metrics
        skip_deep:     set True in CI to skip GPU-heavy models
    """
    os.makedirs(model_out_dir, exist_ok=True)
    assert os.path.exists(pt_out_dir), \
        f" {pt_out_dir} not found -- run preprocessing first!"
    assert os.path.exists(fe_data_dir), \
        f" {fe_data_dir} not found -- run feature_engineering first!"

    # -- Build label -----------------------------------------------------------
    print("=" * 60 + "\n  DSO3 -- Building Next Cell label\n" + "=" * 60)
    df_filtered, _le = _build_next_cell_label(fe_data_dir, model_out_dir)

    # -- Load preprocessed features -------------------------------------------
    with open(os.path.join(pt_out_dir, "config.json")) as f:
        config = json.load(f)

    pf        = pq.ParquetFile(os.path.join(pt_out_dir, "df_preprocessed.parquet"))
    schema    = pf.schema_arrow.names
    cols_x    = [c for c in config["cols_X"] if c in schema]

    df_pre    = pd.read_parquet(
        os.path.join(pt_out_dir, "df_preprocessed.parquet"), columns=cols_x
    )
    common_idx  = df_filtered.index[df_filtered.index.isin(df_pre.index)]
    df_filtered = df_filtered.loc[common_idx]
    X_all       = df_pre.loc[common_idx, cols_x].values.astype(np.float32)
    y_all       = df_filtered["next_cell_enc"].values

    if skip_deep:
        n = 10_000
        X_all = X_all[:n]
        y_all = y_all[:n]
    del df_pre
    gc.collect()

    # -- Stratified split ------------------------------------------------------
    X_temp, X_test, y_temp, y_test = train_test_split(
        X_all, y_all, test_size=0.15, random_state=42, stratify=y_all
    )
    X_train, X_val, y_train, y_val = train_test_split(
        X_temp, y_temp, test_size=0.15 / 0.85, random_state=42, stratify=y_temp
    )
    del X_temp, y_temp
    gc.collect()

    # Re-encode cleanly on y_train classes
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

    N_CLASSES   = len(le2.classes_)
    with open(os.path.join(model_out_dir, "label_encoder_cells.pkl"), "wb") as f:
        pickle.dump(le2, f)

    print(f" {N_CLASSES} classes | train={len(X_train):,} "
          f"| val={len(X_val):,} | test={len(X_test):,}")

    all_metrics = []

    # -- M1 : XGBoost ----------------------------------------------------------
    print("=" * 60 + "\n  M1 -- XGBoost DSO3\n" + "=" * 60)
    xgb_d3 = XGBClassifier(
        n_estimators=300, max_depth=6, learning_rate=0.1,
        subsample=0.8, colsample_bytree=0.8,
        objective="multi:softmax", num_class=N_CLASSES,
        eval_metric="mlogloss", early_stopping_rounds=20,
        tree_method="hist", random_state=42, n_jobs=-1,
        use_label_encoder=False,
    )
    xgb_d3.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=30)
    y_pred_xgb  = xgb_d3.predict(X_test)
    y_proba_xgb = xgb_d3.predict_proba(X_test)

    metrics_xgb = _metrics_multiclass("XGBoost", y_test, y_pred_xgb,
                                       y_proba_xgb, N_CLASSES)
    all_metrics.append(metrics_xgb)
    print(f"  Acc={metrics_xgb['accuracy']:.4f} | "
          f"Top-{TOP_K_EVAL}={metrics_xgb[f'top{TOP_K_EVAL}_acc']:.4f} | "
          f"F1={metrics_xgb['f1_macro']:.4f}")

    with open(os.path.join(model_out_dir, "xgb_dso3.pkl"), "wb") as f:
        pickle.dump(xgb_d3, f)

    top15_cls   = pd.Series(y_test).value_counts().head(15).index.tolist()
    mask_top    = np.isin(y_test, top15_cls)
    top15_labels = [str(le2.classes_[i])[:8] for i in top15_cls]
    _save_cm(
        confusion_matrix(y_test[mask_top], y_pred_xgb[mask_top], labels=top15_cls),
        "Confusion Matrix -- XGBoost DSO3 (Top-15 cells)",
        os.path.join(model_out_dir, "cm_xgb_dso3.png"), top15_labels, "Blues",
    )

    # -- M2 : LightGBM ---------------------------------------------------------
    print("=" * 60 + "\n  M2 -- LightGBM DSO3\n" + "=" * 60)
    lgbm_d3 = LGBMClassifier(
        n_estimators=300, max_depth=7, learning_rate=0.1, num_leaves=63,
        subsample=0.8, colsample_bytree=0.8,
        objective="multiclass", num_class=N_CLASSES,
        metric="multi_logloss", class_weight="balanced",
        random_state=42, n_jobs=-1, verbose=-1,
    )
    lgbm_d3.fit(
        X_train, y_train, eval_set=[(X_val, y_val)],
        callbacks=[lgb.early_stopping(20, verbose=False), lgb.log_evaluation(30)],
    )
    y_pred_lgbm  = lgbm_d3.predict(X_test)
    y_proba_lgbm = lgbm_d3.predict_proba(X_test)

    metrics_lgbm = _metrics_multiclass("LightGBM", y_test, y_pred_lgbm,
                                        y_proba_lgbm, N_CLASSES)
    all_metrics.append(metrics_lgbm)
    with open(os.path.join(model_out_dir, "lgbm_dso3.pkl"), "wb") as f:
        pickle.dump(lgbm_d3, f)
    _save_cm(
        confusion_matrix(y_test[mask_top], y_pred_lgbm[mask_top], labels=top15_cls),
        "Confusion Matrix -- LightGBM DSO3 (Top-15)",
        os.path.join(model_out_dir, "cm_lgbm_dso3.png"), top15_labels, "Greens",
    )

    # -- M3 : Random Forest ----------------------------------------------------
    print("=" * 60 + "\n  M3 -- Random Forest DSO3\n" + "=" * 60)
    rf_d3 = RandomForestClassifier(
        n_estimators=200, max_depth=15, min_samples_leaf=10,
        max_features="sqrt", class_weight="balanced_subsample",
        max_samples=0.3, random_state=42, n_jobs=-1, verbose=1,
    )
    rf_d3.fit(X_train, y_train)
    y_pred_rf  = rf_d3.predict(X_test)
    y_proba_rf = rf_d3.predict_proba(X_test)

    metrics_rf = _metrics_multiclass("Random Forest", y_test, y_pred_rf,
                                      y_proba_rf, N_CLASSES)
    all_metrics.append(metrics_rf)
    with open(os.path.join(model_out_dir, "rf_dso3.pkl"), "wb") as f:
        pickle.dump(rf_d3, f)
    _save_cm(
        confusion_matrix(y_test[mask_top], y_pred_rf[mask_top], labels=top15_cls),
        "Confusion Matrix -- Random Forest DSO3 (Top-15)",
        os.path.join(model_out_dir, "cm_rf_dso3.png"), top15_labels, "Oranges",
    )

    # -- M4 : LSTM Softmax -----------------------------------------------------
    if not skip_deep:
        print("=" * 60 + "\n  M4 -- LSTM Softmax DSO3\n" + "=" * 60)
        import tensorflow as tf
        from tensorflow.keras.models import Model as KModel
        from tensorflow.keras.layers import (
            LSTM, Bidirectional, Dense, Dropout, BatchNormalization, Input,
        )
        from tensorflow.keras.callbacks import (
            EarlyStopping, ReduceLROnPlateau, ModelCheckpoint,
        )
        from tensorflow.keras.optimizers import Adam
        from tensorflow.keras.utils import to_categorical

        window_cols = [c for c in cols_x if any(f"_T{k}" in c for k in range(1, 6))]
        T = 5 if window_cols else 1
        if window_cols:
            w_idx   = [list(cols_x).index(c) for c in window_cols]
            F       = len(w_idx) // T
            X_tr_3d = X_train[:, w_idx].reshape(-1, T, F)
            X_va_3d = X_val[:,   w_idx].reshape(-1, T, F)
            X_te_3d = X_test[:,  w_idx].reshape(-1, T, F)
        else:
            F = X_train.shape[1]
            T = 1
            X_tr_3d = X_train.reshape(-1, 1, F)
            X_va_3d = X_val.reshape(-1, 1, F)
            X_te_3d = X_test.reshape(-1, 1, F)

        y_tr_cat = to_categorical(y_train, N_CLASSES)
        y_va_cat = to_categorical(y_val,   N_CLASSES)
        cw_arr   = compute_class_weight(
            "balanced", classes=np.arange(N_CLASSES), y=y_train
        )
        cw_dict  = {i: cw_arr[i] for i in range(N_CLASSES)}

        tf.random.set_seed(42)
        inp = Input(shape=(T, F))
        x   = Bidirectional(LSTM(128, return_sequences=True,  dropout=0.2))(inp)
        x   = BatchNormalization()(x)
        x   = Bidirectional(LSTM(64,  return_sequences=False, dropout=0.2))(x)
        x   = BatchNormalization()(x)
        x   = Dense(128, activation="relu")(x)
        x   = Dropout(0.35)(x)
        out = Dense(N_CLASSES, activation="softmax")(x)

        lstm_d3 = KModel(inputs=inp, outputs=out, name="LSTM_DSO3")
        lstm_d3.compile(
            optimizer=Adam(1e-3),
            loss="categorical_crossentropy",
            metrics=["accuracy"],
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
        metrics_lstm = _metrics_multiclass("BiLSTM", y_test, y_pred_lstm,
                                            y_proba_lstm, N_CLASSES)
        all_metrics.append(metrics_lstm)
        lstm_d3.save(os.path.join(model_out_dir, "lstm_dso3.h5"))

    # -- M5 : TabNet -----------------------------------------------------------
    if not skip_deep:
        print("=" * 60 + "\n  M5 -- TabNet DSO3\n" + "=" * 60)
        import torch
        from pytorch_tabnet.tab_model import TabNetClassifier
        from pytorch_tabnet.pretraining import TabNetPretrainer

        N_TN    = min(100_000, len(X_train))
        idx_tn  = np.random.choice(len(X_train), N_TN, replace=False)
        X_tr_tn = X_train[idx_tn].astype(np.float32)
        X_va_tn = X_val.astype(np.float32)
        X_te_tn = X_test.astype(np.float32)
        y_tr_tn = y_train[idx_tn]

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

        tabnet_d3 = TabNetClassifier(
            n_d=16, n_a=16, n_steps=3, gamma=1.5,
            n_independent=2, n_shared=2, mask_type="entmax",
            optimizer_fn=torch.optim.Adam,
            optimizer_params={"lr": 2e-3},
            verbose=0, seed=42,
        )
        tabnet_d3.fit(
            X_train=X_tr_tn[:512], y_train=y_tr_tn[:512].astype(int),
            max_epochs=1, batch_size=512, virtual_batch_size=512,
        )
        tabnet_d3.load_weights_from_unsupervised(pt_d3)
        tabnet_d3.verbose = 10
        tabnet_d3.fit(
            X_train=X_tr_tn, y_train=y_tr_tn.astype(int),
            eval_set=[(X_va_tn, y_val.astype(int))],
            eval_metric=["accuracy"],
            max_epochs=30, patience=5,
            batch_size=2048, virtual_batch_size=256,
            weights=1,
        )

        y_pred_tn  = tabnet_d3.predict(X_te_tn)
        y_proba_tn = tabnet_d3.predict_proba(X_te_tn)
        metrics_tn = _metrics_multiclass("TabNet", y_test, y_pred_tn,
                                          y_proba_tn, N_CLASSES)
        all_metrics.append(metrics_tn)
        tabnet_d3.save_model(os.path.join(model_out_dir, "tabnet_dso3"))

    # -- Save summary ----------------------------------------------------------
    with open(os.path.join(model_out_dir, "results_dso3.json"), "w") as f:
        json.dump(all_metrics, f, indent=2)

    df_results = pd.DataFrame(all_metrics).set_index("model")
    print("\n" + df_results.to_string())
    best = df_results["f1_macro"].idxmax()
    print(f"\nBest (F1-macro) : {best} -> {df_results.loc[best, 'f1_macro']:.4f}")
    print("\nDSO3 training complete")
    return all_metrics


if __name__ == "__main__":
    train_dso3()