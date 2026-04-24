# src/feature_engineering.py
# Converted from NB2_Handover_FE-2.ipynb
# Pipeline: FE_data/ → NB2_FE → FE_output/df_final_fe.parquet → NB3_Preprocessing

import os
import gc
import time
import warnings

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from sklearn.cluster import DBSCAN
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import MinMaxScaler

warnings.filterwarnings("ignore")

# ── Constants ────────────────────────────────────────────────────────────────
CONFIGS      = {"static": "session_id", "mobile": "device", "hbahn": "device"}
ECI_COL      = "cell_index"
RSRP_COL     = "rsrp"
VELOCITY_COL = "velocity"
SESSION_COL  = "session_id"


def run_feature_engineering(
    fe_data_dir: str = "FE_data",
    fe_out_dir:  str = "FE_output",
):
    """
    Full Feature Engineering pipeline for DoNext 5G Handover dataset.

    Steps:
        FE-1  Load cell_data.parquet, sort by session × timestamp
        FE-2  Vectorised handover detection  (O(n))
        FE-3  3GPP TR 38.300 handover typing
        FE-4  Join latency / iperf / neighboring tables
        FE-4b KPI gaps  (rsrp_gap = Event A3 trigger proxy)
        FE-4c Temporal sliding window T-5  (for LSTM / XGBoost)
        FE-5  Spatio-temporal ST-DBSCAN clustering
        FE-6  cluster_id_clean + risk_level post-processing
        FE-7  Save df_final_fe.parquet + df_ho.parquet

    Args:
        fe_data_dir : folder containing raw parquet files from NB1
        fe_out_dir  : folder where df_final_fe.parquet is written
    """

    os.makedirs(fe_out_dir, exist_ok=True)
    assert os.path.exists(fe_data_dir), (
        f"❌ {fe_data_dir} not found — run NB1_EDA first!"
    )

    # ── FE-1 : Load & sort cell_data ─────────────────────────────────────────
    print("🔹 Loading cell_data...")
    df_cell = pd.read_parquet(os.path.join(fe_data_dir, "cell_data.parquet"))
    print(f"  ✅ {len(df_cell):,} rows × {df_cell.shape[1]} cols")

    ts_col = next(
        (c for c in ["timestampstart", "timestamp", "timestamp_day"]
         if c in df_cell.columns),
        None,
    )
    print(f"  Timestamp column : {ts_col}")

    if ts_col:
        df_cell = (
            df_cell
            .sort_values([SESSION_COL, ts_col], na_position="last")
            .reset_index(drop=True)
        )
        print("  ✅ Sorted by session × timestamp")
    else:
        print("  ⚠️  No timestamp — order not guaranteed")

    # ── FE-2 : Vectorised handover detection ─────────────────────────────────
    print("\n" + "=" * 60)
    print("  FE-2 — HANDOVER DETECTION")
    print("=" * 60)

    df_ho             = df_cell.copy()
    df_ho["handover"] = 0

    for env, cle in CONFIGS.items():
        mask_env = (df_ho["source_folder"] == env).values
        idx      = np.where(mask_env)[0]
        if len(idx) == 0:
            continue

        print(f"  {env} — session key : {cle}")

        sub         = df_ho.iloc[idx][[cle, ECI_COL]].copy()
        sub["oidx"] = idx
        sub         = sub.sort_values([cle, "oidx"])

        eci_v = sub[ECI_COL].values
        cle_v = sub[cle].values

        ho_v       = (eci_v != np.roll(eci_v, 1)).astype(int)
        grp_change = (cle_v != np.roll(cle_v, 1))
        ho_v[grp_change] = 0  # first record of each session → no HO

        sub["handover"] = ho_v
        sub = sub.sort_values("oidx")
        df_ho.iloc[idx, df_ho.columns.get_loc("handover")] = sub["handover"].values

        n, h = len(idx), int(sub["handover"].sum())
        print(f"     → {n:,} rows | {h:,} HO ({h / max(n, 1) * 100:.1f}%)")

    total     = len(df_ho)
    n_ho      = int(df_ho["handover"].sum())
    ho_pct    = n_ho / total * 100
    imbalance = int((total - n_ho) / max(n_ho, 1))

    print(f"\n  TOTAL : {total:,} rows | {n_ho:,} HO ({ho_pct:.2f}%)")
    print(f"  Imbalance ratio : 1:{imbalance}")
    if imbalance > 5:
        print("  ⚠️  High imbalance → use class_weight / SMOTE / Focal Loss")

    # ── FE-3 : 3GPP TR 38.300 handover typing ────────────────────────────────
    print("\n" + "=" * 60)
    print("  FE-3 — HANDOVER TYPING (3GPP)")
    print("=" * 60)
    print("  Computing previous-cell references (shift per session)...")

    for col_ref in ["earfcn", "mnc", "physical_cellid"]:
        col_prev = f"{col_ref}_prev"
        df_ho[col_prev] = np.nan
        if col_ref not in df_ho.columns:
            continue
        for env, cle in CONFIGS.items():
            mask_env = df_ho["source_folder"] == env
            if cle in df_ho.columns:
                df_ho.loc[mask_env, col_prev] = (
                    df_ho[mask_env].groupby(cle)[col_ref].shift(1)
                )

    df_ho["ho_type"] = "no_handover"
    mask_ho     = df_ho["handover"] == 1
    mask_earfcn = df_ho["earfcn"].notna()           & df_ho["earfcn_prev"].notna()
    mask_mnc    = df_ho["mnc"].notna()              & df_ho["mnc_prev"].notna()
    mask_pci    = (df_ho["physical_cellid"].notna() & df_ho["physical_cellid_prev"].notna())
    mask_5g     = (
        df_ho["ss_rsrp"].notna()
        if "ss_rsrp" in df_ho.columns
        else pd.Series(False, index=df_ho.index)
    )

    # Rule 1 : inter-operator
    df_ho.loc[
        mask_ho & mask_mnc & (df_ho["mnc"] != df_ho["mnc_prev"]),
        "ho_type",
    ] = "inter_operator"
    # Rule 2 : inter-freq
    df_ho.loc[
        mask_ho & mask_earfcn
        & (df_ho["earfcn"] != df_ho["earfcn_prev"])
        & (df_ho["ho_type"] == "no_handover"),
        "ho_type",
    ] = "inter_freq"
    # Rule 3 : intra-freq
    df_ho.loc[
        mask_ho & mask_earfcn
        & (df_ho["earfcn"] == df_ho["earfcn_prev"])
        & (df_ho["ho_type"] == "no_handover"),
        "ho_type",
    ] = "intra_freq"
    # Rule 4 : inter-RAT NR (5G)
    df_ho.loc[
        mask_ho & mask_5g & (df_ho["ho_type"] == "no_handover"),
        "ho_type",
    ] = "inter_RAT_NR"
    # Fallback
    df_ho.loc[mask_ho & (df_ho["ho_type"] == "no_handover"), "ho_type"] = "ho_non_type"
    mask_non = (df_ho["ho_type"] == "ho_non_type") & mask_ho
    df_ho.loc[
        mask_non & mask_pci
        & (df_ho["physical_cellid"] == df_ho["physical_cellid_prev"]),
        "ho_type",
    ] = "intra_freq_pci"
    df_ho.loc[
        mask_non & mask_pci
        & (df_ho["physical_cellid"] != df_ho["physical_cellid_prev"]),
        "ho_type",
    ] = "inter_freq_pci"

    print("\n  Handover type distribution :")
    print(f'  {"Type":<20} {"N":>10} {"% of HO":>10}')
    print("  " + "─" * 44)
    for ht, cnt in df_ho[df_ho["handover"] == 1]["ho_type"].value_counts().items():
        print(f"  {ht:<20} {cnt:>10,} {cnt / n_ho * 100:>9.1f}%")

    # Save df_ho
    path_ho = os.path.join(fe_data_dir, "df_ho.parquet")
    df_ho.to_parquet(path_ho, index=False, compression="snappy")
    size_ho = os.path.getsize(path_ho) / 1e6
    print(f"\n✅ df_ho saved : {len(df_ho):,} rows × {df_ho.shape[1]} cols → {size_ho:.1f} MB")

    del df_cell
    gc.collect()

    # ── FE-4 : Join complementary tables ─────────────────────────────────────
    print("\n" + "=" * 60)
    print("  FE-4 — JOINS (latency / iperf / neighboring)")
    print("=" * 60)
    print("🔹 Loading complementary tables...")

    # Neighboring
    cols_neigh = ["device", "source_folder", "passive_id",
                  "rsrp_neighboring", "rsrq_neighboring",
                  "rssi_neighboring", "MNO_neighboring"]
    schema_n   = pq.read_schema(os.path.join(fe_data_dir, "neighboring_data.parquet")).names
    cols_neigh = [c for c in cols_neigh if c in schema_n]
    df_neigh   = pd.read_parquet(
        os.path.join(fe_data_dir, "neighboring_data.parquet"), columns=cols_neigh
    )
    print(f"  ✅ neighboring : {len(df_neigh):,} rows × {df_neigh.shape[1]} cols")

    # Latency
    cols_lat  = ["device", "source_folder", "mean_latency", "mean_dev_latency",
                 "min_latency", "max_latency", "packet_loss"]
    schema_l  = pq.read_schema(os.path.join(fe_data_dir, "latency_data.parquet")).names
    cols_lat  = [c for c in cols_lat if c in schema_l]
    df_lat    = pd.read_parquet(
        os.path.join(fe_data_dir, "latency_data.parquet"), columns=cols_lat
    )
    print(f"  ✅ latency : {len(df_lat):,} rows")

    # iperf
    cols_iperf = ["device", "source_folder", "datarate", "tcp_mean_rtt_0",
                  "retransmissions", "packet_error_rate"]
    schema_i   = pq.read_schema(os.path.join(fe_data_dir, "iperf_data.parquet")).names
    cols_iperf = [c for c in cols_iperf if c in schema_i]
    df_iperf   = pd.read_parquet(
        os.path.join(fe_data_dir, "iperf_data.parquet"), columns=cols_iperf
    )
    print(f"  ✅ iperf : {len(df_iperf):,} rows")

    df_final = df_ho.copy()

    # 1️⃣ Latency
    lat_agg = df_lat.groupby(["device", "source_folder"]).agg(
        mean_latency     =("mean_latency",     "mean"),
        mean_dev_latency =("mean_dev_latency", "mean"),
        min_latency      =("min_latency",      "mean"),
        max_latency      =("max_latency",      "mean"),
        packet_loss_mean =("packet_loss",      "mean"),
    ).reset_index()
    df_final = df_final.merge(lat_agg, on=["device", "source_folder"], how="left")
    print(f"  Latency joined : {df_final['mean_latency'].notna().mean() * 100:.1f}% available")

    # 2️⃣ iperf
    iperf_agg = df_iperf.groupby(["device", "source_folder"]).agg(
        datarate_mean  =("datarate",          "mean"),
        datarate_max   =("datarate",          "max"),
        tcp_rtt_mean   =("tcp_mean_rtt_0",    "mean"),
        retrans_mean   =("retransmissions",   "mean"),
        pkt_error_mean =("packet_error_rate", "mean"),
    ).reset_index()
    df_final = df_final.merge(iperf_agg, on=["device", "source_folder"], how="left")
    print(f"  iperf joined   : {df_final['datarate_mean'].notna().mean() * 100:.1f}% available")

    # 3️⃣ Neighboring
    if "passive_id" in df_neigh.columns:
        neigh_by_pid = (
            df_neigh[df_neigh["passive_id"].notna()]
            .groupby("passive_id").agg(
                rsrp_best_neighbor =("rsrp_neighboring", "max"),
                rsrp_mean_neighbor =("rsrp_neighboring", "mean"),
                rsrq_mean_neighbor =("rsrq_neighboring", "mean"),
                nb_neighbors_pid   =("rsrp_neighboring", "count"),
            ).reset_index()
        )
        if "passive_id" in df_final.columns:
            df_final = df_final.merge(neigh_by_pid, on="passive_id", how="left")
        else:
            neigh_dev = (
                df_neigh.groupby("device").agg(
                    rsrp_best_neighbor =("rsrp_neighboring", "max"),
                    rsrp_mean_neighbor =("rsrp_neighboring", "mean"),
                    nb_neighbors_pid   =("rsrp_neighboring", "count"),
                ).reset_index()
            )
            df_final = df_final.merge(neigh_dev, on="device", how="left")

    pct_n = df_final["rsrp_best_neighbor"].notna().mean() * 100
    print(f"  Neighboring    : {pct_n:.1f}% available")
    print(f"\n  df_final : {len(df_final):,} rows × {df_final.shape[1]} cols")

    # ── FE-4b : KPI Gaps ─────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  FE-4b — KPI GAPS (Event A3 proxy)")
    print("=" * 60)

    kpi_list = ["rsrp", "rsrq", "rssi", "sinr", "cqi", "tx_power"]
    print(f'  {"KPI":<12} {"Gap HO=0":>15} {"Gap HO=1":>15} {"Avail %":>10}')
    print("  " + "─" * 55)

    for kpi in kpi_list:
        neigh_col = f"{kpi}_best_neighbor"
        if neigh_col in df_final.columns:
            df_final[f"{kpi}_gap"] = df_final[neigh_col] - df_final[kpi]
        elif kpi in df_final.columns:
            df_final[f"{kpi}_gap"] = df_final[kpi]

        gap_col = f"{kpi}_gap"
        if gap_col not in df_final.columns:
            continue
        dispo = df_final[gap_col].notna().mean() * 100
        m0    = df_final.loc[df_final["handover"] == 0, gap_col].mean()
        m1    = df_final.loc[df_final["handover"] == 1, gap_col].mean()
        print(f"  {kpi:<12} {m0:>15.3f} {m1:>15.3f} {dispo:>9.1f}%")

    # ── FE-4c : Temporal sliding window T-5 ──────────────────────────────────
    print("\n" + "=" * 60)
    print("  FE-4c — TEMPORAL WINDOW T-5")
    print("=" * 60)

    FEATURES_WINDOW = [f for f in
                       ["rsrp", "rsrq", "sinr", "rssi", "cqi", "tx_power",
                        "ss_rsrp", "ss_rsrq", "ss_sinr"]
                       if f in df_final.columns]
    N_STEPS = 5

    print(f"  Window features : {FEATURES_WINDOW}")
    print(f"  Steps : T-1 → T-{N_STEPS}")
    print(f"  New columns : {len(FEATURES_WINDOW) * N_STEPS}")

    for feat in FEATURES_WINDOW:
        for step in range(1, N_STEPS + 1):
            df_final[f"{feat}_T{step}"] = np.nan

    for env, cle in CONFIGS.items():
        mask_env = df_final["source_folder"] == env
        print(f"  {env} — {mask_env.sum():,} rows")
        for feat in FEATURES_WINDOW:
            for step in range(1, N_STEPS + 1):
                df_final.loc[mask_env, f"{feat}_T{step}"] = (
                    df_final[mask_env].groupby(cle)[feat].shift(step).values
                )
        gc.collect()

    print(f"\n  df_final after FE : {len(df_final):,} rows × {df_final.shape[1]} cols")

    # ── FE-5 : ST-DBSCAN clustering ──────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  FE-5 — SPATIO-TEMPORAL CLUSTERING (ST-DBSCAN)")
    print("=" * 60)

    df_final["cluster_id"]   = -2
    df_final["cluster_risk"] = 0.0

    mask_mobile = df_final["source_folder"].isin(["mobile", "hbahn"])
    mask_gps    = df_final["latitude"].notna() & df_final["longitude"].notna()
    mask_valid  = mask_mobile & mask_gps

    n_total  = len(df_final)
    n_valid  = mask_valid.sum()
    n_static = (~mask_mobile).sum()

    print(f"  Total rows             : {n_total:>12,}")
    print(f"  Static (cluster=-2)    : {n_static:>12,} ({n_static / n_total * 100:.1f}%)")
    print(f"  Mobile+Hbahn with GPS  : {n_valid:>12,} ({n_valid / n_total * 100:.1f}%)")

    if n_valid < 1000:
        print("  ⚠️  Not enough GPS data → clustering skipped")
    else:
        cols_cluster = []

        gps_ok  = [c for c in ["latitude", "longitude"] if c in df_final.columns]
        kpi_ok  = [c for c in ["rsrp", "rsrq", "sinr"] if c in df_final.columns]
        time_ok = [c for c in ["day_of_week", "week_of_year"] if c in df_final.columns]

        if len(gps_ok) == 2:
            cols_cluster += gps_ok
        else:
            print("  ❌ GPS not available → skipping clustering")
            cols_cluster = None

        if cols_cluster is not None:
            cols_cluster += kpi_ok
            if "velocity" in df_final.columns:
                cols_cluster.append("velocity")
            cols_cluster += time_ok

            df_sub = df_final.loc[mask_valid, cols_cluster + ["handover"]].copy()

            # Impute residual NaN
            for col in cols_cluster:
                n_nan = df_sub[col].isna().sum()
                if n_nan > 0:
                    med = df_sub[col].median()
                    df_sub[col] = df_sub[col].fillna(med)

            # MinMax normalisation (required for DBSCAN euclidean distance)
            scaler_cluster = MinMaxScaler()
            X_cluster      = scaler_cluster.fit_transform(df_sub[cols_cluster])

            # Subsample for DBSCAN (RAM constraint)
            MAX_DBSCAN = 200_000
            n_sub      = len(X_cluster)

            if n_sub > MAX_DBSCAN:
                print(f"\n  Subsampling for DBSCAN : {n_sub:,} → {MAX_DBSCAN:,}")
                np.random.seed(42)
                idx_sample = np.sort(
                    np.random.choice(n_sub, MAX_DBSCAN, replace=False)
                )
                X_sample = X_cluster[idx_sample]
                y_sample = df_sub["handover"].values[idx_sample]
            else:
                idx_sample = np.arange(n_sub)
                X_sample   = X_cluster
                y_sample   = df_sub["handover"].values

            print("\n  Running DBSCAN (eps=0.05, min_samples=30)...")
            t0            = time.time()
            dbscan        = DBSCAN(eps=0.05, min_samples=30,
                                   metric="euclidean", n_jobs=-1)
            labels_sample = dbscan.fit_predict(X_sample)
            print(f"  DBSCAN duration : {time.time() - t0:.1f}s")

            n_clusters  = len(set(labels_sample)) - (1 if -1 in labels_sample else 0)
            n_noise     = (labels_sample == -1).sum()
            n_clustered = (labels_sample != -1).sum()
            print(f"  Clusters found    : {n_clusters}")
            print(f"  Clustered points  : {n_clustered:,} ({n_clustered / len(X_sample) * 100:.1f}%)")
            print(f"  Outliers (=-1)    : {n_noise:,}")

            # Compute HO rate per cluster
            cluster_profiles = {}
            unique_labels    = sorted(set(labels_sample))
            for lbl in unique_labels:
                mask_lbl = labels_sample == lbl
                n_lbl    = mask_lbl.sum()
                if n_lbl == 0:
                    continue
                ho_rate = y_sample[mask_lbl].mean()
                if "rsrp" in cols_cluster:
                    rsrp_idx  = cols_cluster.index("rsrp")
                    rsrp_norm = X_sample[mask_lbl, rsrp_idx].mean()
                    rsrp_real = rsrp_norm * (-44 - (-140)) + (-140)
                else:
                    rsrp_real = np.nan
                cluster_profiles[lbl] = {
                    "n": n_lbl, "ho_rate": round(ho_rate, 4),
                    "rsrp_mean": round(rsrp_real, 1),
                }

            # Assign all points
            labels_all = np.full(n_sub, -2, dtype=np.int32)
            if n_sub > MAX_DBSCAN:
                labels_all[idx_sample] = labels_sample
                centroid_lbls, centroid_pts = [], []
                for lbl in unique_labels:
                    if lbl == -1:
                        continue
                    centroid = X_sample[labels_sample == lbl].mean(axis=0)
                    centroid_lbls.append(lbl)
                    centroid_pts.append(centroid)
                if centroid_pts:
                    centroid_pts = np.array(centroid_pts)
                    nbrs = NearestNeighbors(n_neighbors=1, n_jobs=-1)
                    nbrs.fit(centroid_pts)
                    other_idx = np.setdiff1d(np.arange(n_sub), idx_sample)
                    if len(other_idx) > 0:
                        _, nearest = nbrs.kneighbors(X_cluster[other_idx])
                        labels_all[other_idx] = [centroid_lbls[n[0]] for n in nearest]
            else:
                labels_all = labels_sample.astype(np.int32)

            df_final.loc[mask_valid, "cluster_id"] = labels_all
            for lbl, prof in cluster_profiles.items():
                df_final.loc[df_final["cluster_id"] == lbl, "cluster_risk"] = prof["ho_rate"]

            del X_cluster, X_sample, labels_all, labels_sample, df_sub
            gc.collect()
            print(f"\n  ✅ FE-5 done — df_final shape : {df_final.shape}")

    # ── FE-6 : Post-processing cluster features ───────────────────────────────
    print("\n" + "=" * 60)
    print("  FE-6 — CLUSTER POST-PROCESSING")
    print("=" * 60)

    top_clusters = df_final["cluster_id"].value_counts().head(20).index
    df_final["cluster_id_clean"] = df_final["cluster_id"].apply(
        lambda x: x if x in top_clusters else -99
    )

    df_final["risk_level"] = pd.cut(
        df_final["cluster_risk"],
        bins=[-1, 0.05, 0.15, 1],
        labels=["low", "medium", "high"],
    )

    print(df_final[["cluster_id", "cluster_id_clean", "risk_level"]].head())

    # ── FE-7 : Save df_final_fe.parquet ──────────────────────────────────────
    print("\n" + "=" * 60)
    print("  FE-7 — SAVE df_final_fe.parquet")
    print("=" * 60)

    path_fe = os.path.join(fe_out_dir, "df_final_fe.parquet")
    df_final.to_parquet(path_fe, index=False, compression="snappy")
    size_fe = os.path.getsize(path_fe) / 1e6

    n_ho_final = int(df_final["handover"].sum())
    total_final = len(df_final)

    print(f"✅ df_final_fe.parquet : {total_final:,} rows × "
          f"{df_final.shape[1]} cols → {size_fe:.1f} MB")
    print(f"  HO : {n_ho_final:,} / {total_final:,} "
          f"({n_ho_final / total_final * 100:.2f}%)")
    print(f"  Ratio 1:{int((total_final - n_ho_final) / max(n_ho_final, 1))}")
    print("\n→ Next step : NB3_Preprocessing / preprocessing.py")


if __name__ == "__main__":
    run_feature_engineering()