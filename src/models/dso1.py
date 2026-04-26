# src/models/dso1.py
# Converted from NB4_DSO1_Handover_Binary_CORRIGE.ipynb
# Task: Binary classification — predict handover (0/1)
# Input:  PT_output/df_preprocessed.parquet + idx/y .npy files
# Output: MODEL_output/DSO1/ ? xgb_model.pkl, lgbm_model.pkl, rf_model.pkl,
#                               lstm_dso1.h5, tabnet_model.*,
#                               results_dso1.json, cm_*.png

import os
import gc
import json
import pickle
import warnings

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # headless — no display needed in CI
import matplotlib.pyplot as plt
import seaborn as sns

from xgboost import XGBClassifier
from lightgbm import LGBMClassifier
import lightgbm as lgb
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    classification_report, confusion_matrix,
    roc_auc_score, f1_score, precision_score, recall_score,
    average_precision_score,
)

warnings.filterwarnings("ignore")

CM_LABELS = ["No HO", "HO"]


def _load_data(pt_out_dir: str, dry_run: bool = False):
    """Load preprocessed data and split indices from PT_output."""
    idx_train = np.load(os.path.join(pt_out_dir, "idx_train.npy"), allow_pickle=True)
    idx_val   = np.load(os.path.join(pt_out_dir, "idx_val.npy"),   allow_pickle=True)
    idx_test  = np.load(os.path.join(pt_out_dir, "idx_test.npy"),  allow_pickle=True)
    y_train   = np.load(os.path.join(pt_out_dir, "y_train.npy"))
    y_val     = np.load(os.path.join(pt_out_dir, "y_val.npy"))
    y_test    = np.load(os.path.join(pt_out_dir, "y_test.npy"))

    with open(os.path.join(pt_out_dir, "config.json")) as f:
        config = json.load(f)
    cols_x = config["cols_X"]

    # CI dry-run: slice to 10k rows to avoid OOM
    if dry_run:
        n = 10_000
        idx_train = idx_train[:n]
        idx_val   = idx_val[:int(n * 0.2)]
        idx_test  = idx_test[:int(n * 0.2)]
        y_train   = y_train[:n]
        y_val     = y_val[:int(n * 0.2)]
        y_test    = y_test[:int(n * 0.2)]

    # read in chunks + cast to float32 immediately — avoids 6 GB float64 spike
    import pyarrow.parquet as pq
    pf = pq.ParquetFile(os.path.join(pt_out_dir, "df_preprocessed.parquet"))
    chunks = []
    for batch in pf.iter_batches(batch_size=100_000, columns=cols_x):
        chunks.append(batch.to_pandas().astype(np.float32))
    df = pd.concat(chunks, ignore_index=True)
    gc.collect()

    X_train = df.loc[idx_train].values
    X_val   = df.loc[idx_val].values
    X_test  = df.loc[idx_test].values
    del df
    gc.collect()

    ratio = int((1 - y_train.mean()) / max(y_train.mean(), 1e-6))
    print(f"X_train {X_train.shape} | HO%={y_train.mean()*100:.2f}% | ratio 1:{ratio}")
    return X_train, X_val, X_test, y_train, y_val, y_test, cols_x, ratio

def _save_cm(cm, title, path, labels, cmap="Blues"):
    """Save a confusion-matrix PNG (headless)."""
    fig, ax = plt.subplots(figsize=(6, 5))
    sns.heatmap(cm, annot=True, fmt="d", cmap=cmap,
                xticklabels=labels, yticklabels=labels,
                linewidths=0.5, ax=ax, annot_kws={"size": 14, "weight": "bold"})
    ax.set_xlabel("Prédit", fontsize=11)
    ax.set_ylabel("Réel", fontsize=11)
    ax.set_title(title, fontsize=12, fontweight="bold")
    plt.tight_layout()
    plt.savefig(path, bbox_inches="tight")
    plt.close(fig)


def _metrics_binary(name, y_true, y_pred, y_prob):
    return {
        "model":     name,
        "f1":        round(f1_score(y_true, y_pred), 4),
        "precision": round(precision_score(y_true, y_pred), 4),
        "recall":    round(recall_score(y_true, y_pred), 4),
        "auc_roc":   round(roc_auc_score(y_true, y_prob), 4),
        "auc_pr":    round(average_precision_score(y_true, y_prob), 4),
    }


def train_dso1(
    pt_out_dir:    str = "PT_output",
    model_out_dir: str = os.path.join("MODEL_output", "DSO1"),
    skip_deep: bool = False,
):
    """
    Train all 5 models for DSO1 (binary handover prediction).

    Models:
        M1  XGBoost
        M2  LightGBM
        M3  Random Forest
        M4  BiLSTM          (skipped if skip_deep=True)
        M5  TabNet          (skipped if skip_deep=True)

    Args:
        pt_out_dir:    folder produced by preprocessing.py
        model_out_dir: output folder for models + metrics
        skip_deep:     set True in CI to skip GPU-heavy models
    """
    os.makedirs(model_out_dir, exist_ok=True)
    assert os.path.exists(pt_out_dir), \
        f" {pt_out_dir} not found — run preprocessing first!"

   # ?? Load data ?????????????????????????????????????????????????????????????
    X_train, X_val, X_test, y_train, y_val, y_test, cols_x, ratio = \
        _load_data(pt_out_dir, dry_run=skip_deep)
    all_metrics = []

    # ?? M1 : XGBoost ??????????????????????????????????????????????????????????
    print("=" * 60 + "\n  M1 — XGBoost\n" + "=" * 60)
    xgb_model = XGBClassifier(
        n_estimators=500, max_depth=6, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8, scale_pos_weight=ratio,
        eval_metric="aucpr", early_stopping_rounds=30, tree_method="hist",
        random_state=42, n_jobs=-1, use_label_encoder=False,
    )
    xgb_model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=50)

    y_pred_xgb = xgb_model.predict(X_test)
    y_prob_xgb = xgb_model.predict_proba(X_test)[:, 1]
    print(classification_report(y_test, y_pred_xgb, target_names=CM_LABELS))

    metrics_xgb = _metrics_binary("XGBoost", y_test, y_pred_xgb, y_prob_xgb)
    all_metrics.append(metrics_xgb)

    with open(os.path.join(model_out_dir, "xgb_model.pkl"), "wb") as f:
        pickle.dump(xgb_model, f)
    _save_cm(confusion_matrix(y_test, y_pred_xgb),
             "Confusion Matrix — XGBoost (DSO1)",
             os.path.join(model_out_dir, "cm_xgb_dso1.png"), CM_LABELS, "Blues")

    # ?? M2 : LightGBM ?????????????????????????????????????????????????????????
    print("=" * 60 + "\n  M2 — LightGBM\n" + "=" * 60)
    lgbm_model = LGBMClassifier(
        n_estimators=500, max_depth=7, learning_rate=0.05, num_leaves=63,
        subsample=0.8, colsample_bytree=0.8, is_unbalance=True,
        metric="average_precision", random_state=42, n_jobs=-1, verbose=-1,
    )
    lgbm_model.fit(
        X_train, y_train, eval_set=[(X_val, y_val)],
        callbacks=[lgb.early_stopping(30, verbose=False), lgb.log_evaluation(50)],
    )

    y_pred_lgbm = lgbm_model.predict(X_test)
    y_prob_lgbm = lgbm_model.predict_proba(X_test)[:, 1]
    print(classification_report(y_test, y_pred_lgbm, target_names=CM_LABELS))

    metrics_lgbm = _metrics_binary("LightGBM", y_test, y_pred_lgbm, y_prob_lgbm)
    all_metrics.append(metrics_lgbm)

    with open(os.path.join(model_out_dir, "lgbm_model.pkl"), "wb") as f:
        pickle.dump(lgbm_model, f)
    _save_cm(confusion_matrix(y_test, y_pred_lgbm),
             "Confusion Matrix — LightGBM (DSO1)",
             os.path.join(model_out_dir, "cm_lgbm_dso1.png"), CM_LABELS, "Greens")

    # ?? M3 : Random Forest ????????????????????????????????????????????????????
    print("=" * 60 + "\n  M3 — Random Forest\n" + "=" * 60)
    rf_model = RandomForestClassifier(
        n_estimators=300, max_depth=15, min_samples_leaf=20,
        max_features="sqrt", class_weight="balanced_subsample",
        max_samples=0.2, random_state=42, n_jobs=-1, verbose=1,
    )
    rf_model.fit(X_train, y_train)

    y_pred_rf = rf_model.predict(X_test)
    y_prob_rf = rf_model.predict_proba(X_test)[:, 1]
    print(classification_report(y_test, y_pred_rf, target_names=CM_LABELS))

    metrics_rf = _metrics_binary("Random Forest", y_test, y_pred_rf, y_prob_rf)
    all_metrics.append(metrics_rf)

    with open(os.path.join(model_out_dir, "rf_model.pkl"), "wb") as f:
        pickle.dump(rf_model, f)
    _save_cm(confusion_matrix(y_test, y_pred_rf),
             "Confusion Matrix — Random Forest (DSO1)",
             os.path.join(model_out_dir, "cm_rf_dso1.png"), CM_LABELS, "Oranges")

    # ?? M4 : BiLSTM ???????????????????????????????????????????????????????????
    if not skip_deep:
        print("=" * 60 + "\n  M4 — BiLSTM\n" + "=" * 60)
        import tensorflow as tf
        from tensorflow.keras.models import Model as KModel
        from tensorflow.keras.layers import (
            LSTM, Bidirectional, Dense, Dropout, BatchNormalization, Input,
        )
        from tensorflow.keras.callbacks import (
            EarlyStopping, ReduceLROnPlateau, ModelCheckpoint,
        )
        from tensorflow.keras.optimizers import Adam

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
            optimizer=Adam(1e-3), loss="binary_crossentropy", metrics=["AUC"]
        )
        sw = np.where(y_train == 1, ratio, 1).astype(np.float32)

        lstm_model.fit(
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
                    os.path.join(model_out_dir, "lstm_dso1_best.h5"),
                    monitor="val_AUC", save_best_only=True, mode="max",
                ),
            ],
        )

        y_prob_lstm = lstm_model.predict(
            X_te_3d, batch_size=4096, verbose=0
        ).flatten()
        y_pred_lstm = (y_prob_lstm > 0.5).astype(int)
        print(classification_report(y_test, y_pred_lstm, target_names=CM_LABELS))

        metrics_lstm = _metrics_binary("BiLSTM", y_test, y_pred_lstm, y_prob_lstm)
        all_metrics.append(metrics_lstm)
        lstm_model.save(os.path.join(model_out_dir, "lstm_dso1.h5"))
        _save_cm(confusion_matrix(y_test, y_pred_lstm),
                 "Confusion Matrix — BiLSTM (DSO1)",
                 os.path.join(model_out_dir, "cm_lstm_dso1.png"), CM_LABELS, "Blues")

    # ?? M5 : TabNet ???????????????????????????????????????????????????????????
    if not skip_deep:
        print("=" * 60 + "\n  M5 — TabNet\n" + "=" * 60)
        import torch
        from pytorch_tabnet.tab_model import TabNetClassifier
        from pytorch_tabnet.pretraining import TabNetPretrainer

        N_TN    = min(300_000, len(X_train))
        idx_tn  = np.random.choice(len(X_train), N_TN, replace=False)
        X_tr_tn = X_train[idx_tn].astype(np.float32)
        X_va_tn = X_val.astype(np.float32)
        X_te_tn = X_test.astype(np.float32)
        y_tr_tn = y_train[idx_tn]

        pretrainer = TabNetPretrainer(
            n_d=16, n_a=16, n_steps=3, gamma=1.5,
            n_independent=2, n_shared=2, mask_type="entmax",
            optimizer_fn=torch.optim.Adam,
            optimizer_params={"lr": 2e-3},
            verbose=5, seed=42,
        )
        pretrainer.fit(
            X_train=X_tr_tn, eval_set=[X_va_tn],
            max_epochs=30, patience=5,
            batch_size=2048, virtual_batch_size=256,
            pretraining_ratio=0.5,
        )

        tabnet_model = TabNetClassifier(
            n_d=16, n_a=16, n_steps=3, gamma=1.5,
            n_independent=2, n_shared=2, mask_type="entmax",
            optimizer_fn=torch.optim.Adam,
            optimizer_params={"lr": 2e-3},
            verbose=0, seed=42,
        )
        tabnet_model.fit(
            X_train=X_tr_tn[:512], y_train=y_tr_tn[:512].astype(int),
            max_epochs=1, batch_size=512, virtual_batch_size=512,
        )
        tabnet_model.load_weights_from_unsupervised(pretrainer)
        tabnet_model.verbose = 10
        tabnet_model.fit(
            X_train=X_tr_tn, y_train=y_tr_tn.astype(int),
            eval_set=[(X_va_tn, y_val.astype(int))],
            eval_metric=["auc"],
            max_epochs=30, patience=5,
            batch_size=4096, virtual_batch_size=512,
            weights=1,
        )

        y_pred_tn = tabnet_model.predict(X_te_tn)
        y_prob_tn = tabnet_model.predict_proba(X_te_tn)[:, 1]
        print(classification_report(y_test, y_pred_tn, target_names=CM_LABELS))

        metrics_tn = _metrics_binary("TabNet", y_test, y_pred_tn, y_prob_tn)
        all_metrics.append(metrics_tn)
        tabnet_model.save_model(os.path.join(model_out_dir, "tabnet_model"))

    # ?? Save summary ??????????????????????????????????????????????????????????
    with open(os.path.join(model_out_dir, "results_dso1.json"), "w") as f:
        json.dump(all_metrics, f, indent=2)

    df_results = pd.DataFrame(all_metrics).set_index("model")
    print("\n" + df_results.to_string())
    best = df_results["f1"].idxmax()
    print(f"\n Best (F1) : {best} -> {df_results.loc[best, 'f1']:.4f}")
    print("\n DSO1 training complete")
    return all_metrics


if __name__ == "__main__":
    train_dso1()