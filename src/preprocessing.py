# src/preprocessing.py
# Converted from NB3_Preprocessing.ipynb
# Pipeline: NB2_FE → NB3_Preprocessing → NB4_Modeling

import os
import gc
import json
import pickle
import warnings

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler, RobustScaler

warnings.filterwarnings('ignore')


def run_preprocessing(
    fe_out_dir: str = "FE_output",
    pt_out_dir: str = "PT_output",
):
    """
    Full preprocessing pipeline for DoNext 5G Handover dataset.

    Steps:
        PT-0  Load df_final_fe.parquet
        PT-1  Drop useless / leakage columns
        PT-2  Robust NaN imputation
        PT-3  Categorical label encoding
        PT-4  IQR Winsorization (iperf features only)
        PT-5  Temporal split 70/15/15
        PT-6  Hybrid normalisation (MinMax + Robust)
        PT-7  Save all outputs to PT_output/

    Args:
        fe_out_dir: folder that contains df_final_fe.parquet (from NB2)
        pt_out_dir: folder where all outputs will be written
    """

    os.makedirs(pt_out_dir, exist_ok=True)
    assert os.path.exists(fe_out_dir), \
        f" {fe_out_dir} not found — run NB2 / feature_engineering first!"

    # ── PT-0 : Load ──────────────────────────────────────────────────────────
    print("=" * 60)
    print("  PT-0 — LOADING")
    print("=" * 60)

    df_final = pd.read_parquet(os.path.join(fe_out_dir, "df_final_fe.parquet"))
    print(f"{len(df_final):,} rows × {df_final.shape[1]} cols")
    print(f"   RAM estimate : {df_final.memory_usage(deep=True).sum() / 1e6:.0f} MB")

    df = df_final.copy()
    del df_final
    gc.collect()
    print(f"Working dataset : {len(df):,} × {df.shape[1]}")

    # ── PT-1 : Drop columns ──────────────────────────────────────────────────
    print("=" * 60)
    print("  PT-1 — DROP COLUMNS")
    print("=" * 60)

    cols_100_nan   = []
    cols_unique_1  = []
    cols_low_dispo = []
    total_cols     = len(df.columns)

    for i, col in enumerate(df.columns):
        if i % 10 == 0:
            print(f"  Progress : {i}/{total_cols}")
        try:
            s_sample = df[col].sample(min(200_000, len(df)), random_state=42)

            if s_sample.isna().mean() == 1.0:
                cols_100_nan.append(col)
                continue
            if s_sample.nunique(dropna=True) <= 1:
                cols_unique_1.append(col)
                continue
            if (s_sample.notna().mean() < 0.05
                    and col not in ["handover", "ho_type"]):
                cols_low_dispo.append(col)
        except Exception:
            continue

    print("  Analysis done ")

    cols_id = [c for c in
               ["source_file", "id", "refsig_id", "username",
                "session_start_timestamp", "devicename"]
               if c in df.columns]

    cols_leakage = [c for c in
                    ["cell_index", "physical_cellid", "earfcn_prev",
                     "mnc_prev", "physical_cellid_prev"]
                    if c in df.columns]

    all_drop = list(set(cols_100_nan + cols_unique_1 + cols_id
                        + cols_leakage + cols_low_dispo))
    print(f"  Columns to drop : {len(all_drop)}")

    df = df.drop(columns=all_drop, errors="ignore")
    print(f"Remaining columns : {df.shape[1]}")

    # ── PT-2 : Robust NaN imputation ─────────────────────────────────────────
    print("=" * 60)
    print("  PT-2 — ROBUST IMPUTATION")
    print("=" * 60)

    # Clean object columns
    for col in df.columns:
        if df[col].dtype == "object":
            df[col] = df[col].replace(["", "-", " "], np.nan)

    # Binary presence flags
    features_map = {
        "has_gps":   "latitude",
        "is_5g":     "ss_rsrp",
        "has_iperf": "datarate_mean",
        "has_neigh": "nb_neighbors_mean",
    }
    for feat, col in features_map.items():
        df[feat] = df[col].notna().astype("int8") if col in df.columns else 0

    # Radio KPI 3GPP ranges
    PLAGES_3GPP = {
        "rsrp":     (-140, -44),
        "rsrq":     (-19.5, -3),
        "sinr":     (-23, 40),
        "rssi":     (-120, 0),
        "cqi":      (0, 15),
        "tx_power": (-40, 23),
    }
    for col, (lo, hi) in PLAGES_3GPP.items():
        if col not in df.columns:
            continue
        df.loc[df[col].notna() & ~df[col].between(lo, hi), col] = np.nan
        med = df[col].median()
        if np.isnan(med):
            med = lo
        df[col] = df[col].fillna(med).clip(lo, hi)

    # GPS columns
    gps_cols = ["latitude", "longitude", "altitude", "location_accuracy",
                "velocity", "velocity_accuracy", "bearing", "bearing_accuracy"]
    for col in gps_cols:
        if col in df.columns:
            med = df[col].median()
            df[col] = df[col].fillna(med if not np.isnan(med) else 0)

    # Numeric columns
    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]) and df[col].isna().any():
            med = df[col].median()
            df[col] = df[col].fillna(med if not np.isnan(med) else 0)

    # Datetime columns
    for col in df.columns:
        if "datetime64" in str(df[col].dtype):
            df[col] = df[col].fillna(pd.Timestamp("1970-01-01"))

    # Categorical columns
    for col in df.columns:
        if df[col].dtype == "object" and df[col].isna().any():
            mode = df[col].mode()
            df[col] = df[col].fillna(mode[0] if len(mode) > 0 else "unknown")

    nan_total = df.isna().sum().sum()
    print(f"\n  Remaining NaN : {nan_total}")
    print(" OK" if nan_total == 0 else "  NaN remaining")
    print(f"  Shape : {df.shape}")

    # ── PT-3 : Categorical encoding ──────────────────────────────────────────
    print("=" * 60)
    print("  PT-3 — CATEGORICAL ENCODING")
    print("=" * 60)

    df = df.replace(["", " ", "-", "NA", "N/A", "null"], pd.NA)

    MAPPINGS = {
        "source_folder": {"static": 0, "mobile": 1, "hbahn": 2},
        "ho_type": {
            "no_handover": 0, "intra_freq": 1, "inter_freq": 2,
            "inter_RAT_NR": 3, "inter_operator": 4,
            "intra_freq_pci": 5, "inter_freq_pci": 6, "ho_non_type": 7,
        },
        "network":            {"2G": 0, "3G": 1, "4G": 2, "5G NSA": 3},
        "network_neighboring": {"2G": 0, "3G": 1, "4G": 2, "5G": 3},
        "MNO":                {"A": 0, "B": 1, "C": 2},
        "MNO_neighboring":    {"A": 0, "B": 1, "C": 2},
        "protocol":           {"tcp": 0, "udp": 1},
        "device": {
            "armv7l_RM500Q-GL": 0, "armv7l_none": 1,
            "o1s_SM-G991B": 2,    "r0s_SM-S901B": 3,
            "x86_64_RM500Q-GL": 4, "x86_64_RM520N-EU": 5,
        },
    }

    encoded_cols = []
    for col, mapping in MAPPINGS.items():
        if col in df.columns:
            df[f"{col}_enc"] = df[col].map(mapping).fillna(-1).astype(int)
            encoded_cols.append(col)
            print(f"  {col:<25} → {col}_enc  "
                  f"(unique: {df[f'{col}_enc'].nunique()})")

    if "server_ip" in df.columns:
        df["server_ip_enc"] = pd.factorize(df["server_ip"])[0]
        encoded_cols.append("server_ip")
        print(f"  {'server_ip':<25} → server_ip_enc")

    for col in df.select_dtypes(include="object").columns:
        if col not in encoded_cols:
            df[f"{col}_enc"] = pd.factorize(df[col])[0]
            print(f"  {col:<25} → {col}_enc (auto)")

    df.drop(columns=[c for c in encoded_cols if c in df.columns], inplace=True)

    with open(os.path.join(pt_out_dir, "mappings.json"), "w") as f:
        json.dump(MAPPINGS, f, indent=2)

    print("\n PT-3 done")

    # ── PT-4 : IQR Winsorization ─────────────────────────────────────────────
    print("=" * 60)
    print("  PT-4 — OUTLIERS : IQR Winsorization (iperf only)")
    print("=" * 60)

    cols_winsor = [c for c in
                   ["pkt_error_mean", "datarate_max", "tcp_rtt_mean",
                    "retrans_mean", "datarate_mean"]
                   if c in df.columns]

    print(f"  Columns : {cols_winsor}")
    for col in cols_winsor:
        Q1, Q3 = df[col].quantile(0.25), df[col].quantile(0.75)
        IQR    = Q3 - Q1
        lo, hi = Q1 - 1.5 * IQR, Q3 + 1.5 * IQR
        n_cap  = ((df[col] < lo) | (df[col] > hi)).sum()
        df[col] = df[col].clip(lower=lo, upper=hi)
        print(f"  {col:<25} borne_hi={hi:>10.1f}  capped={n_cap:,}")

    print("\n PT-4 done")

    # ── PT-5 : Temporal split 70/15/15 ───────────────────────────────────────
    print("=" * 60)
    print("  PT-5 — TEMPORAL SPLIT 70/15/15")
    print("=" * 60)
    gc.collect()

    y_binary     = df["handover"].values

    cols_X = [c for c in df.columns
              if c not in ["handover", "ho_type_enc"]]
    print(f"  Features (X) : {len(cols_X)}")

    idx_trains, idx_vals, idx_tests = [], [], []
    y_trains,   y_vals,   y_tests   = [], [], []

    print(f'  {"Env":<10} {"Total":>10} {"Train":>10} '
          f'{"Val":>10} {"Test":>10} {"HO%":>8}')
    print("  " + "─" * 58)

    for env_code, env_name in [(0, "static"), (1, "mobile"), (2, "hbahn")]:
        idx_env = df.index[df["source_folder_enc"] == env_code].tolist()
        n = len(idx_env)
        if n == 0:
            print(f"  {env_name:<10} — no data")
            continue
        n_train = int(n * 0.70)
        n_val   = int(n * 0.15)

        idx_trains.append(idx_env[:n_train])
        idx_vals.append(  idx_env[n_train:n_train + n_val])
        idx_tests.append( idx_env[n_train + n_val:])

        y_env = y_binary[idx_env]
        y_trains.append(y_env[:n_train])
        y_vals.append(  y_env[n_train:n_train + n_val])
        y_tests.append( y_env[n_train + n_val:])

        print(f"  {env_name:<10} {n:>10,} {n_train:>10,} {n_val:>10,} "
              f"{n - n_train - n_val:>10,} "
              f"{y_env[:n_train].mean() * 100:>7.2f}%")
        gc.collect()

    idx_train_all = sum(idx_trains, [])
    idx_val_all   = sum(idx_vals,   [])
    idx_test_all  = sum(idx_tests,  [])
    y_train = np.concatenate(y_trains)
    y_val   = np.concatenate(y_vals)
    y_test  = np.concatenate(y_tests)

    print(f"\n  Train : {len(idx_train_all):,}  |  "
          f"Val : {len(idx_val_all):,}  |  "
          f"Test : {len(idx_test_all):,}")
    print("\n PT-5 done")

    # ── PT-6 : Hybrid normalisation ──────────────────────────────────────────
    print("=" * 60)
    print("  PT-6 — HYBRID NORMALISATION")
    print("=" * 60)

    def numeric_only(dataframe, cols):
        return [c for c in cols
                if pd.api.types.is_numeric_dtype(dataframe[c])]

    cols_no_norm = [c for c in
                    ["source_folder_enc", "network_enc", "MNO_enc",
                     "device_enc", "has_gps", "is_5g", "has_iperf",
                     "has_neigh", "session_id", "passive_id",
                     "timestamp", "timestamp_day",
                     "week_of_year", "day_of_week"]
                    if c in cols_X]

    cols_robust = numeric_only(df, [c for c in
                                    ["datarate_mean", "datarate_max",
                                     "tcp_rtt_mean", "retrans_mean",
                                     "pkt_error_mean", "packet_loss_mean",
                                     "mean_latency", "mean_dev_latency",
                                     "min_latency", "max_latency",
                                     "nb_neighbors_pid", "nb_neighbors_mean",
                                     "nb_neighbors_max"]
                                    if c in cols_X
                                    and c not in cols_no_norm])

    cols_minmax = numeric_only(df, [c for c in cols_X
                                    if c not in cols_no_norm
                                    and c not in cols_robust])

    X_train_ref = df.loc[idx_train_all, :]

    scaler_mm = MinMaxScaler()
    if cols_minmax:
        scaler_mm.fit(X_train_ref[cols_minmax])
        df[cols_minmax] = scaler_mm.transform(df[cols_minmax])
    scaler_rb = RobustScaler()
    if cols_robust:
        scaler_rb.fit(X_train_ref[cols_robust])
        df[cols_robust] = scaler_rb.transform(df[cols_robust])

    print(f"  Excluded  : {len(cols_no_norm)}")
    print(f"  Min-Max   : {len(cols_minmax)}")
    print(f"  Robust    : {len(cols_robust)}")
    print("\n✅ PT-6 done")

    # ── PT-7 : Save outputs ───────────────────────────────────────────────────
    print("=" * 60)
    print("  PT-7 — SAVE OUTPUTS")
    print("=" * 60)

    np.save(os.path.join(pt_out_dir, "idx_train.npy"), np.array(idx_train_all))
    np.save(os.path.join(pt_out_dir, "idx_val.npy"),   np.array(idx_val_all))
    np.save(os.path.join(pt_out_dir, "idx_test.npy"),  np.array(idx_test_all))
    np.save(os.path.join(pt_out_dir, "y_train.npy"),   y_train)
    np.save(os.path.join(pt_out_dir, "y_val.npy"),     y_val)
    np.save(os.path.join(pt_out_dir, "y_test.npy"),    y_test)

    path_final = os.path.join(pt_out_dir, "df_preprocessed.parquet")
    df.to_parquet(path_final, index=False, compression="snappy")

    with open(os.path.join(pt_out_dir, "scaler_minmax.pkl"), "wb") as f:
        pickle.dump(scaler_mm, f)
    with open(os.path.join(pt_out_dir, "scaler_robust.pkl"), "wb") as f:
        pickle.dump(scaler_rb, f)

    config = {
        "cols_X":        cols_X,
        "cols_minmax":   cols_minmax,
        "cols_robust":   cols_robust,
        "cols_no_norm":  cols_no_norm,
        "n_train":       len(idx_train_all),
        "n_val":         len(idx_val_all),
        "n_test":        len(idx_test_all),
        "ho_rate_train": float(y_train.mean()),
    }
    with open(os.path.join(pt_out_dir, "config.json"), "w") as f:
        json.dump(config, f, indent=2)

    size = os.path.getsize(path_final) / 1e6
    print(f"  df_preprocessed.parquet : {len(df):,} rows × "
          f"{df.shape[1]} cols → {size:.1f} MB")
    print(f"  y_train {y_train.shape}  HO={y_train.mean() * 100:.2f}%")
    print(f"  y_val   {y_val.shape}    HO={y_val.mean() * 100:.2f}%")
    print(f"  y_test  {y_test.shape}   HO={y_test.mean() * 100:.2f}%")
    print("\n PREPROCESSING COMPLETE → ready for NB4 / modeling")


if __name__ == "__main__":
    run_preprocessing()