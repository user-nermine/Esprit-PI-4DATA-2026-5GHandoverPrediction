# scripts/validate_data.py
import pandas as pd
import numpy as np
import os
import sys

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
            print(f" {f} exists")

    # Load and validate dataframe
    df = pd.read_parquet(os.path.join(pt_out_dir, "df_preprocessed.parquet"))
    print(f"\n  Shape: {df.shape}")

    # Check minimum rows
    if len(df) < 1000:
        errors.append(f"Too few rows: {len(df)} (expected >= 1000)")
    else:
        print(f" Row count OK: {len(df):,}")

    # Check no fully empty columns
    empty_cols = [c for c in df.columns if df[c].isna().all()]
    if empty_cols:
        errors.append(f"Fully empty columns: {empty_cols}")
    else:
        print(f" No fully empty columns")

    # Check handover column exists
    if "handover" not in df.columns:
        errors.append("Missing column: handover")
    else:
        ho_rate = df["handover"].mean()
        print(f" handover column exists (HO rate: {ho_rate:.2%})")

    # Check labels
    y_train = np.load(os.path.join(pt_out_dir, "y_train.npy"))
    y_test  = np.load(os.path.join(pt_out_dir, "y_test.npy"))

    if len(y_train) == 0:
        errors.append("y_train is empty")
    else:
        print(f" y_train size: {len(y_train):,}")

    if len(y_test) == 0:
        errors.append("y_test is empty")
    else:
        print(f" y_test size: {len(y_test):,}")

    # Check train/test split ratio
    total = len(y_train) + len(y_test)
    train_ratio = len(y_train) / total
    if not (0.5 <= train_ratio <= 0.9):
        errors.append(f"Unexpected train ratio: {train_ratio:.2f}")
    else:
        print(f"Train ratio OK: {train_ratio:.2f}")

    # Final result
    print("\n" + "=" * 50)
    if errors:
        print(" VALIDATION FAILED:")
        for e in errors:
            print(f"     - {e}")
        sys.exit(1)
    else:
        print(" ALL CHECKS PASSED")
    print("=" * 50)

if __name__ == "__main__":
    validate_pt_output()