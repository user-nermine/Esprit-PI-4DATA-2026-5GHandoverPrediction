# src/models/dso2.py
# Converted from NB4_DSO2_RSRP_Drop_F.ipynb
# Task: Binary classification -- predict RSRP drop > 6 dBm in next 5 measures
# Input:  PT_output/ + FE_output/df_final_fe.parquet  (for label construction)
# Output: MODEL_output/DSO2/ -> xgb_dso2.pkl, lgbm_dso2.pkl, rf_dso2.pkl,
#                               lstm_dso2.h5, tabnet_dso2.*,
#                               results_dso2.json, cm_*.png

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

CONFIGS    = {"static": "session_id", "mobile": "device", "hbahn": "device"}
CM_LABELS  = ["No Drop", "Drop"]
SEUIL_DBM  = -6.0
HORIZON    = 5


def _build_rsrp_drop_label(fe_out_dir: str) -> pd.Series:
    """
    Compute rsrp_drop binary label from df_final_fe.parquet.
    rsrp_drop=1 when RSRP drops > 6 dBm within the next 5 measurements.
    """
    df_fe = pd.read_parquet(
        os.path.join(fe_out_dir, "df_final_fe.parquet"),
        columns=["rsrp", "session_id", "source_folder", "device"],
    )
    df_fe = df_fe.reset_index(drop=True)
    df_fe["rsrp_drop"] = 0

    print(f"  Seuil={SEUIL_DBM} dBm | Horizon={HORIZON}")
    for env, cle in CONFIGS.items():
        if cle not in df_fe.columns:
            continue
        mask_env = df_fe["source_folder"] == env
        for _, grp in df_fe[mask_env].groupby(cle):
            rsrp_v = grp["rsrp"].values
            idxs   = grp.index
            n      = len(rsrp_v)
            for i in range(n - HORIZON):
                if (rsrp_v[i + 1: i + 1 + HORIZON].min() - rsrp_v[i]) < SEUIL_DBM:
                    df_fe.at[idxs[i], "rsrp_drop"] = 1
        nd = df_fe.loc[mask_env, "rsrp_drop"].sum()
        print(f"    {env}: {nd:,} drops ({nd / mask_env.sum() * 100:.1f}%)")

    total_drop = df_fe["rsrp_drop"].sum()
    total      = len(df_fe)
    print(f"  TOTAL {total_drop:,}/{total:,} ({total_drop / total * 100:.2f}%)")
    return df_fe["rsrp_drop"]


def _save_cm(cm, title, path, labels, cmap="Blues"):
    fig, ax = plt.subplots(figsize=(6, 5))
    sns.heatmap(cm, annot=True, fmt="d", cmap=cmap,
                xticklabels=labels, yticklabels=labels,
                linewidths=0.5, ax=ax, annot_kws={"size": 14, "weight": "bold"})
    ax.set_xlabel("Predit", fontsize=11)
    ax.set_ylabel("Reel", fontsize=11)
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


def train_dso2(
    pt_out_dir:    str = "PT_output",
    fe_out_dir:    str = "FE_output",
    model_out_dir: str = os.path.join("MODEL_output", "DSO2"),
    skip_deep:     bool = False,
):
    """
    Train all 5 models for DSO2 (RSRP drop prediction).

    Models:
        M1  XGBoost
        M2  LightGBM
        M3  Random Forest
        M4  BiLSTM          (skipped if skip_deep=True)
        M5  TabNet          (skipped if skip_deep=True)

    Args:
        pt_out_dir:    folder produced by preprocessing.py
        fe_out_dir:    folder produced by feature_engineering.py (for label)
        model_out_dir: output folder for models + metrics
        skip_deep:     set True in CI to skip GPU-heavy models
    """
    os.makedirs(model_out_dir, exist_ok=True)
    assert os.path.exists(pt_out_dir), \
        f" {pt_out_dir} not found -- run preprocessing first!"
    assert os.path.exists(fe_out_dir), \
        f" {fe_out_dir} not found -- run feature_engineering first!"

    # -- Build label -----------------------------------------------------------
    print("=" * 60 + "\n  DSO2 -- Building RSRP Drop label\n" + "=" * 60)
    rsrp_drop_series = _build_rsrp_drop_label(fe_out_dir)

    # -- Load preprocessed features -------------------------------------------
    with open(os.path.join(pt_out_dir, "config.json")) as f:
        config = json.load(f)

    import pyarrow.parquet as pq
    pf = pq.ParquetFile(os.path.join(pt_out_dir, "df_preprocessed.parquet"))
    chunks = []
    for batch in pf.iter_batches(batch_size=100_000, columns=config["cols_X"]):
        chunks.append(batch.to_pandas().astype(np.float32))
    df = pd.concat(chunks, ignore_index=True)
    df["rsrp_drop"] = rsrp_drop_series.values

    idx_train = np.load(os.path.join(pt_out_dir, "idx_train.npy"), allow_pickle=True)
    idx_val   = np.load(os.path.join(pt_out_dir, "idx_val.npy"),   allow_pickle=True)
    idx_test  = np.load(os.path.join(pt_out_dir, "idx_test.npy"),  allow_pickle=True)

    cols_x  = [c for c in config["cols_X"] if c in df.columns and c != "rsrp_drop"]
    y_train = df.loc[idx_train, "rsrp_drop"].values
    y_val   = df.loc[idx_val,   "rsrp_drop"].values
    y_test  = df.loc[idx_test,  "rsrp_drop"].values

    if skip_deep:
        n = 10_000
        pos_mask_tr = y_train == 1
        neg_mask_tr = y_train == 0
        pos_idx_tr  = idx_train[pos_mask_tr]
        neg_idx_tr  = idx_train[neg_mask_tr]
        n_pos = min(len(pos_idx_tr), n // 2)
        n_neg = min(len(neg_idx_tr), n - n_pos)
        idx_train = np.concatenate([pos_idx_tr[:n_pos], neg_idx_tr[:n_neg]])
        y_train   = np.concatenate([np.ones(n_pos), np.zeros(n_neg)])

        pos_idx_v = idx_val[y_val == 1]
        neg_idx_v = idx_val[y_val == 0]
        n_pos_v   = min(len(pos_idx_v), 1000)
        n_neg_v   = min(len(neg_idx_v), 1000)
        idx_val   = np.concatenate([pos_idx_v[:n_pos_v], neg_idx_v[:n_neg_v]])
        y_val     = np.concatenate([np.ones(n_pos_v), np.zeros(n_neg_v)])

        pos_idx_t = idx_test[y_test == 1]
        neg_idx_t = idx_test[y_test == 0]
        n_pos_t   = min(len(pos_idx_t), 1000)
        n_neg_t   = min(len(neg_idx_t), 1000)
        idx_test  = np.concatenate([pos_idx_t[:n_pos_t], neg_idx_t[:n_neg_t]])
        y_test    = np.concatenate([np.ones(n_pos_t), np.zeros(n_neg_t)])

    cols_x  = [c for c in config["cols_X"] if c in df.columns and c != "rsrp_drop"]
    y_train = df.loc[idx_train, "rsrp_drop"].values
    y_val   = df.loc[idx_val,   "rsrp_drop"].values
    y_test  = df.loc[idx_test,  "rsrp_drop"].values

    X_train = df.loc[idx_train, cols_x].values.astype(np.float32)
    X_val   = df.loc[idx_val,   cols_x].values.astype(np.float32)
    X_test  = df.loc[idx_test,  cols_x].values.astype(np.float32)
    del df
    gc.collect()

    ratio = int((1 - y_train.mean()) / max(y_train.mean(), 1e-6))
    print(f" X_train {X_train.shape} | Drop%={y_train.mean()*100:.2f}% | ratio 1:{ratio}")

    all_metrics = []

    # -- M1 : XGBoost ----------------------------------------------------------
    print("=" * 60 + "\n  M1 -- XGBoost DSO2\n" + "=" * 60)
    xgb_d2 = XGBClassifier(
        n_estimators=500, max_depth=6, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8, scale_pos_weight=ratio,
        eval_metric="aucpr", early_stopping_rounds=30, tree_method="hist",
        random_state=42, n_jobs=-1, use_label_encoder=False,
    )
    xgb_d2.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=50)
    y_pred_xgb = xgb_d2.predict(X_test)
    y_prob_xgb = xgb_d2.predict_proba(X_test)[:, 1]
    print(classification_report(y_test, y_pred_xgb, target_names=CM_LABELS))

    metrics_xgb = _metrics_binary("XGBoost", y_test, y_pred_xgb, y_prob_xgb)
    all_metrics.append(metrics_xgb)
    with open(os.path.join(model_out_dir, "xgb_dso2.pkl"), "wb") as f:
        pickle.dump(xgb_d2, f)
    _save_cm(confusion_matrix(y_test, y_pred_xgb),
             "Confusion Matrix -- XGBoost (DSO2)",
             os.path.join(model_out_dir, "cm_xgb_dso2.png"), CM_LABELS, "Blues")

    # -- M2 : LightGBM ---------------------------------------------------------
    print("=" * 60 + "\n  M2 -- LightGBM DSO2\n" + "=" * 60)
    lgbm_d2 = LGBMClassifier(
        n_estimators=500, max_depth=7, learning_rate=0.05, num_leaves=63,
        subsample=0.8, colsample_bytree=0.8, is_unbalance=True,
        metric="average_precision", random_state=42, n_jobs=-1, verbose=-1,
    )
    lgbm_d2.fit(
        X_train, y_train, eval_set=[(X_val, y_val)],
        callbacks=[lgb.early_stopping(30, verbose=False), lgb.log_evaluation(50)],
    )
    y_pred_lgbm = lgbm_d2.predict(X_test)
    y_prob_lgbm = lgbm_d2.predict_proba(X_test)[:, 1]
    print(classification_report(y_test, y_pred_lgbm, target_names=CM_LABELS))

    metrics_lgbm = _metrics_binary("LightGBM", y_test, y_pred_lgbm, y_prob_lgbm)
    all_metrics.append(metrics_lgbm)
    with open(os.path.join(model_out_dir, "lgbm_dso2.pkl"), "wb") as f:
        pickle.dump(lgbm_d2, f)
    _save_cm(confusion_matrix(y_test, y_pred_lgbm),
             "Confusion Matrix -- LightGBM (DSO2)",
             os.path.join(model_out_dir, "cm_lgbm_dso2.png"), CM_LABELS, "Greens")

    # -- M3 : Random Forest ----------------------------------------------------
    print("=" * 60 + "\n  M3 -- Random Forest DSO2\n" + "=" * 60)
    rf_d2 = RandomForestClassifier(
        n_estimators=300, max_depth=15, min_samples_leaf=20,
        max_features="sqrt", class_weight="balanced_subsample",
        max_samples=0.2, random_state=42, n_jobs=-1, verbose=1,
    )
    rf_d2.fit(X_train, y_train)
    y_pred_rf = rf_d2.predict(X_test)
    y_prob_rf = rf_d2.predict_proba(X_test)[:, 1]
    print(classification_report(y_test, y_pred_rf, target_names=CM_LABELS))

    metrics_rf = _metrics_binary("Random Forest", y_test, y_pred_rf, y_prob_rf)
    all_metrics.append(metrics_rf)
    with open(os.path.join(model_out_dir, "rf_dso2.pkl"), "wb") as f:
        pickle.dump(rf_d2, f)
    _save_cm(confusion_matrix(y_test, y_pred_rf),
             "Confusion Matrix -- Random Forest (DSO2)",
             os.path.join(model_out_dir, "cm_rf_dso2.png"), CM_LABELS, "Oranges")

    # -- M4 : BiLSTM -----------------------------------------------------------
    if not skip_deep:
        print("=" * 60 + "\n  M4 -- BiLSTM DSO2\n" + "=" * 60)
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

        lstm_d2 = KModel(inputs=inp, outputs=out, name="BiLSTM_DSO2")
        lstm_d2.compile(
            optimizer=Adam(1e-3), loss="binary_crossentropy", metrics=["AUC"]
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
        all_metrics.append(metrics_lstm)
        lstm_d2.save(os.path.join(model_out_dir, "lstm_dso2.h5"))
        _save_cm(confusion_matrix(y_test, y_pred_lstm),
                 "Confusion Matrix -- BiLSTM (DSO2)",
                 os.path.join(model_out_dir, "cm_lstm_dso2.png"), CM_LABELS, "Reds")

    # -- M5 : TabNet -----------------------------------------------------------
    if not skip_deep:
        print("=" * 60 + "\n  M5 -- TabNet DSO2\n" + "=" * 60)
        import torch
        from pytorch_tabnet.tab_model import TabNetClassifier
        from pytorch_tabnet.pretraining import TabNetPretrainer

        N_TN    = min(100_000, len(X_train))
        idx_tn  = np.random.choice(len(X_train), N_TN, replace=False)
        X_tr_tn = X_train[idx_tn].astype(np.float32)
        X_va_tn = X_val.astype(np.float32)
        X_te_tn = X_test.astype(np.float32)
        y_tr_tn = y_train[idx_tn]

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

        tabnet_d2 = TabNetClassifier(
            n_d=16, n_a=16, n_steps=3, gamma=1.5,
            n_independent=2, n_shared=2, mask_type="entmax",
            optimizer_fn=torch.optim.Adam,
            optimizer_params={"lr": 2e-3},
            verbose=0, seed=42,
        )
        tabnet_d2.fit(
            X_train=X_tr_tn[:512], y_train=y_tr_tn[:512].astype(int),
            max_epochs=1, batch_size=512, virtual_batch_size=512,
        )
        tabnet_d2.load_weights_from_unsupervised(pt_d2)
        tabnet_d2.verbose = 10
        tabnet_d2.fit(
            X_train=X_tr_tn, y_train=y_tr_tn.astype(int),
            eval_set=[(X_va_tn, y_val.astype(int))],
            eval_metric=["auc"],
            max_epochs=30, patience=5,
            batch_size=2048, virtual_batch_size=256,
            weights=1,
        )

        y_pred_tn = tabnet_d2.predict(X_te_tn)
        y_prob_tn = tabnet_d2.predict_proba(X_te_tn)[:, 1]
        print(classification_report(y_test, y_pred_tn, target_names=CM_LABELS))

        metrics_tn = _metrics_binary("TabNet", y_test, y_pred_tn, y_prob_tn)
        all_metrics.append(metrics_tn)
        tabnet_d2.save_model(os.path.join(model_out_dir, "tabnet_dso2"))

    # -- Save summary ----------------------------------------------------------
    with open(os.path.join(model_out_dir, "results_dso2.json"), "w") as f:
        json.dump(all_metrics, f, indent=2)

    df_results = pd.DataFrame(all_metrics).set_index("model")
    print("\n" + df_results.to_string())
    best = df_results["f1"].idxmax()
    print(f"\nBest (F1) : {best} -> {df_results.loc[best, 'f1']:.4f}")
    print("\nDSO2 training complete")
    return all_metrics


if __name__ == "__main__":
    train_dso2()