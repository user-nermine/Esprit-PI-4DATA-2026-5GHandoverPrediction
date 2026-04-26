# scripts/validate_data.py
import numpy as np
import os
import sys
import json
import pyarrow.parquet as pq


def validate_pt_output(pt_out_dir="PT_output"):
    print("=" * 50)
    print("  DATA QUALITY VALIDATION")
    print("=" * 50)

    errors = []

    # Check all required files exist
    required_files = [
        "df_preprocessed.parquet",
        "config.json",
        "idx_train.npy",
        "idx_val.npy",
        "idx_test.npy",
        "y_train.npy",
        "y_val.npy",
        "y_test.npy",
    ]
    for f in required_files:
        path = os.path.join(pt_out_dir, f)
        if not os.path.exists(path):
            errors.append(f"Missing file: {path}")
        else:
            print(f"  {f} exists")

    # Validate parquet metadata only (no full load)
    pf   = pq.ParquetFile(os.path.join(pt_out_dir, "df_preprocessed.parquet"))
    meta = pf.metadata
    n_rows = meta.num_rows
    n_cols = meta.num_columns
    print(f"  df_preprocessed: {n_rows:,} rows x {n_cols} cols")

    if n_rows < 1000:
        errors.append(f"Too few rows: {n_rows} (expected >= 1000)")
    else:
        print(f"  Row count OK: {n_rows:,}")

    # Validate config
    with open(os.path.join(pt_out_dir, "config.json")) as f:
        config = json.load(f)
    if "cols_X" not in config:
        errors.append("config.json missing 'cols_X' key")
    else:
        print(f"  config.json OK: {len(config['cols_X'])} features")

    # Validate labels
    y_train = np.load(os.path.join(pt_out_dir, "y_train.npy"))
    y_val   = np.load(os.path.join(pt_out_dir, "y_val.npy"))
    y_test  = np.load(os.path.join(pt_out_dir, "y_test.npy"))

    if len(y_train) == 0:
        errors.append("y_train is empty")
    else:
        print(f"  y_train size: {len(y_train):,}")

    if len(y_val) == 0:
        errors.append("y_val is empty")
    else:
        print(f"  y_val size: {len(y_val):,}")

    if len(y_test) == 0:
        errors.append("y_test is empty")
    else:
        print(f"  y_test size: {len(y_test):,}")

    # Check train/test split ratio
    total = len(y_train) + len(y_val) + len(y_test)
    train_ratio = len(y_train) / total
    if not (0.5 <= train_ratio <= 0.9):
        errors.append(f"Unexpected train ratio: {train_ratio:.2f}")
    else:
        print(f"  Train ratio OK: {train_ratio:.2f}")

    # Final result
    print("\n" + "=" * 50)
    if errors:
        print("  VALIDATION FAILED:")
        for e in errors:
            print(f"    - {e}")
        sys.exit(1)
    else:
        print("  ALL CHECKS PASSED")
    print("=" * 50)


if __name__ == "__main__":
    validate_pt_output()