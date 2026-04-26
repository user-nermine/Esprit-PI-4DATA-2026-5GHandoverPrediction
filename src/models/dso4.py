# src/models/dso4.py
# Converted from NB4_DSO4_HO_Type_F.ipynb
# Task: Multiclass classification -- predict 3GPP handover type
# Input:  PT_output/df_preprocessed.parquet  (ho_type_enc column)
# Output: MODEL_output/DSO4/ -> xgb_dso4.pkl, lgbm_dso4.pkl, rf_dso4.pkl,
#                               lstm_dso4.h5, tabnet_dso4.*,
#                               results_dso4.json, cm_*.png

import os
import gc
import json
import pickle
import warnings

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.utils.class_weight import compute_class_weight
from sklearn.metrics import (
    classification_report, confusion_matrix,
    f1_score, accuracy_score,
)
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier
import lightgbm as lgb
from sklearn.ensemble import RandomForestClassifier

warnings.filterwarnings("ignore")

HO_TYPE_NAMES = [
    "no_handover", "intra_freq", "inter_freq", "inter_RAT_NR",
    "inter_operator", "intra_freq_pci", "inter_freq_pci", "ho_non_type",
]
EXPERIMENT_NAME = "DSO4-HOType"


def _save_cm(cm, title, path, labels, cmap="Blues"):
    fig, ax = plt.subplots(figsize=(10, 8))
    sns.heatmap(cm, annot=True, fmt="d", cmap=cmap,
                xticklabels=labels, yticklabels=labels,
                linewidths=0.4, ax=ax, annot_kws={"size": 9, "weight": "bold"})
    ax.set_xlabel("Predit", fontsize=11)
    ax.set_ylabel("Reel", fontsize=11)
    ax.tick_params(axis="x", rotation=35, labelsize=8)
    ax.tick_params(axis="y", rotation=0, labelsize=8)
    ax.set_title(title, fontsize=12, fontweight="bold")
    plt.tight_layout()
    plt.savefig(path, bbox_inches="tight")
    plt.close(fig)


def _metrics_multiclass(name, y_true, y_pred):
    return {
        "model":       name,
        "accuracy":    round(accuracy_score(y_true, y_pred), 4),
        "f1_macro":    round(f1_score(y_true, y_pred, average="macro",
                                      zero_division=0), 4),
        "f1_weighted": round(f1_score(y_true, y_pred, average="weighted",
                                      zero_division=0), 4),
    }


def train_dso4(
    pt_out_dir:    str = "PT_output",
    model_out_dir: str = os.path.join("MODEL_output", "DSO4"),
    skip_deep:     bool = False,
):
    """
    Train all 5 models for DSO4 (handover type prediction).

    Models:
        M1  XGBoost        (multi:softmax)
        M2  LightGBM       (multiclass)
        M3  Random Forest
        M4  BiLSTM Softmax  (skipped if skip_deep=True)
        M5  TabNet          (skipped if skip_deep=True)

    Args:
        pt_out_dir:    folder produced by preprocessing.py
        model_out_dir: output folder for models + metrics
        skip_deep:     set True in CI to skip GPU-heavy models
    """
    os.makedirs(model_out_dir, exist_ok=True)
    assert os.path.exists(pt_out_dir), \
        f" {pt_out_dir} not found -- run preprocessing first!"

    try:
        from mlflow_utils import log_model_run
        mlflow_available = True
    except Exception:
        mlflow_available = False
        print("  [MLflow] Not available, skipping logging.")

    tags = {"dso": "DSO4", "task": "ho_type", "skip_deep": str(skip_deep)}

    # -- Load data -------------------------------------------------------------
    print("=" * 60 + "\n  DSO4 -- Loading data\n" + "=" * 60)
    import pyarrow.parquet as pq
    pf = pq.ParquetFile(os.path.join(pt_out_dir, "df_preprocessed.parquet"))
    chunks = []
    for batch in pf.iter_batches(batch_size=100_000):
        chunks.append(batch.to_pandas())
    df = pd.concat(chunks, ignore_index=True)
    if skip_deep:
        df = df.iloc[:50_000].copy()
    assert "ho_type_enc" in df.columns and "handover" in df.columns, \
        " ho_type_enc or handover column missing -- check preprocessing!"

    df_ho4 = df[df["handover"] == 1].copy()
    print(f"  Handovers : {len(df_ho4):,}")

    with open(os.path.join(pt_out_dir, "config.json")) as f:
        config = json.load(f)

    cols_x = [
        c for c in config["cols_X"]
        if c in df_ho4.columns and c not in ["handover", "ho_type_enc"]
    ]

    X_all  = df_ho4[cols_x].values.astype(np.float32)
    y_all  = df_ho4["ho_type_enc"].values.astype(int)
    del df
    gc.collect()

    # Remap classes to contiguous 0..N-1
    unique_classes = np.unique(y_all)
    remap          = {old: new for new, old in enumerate(unique_classes)}
    y_all_enc      = np.array([remap[y] for y in y_all])
    N_CLASSES      = len(unique_classes)
    class_names    = [
        HO_TYPE_NAMES[int(c)] if int(c) < len(HO_TYPE_NAMES) else f"type_{c}"
        for c in unique_classes
    ]

    n      = len(X_all)
    n_tr   = int(n * 0.70)
    n_va   = int(n * 0.15)
    X_train, X_val, X_test = X_all[:n_tr], X_all[n_tr: n_tr + n_va], X_all[n_tr + n_va:]
    y_train, y_val, y_test = (
        y_all_enc[:n_tr],
        y_all_enc[n_tr: n_tr + n_va],
        y_all_enc[n_tr + n_va:],
    )

    cw_arr  = compute_class_weight("balanced", classes=np.arange(N_CLASSES), y=y_train)
    cw_dict = {i: cw_arr[i] for i in range(N_CLASSES)}

    print(f"  N_CLASSES={N_CLASSES} | Classes={class_names}")
    print(f"  train={len(X_train):,} | val={len(X_val):,} | test={len(X_test):,}")

    all_metrics = []

    # -- M1 : XGBoost ----------------------------------------------------------
    print("=" * 60 + "\n  M1 -- XGBoost DSO4\n" + "=" * 60)
    xgb_params = dict(
        n_estimators=400, max_depth=7, learning_rate=0.08,
        subsample=0.8, colsample_bytree=0.8,
    )
    sw_train = np.array([cw_dict[y] for y in y_train], dtype=np.float32)
    xgb_d4   = XGBClassifier(
        **xgb_params,
        objective="multi:softmax", num_class=N_CLASSES,
        eval_metric="mlogloss", early_stopping_rounds=25,
        tree_method="hist", random_state=42, n_jobs=-1,
        use_label_encoder=False,
    )
    xgb_d4.fit(
        X_train, y_train, sample_weight=sw_train,
        eval_set=[(X_val, y_val)], verbose=40,
    )
    y_pred_xgb = xgb_d4.predict(X_test)
    print(classification_report(y_test, y_pred_xgb,
                                 target_names=class_names, zero_division=0))

    metrics_xgb = _metrics_multiclass("XGBoost", y_test, y_pred_xgb)
    all_metrics.append(metrics_xgb)

    pkl_xgb = os.path.join(model_out_dir, "xgb_dso4.pkl")
    cm_xgb  = os.path.join(model_out_dir, "cm_xgb_dso4.png")
    with open(pkl_xgb, "wb") as f:
        pickle.dump(xgb_d4, f)
    _save_cm(
        confusion_matrix(y_test, y_pred_xgb, labels=list(range(N_CLASSES))),
        "Confusion Matrix -- XGBoost (DSO4)", cm_xgb, class_names, "Blues",
    )
    if mlflow_available:
        log_model_run(EXPERIMENT_NAME, "XGBoost", xgb_params,
                      {k: v for k, v in metrics_xgb.items() if k != "model"},
                      [cm_xgb, pkl_xgb], tags)

    # -- M2 : LightGBM ---------------------------------------------------------
    print("=" * 60 + "\n  M2 -- LightGBM DSO4\n" + "=" * 60)
    lgbm_params = dict(
        n_estimators=400, max_depth=8, learning_rate=0.08, num_leaves=127,
        subsample=0.8, colsample_bytree=0.8,
    )
    lgbm_d4 = LGBMClassifier(
        **lgbm_params,
        objective="multiclass", num_class=N_CLASSES,
        metric="multi_logloss", class_weight="balanced",
        random_state=42, n_jobs=-1, verbose=-1,
    )
    lgbm_d4.fit(
        X_train, y_train, eval_set=[(X_val, y_val)],
        callbacks=[lgb.early_stopping(25, verbose=False), lgb.log_evaluation(40)],
    )
    y_pred_lgbm = lgbm_d4.predict(X_test)
    print(classification_report(y_test, y_pred_lgbm,
                                  target_names=class_names, zero_division=0))

    metrics_lgbm = _metrics_multiclass("LightGBM", y_test, y_pred_lgbm)
    all_metrics.append(metrics_lgbm)

    pkl_lgbm = os.path.join(model_out_dir, "lgbm_dso4.pkl")
    cm_lgbm  = os.path.join(model_out_dir, "cm_lgbm_dso4.png")
    with open(pkl_lgbm, "wb") as f:
        pickle.dump(lgbm_d4, f)
    _save_cm(
        confusion_matrix(y_test, y_pred_lgbm, labels=list(range(N_CLASSES))),
        "Confusion Matrix -- LightGBM (DSO4)", cm_lgbm, class_names, "Greens",
    )
    if mlflow_available:
        log_model_run(EXPERIMENT_NAME, "LightGBM", lgbm_params,
                      {k: v for k, v in metrics_lgbm.items() if k != "model"},
                      [cm_lgbm, pkl_lgbm], tags)

    # -- M3 : Random Forest ----------------------------------------------------
    print("=" * 60 + "\n  M3 -- Random Forest DSO4\n" + "=" * 60)
    rf_params = dict(
        n_estimators=250, max_depth=18, min_samples_leaf=5, max_features="sqrt",
    )
    rf_d4 = RandomForestClassifier(
        **rf_params, class_weight="balanced_subsample",
        max_samples=0.4, random_state=42, n_jobs=-1, verbose=1,
    )
    rf_d4.fit(X_train, y_train)
    y_pred_rf = rf_d4.predict(X_test)
    print(classification_report(y_test, y_pred_rf,
                                  target_names=class_names, zero_division=0))

    metrics_rf = _metrics_multiclass("Random Forest", y_test, y_pred_rf)
    all_metrics.append(metrics_rf)

    pkl_rf = os.path.join(model_out_dir, "rf_dso4.pkl")
    cm_rf  = os.path.join(model_out_dir, "cm_rf_dso4.png")
    with open(pkl_rf, "wb") as f:
        pickle.dump(rf_d4, f)
    _save_cm(
        confusion_matrix(y_test, y_pred_rf, labels=list(range(N_CLASSES))),
        "Confusion Matrix -- Random Forest (DSO4)", cm_rf, class_names, "Oranges",
    )
    if mlflow_available:
        log_model_run(EXPERIMENT_NAME, "RandomForest", rf_params,
                      {k: v for k, v in metrics_rf.items() if k != "model"},
                      [cm_rf, pkl_rf], tags)

    # -- M4 : BiLSTM Softmax ---------------------------------------------------
    if not skip_deep:
        print("=" * 60 + "\n  M4 -- BiLSTM DSO4\n" + "=" * 60)
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

        tf.random.set_seed(42)
        inp = Input(shape=(T, F))
        x   = Bidirectional(LSTM(128, return_sequences=True,  dropout=0.2))(inp)
        x   = BatchNormalization()(x)
        x   = Bidirectional(LSTM(64,  return_sequences=False, dropout=0.2))(x)
        x   = BatchNormalization()(x)
        x   = Dense(128, activation="relu")(x)
        x   = Dropout(0.35)(x)
        x   = Dense(64, activation="relu")(x)
        out = Dense(N_CLASSES, activation="softmax")(x)

        lstm_d4 = KModel(inputs=inp, outputs=out, name="LSTM_DSO4")
        lstm_d4.compile(
            optimizer=Adam(1e-3),
            loss="categorical_crossentropy",
            metrics=["accuracy"],
        )
        lstm_d4.fit(
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
                    os.path.join(model_out_dir, "lstm_dso4_best.h5"),
                    monitor="val_accuracy", save_best_only=True, mode="max",
                ),
            ],
        )

        y_proba_lstm = lstm_d4.predict(X_te_3d, batch_size=2048, verbose=0)
        y_pred_lstm  = y_proba_lstm.argmax(axis=1)
        print(classification_report(y_test, y_pred_lstm,
                                     target_names=class_names, zero_division=0))

        metrics_lstm = _metrics_multiclass("BiLSTM", y_test, y_pred_lstm)
        all_metrics.append(metrics_lstm)
        lstm_path = os.path.join(model_out_dir, "lstm_dso4.h5")
        lstm_d4.save(lstm_path)
        cm_lstm = os.path.join(model_out_dir, "cm_lstm_dso4.png")
        _save_cm(
            confusion_matrix(y_test, y_pred_lstm, labels=list(range(N_CLASSES))),
            "Confusion Matrix -- BiLSTM (DSO4)", cm_lstm, class_names, "Reds",
        )
        if mlflow_available:
            log_model_run(EXPERIMENT_NAME, "BiLSTM",
                          {"lstm_units": 128, "epochs": 30, "batch_size": 1024},
                          {k: v for k, v in metrics_lstm.items() if k != "model"},
                          [cm_lstm, lstm_path], tags)

    # -- M5 : TabNet -----------------------------------------------------------
    if not skip_deep:
        print("=" * 60 + "\n  M5 -- TabNet DSO4\n" + "=" * 60)
        import torch
        from pytorch_tabnet.tab_model import TabNetClassifier
        from pytorch_tabnet.pretraining import TabNetPretrainer

        N_TN    = min(100_000, len(X_train))
        idx_tn  = np.random.choice(len(X_train), N_TN, replace=False)
        X_tr_tn = X_train[idx_tn].astype(np.float32)
        X_va_tn = X_val.astype(np.float32)
        X_te_tn = X_test.astype(np.float32)
        y_tr_tn = y_train[idx_tn]

        pt_d4 = TabNetPretrainer(
            n_d=16, n_a=16, n_steps=3, gamma=1.5,
            n_independent=2, n_shared=2, mask_type="entmax",
            optimizer_fn=torch.optim.Adam,
            optimizer_params={"lr": 2e-3},
            verbose=5, seed=42,
        )
        pt_d4.fit(
            X_train=X_tr_tn, eval_set=[X_va_tn],
            max_epochs=30, patience=5,
            batch_size=2048, virtual_batch_size=256,
            pretraining_ratio=0.5,
        )

        tabnet_d4 = TabNetClassifier(
            n_d=16, n_a=16, n_steps=3, gamma=1.5,
            n_independent=2, n_shared=2, mask_type="entmax",
            optimizer_fn=torch.optim.Adam,
            optimizer_params={"lr": 2e-3},
            verbose=0, seed=42,
        )
        tabnet_d4.fit(
            X_train=X_tr_tn[:512], y_train=y_tr_tn[:512].astype(int),
            max_epochs=1, batch_size=512, virtual_batch_size=512,
        )
        tabnet_d4.load_weights_from_unsupervised(pt_d4)
        tabnet_d4.verbose = 10
        tabnet_d4.fit(
            X_train=X_tr_tn, y_train=y_tr_tn.astype(int),
            eval_set=[(X_va_tn, y_val.astype(int))],
            eval_metric=["accuracy"],
            max_epochs=30, patience=5,
            batch_size=2048, virtual_batch_size=256,
            weights=1,
        )

        y_pred_tn = tabnet_d4.predict(X_te_tn)
        print(classification_report(y_test, y_pred_tn,
                                     target_names=class_names, zero_division=0))

        metrics_tn = _metrics_multiclass("TabNet", y_test, y_pred_tn)
        all_metrics.append(metrics_tn)
        tabnet_d4.save_model(os.path.join(model_out_dir, "tabnet_dso4"))

        if mlflow_available:
            log_model_run(EXPERIMENT_NAME, "TabNet",
                          {"n_d": 16, "n_a": 16, "n_steps": 3},
                          {k: v for k, v in metrics_tn.items() if k != "model"},
                          [], tags)

    # -- Save summary ----------------------------------------------------------
    with open(os.path.join(model_out_dir, "results_dso4.json"), "w") as f:
        json.dump(all_metrics, f, indent=2)

    df_results = pd.DataFrame(all_metrics).set_index("model")
    print("\n" + df_results.to_string())
    best = df_results["f1_macro"].idxmax()
    print(f"\nBest (F1-macro) : {best} -> {df_results.loc[best, 'f1_macro']:.4f}")
    print("\nDSO4 training complete")
    return all_metrics


if __name__ == "__main__":
    train_dso4()