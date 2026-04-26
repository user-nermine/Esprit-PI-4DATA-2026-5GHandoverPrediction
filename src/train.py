# src/train.py
# Master pipeline runner — executes all stages end-to-end
#
# Usage:
#   python src/train.py                     # full pipeline (all 5 models per DSO)
#   python src/train.py --skip-deep         # tree models only (fast CI mode)
#   python src/train.py --start-from dso1   # skip FE + preprocessing

import argparse
import sys
import os

# Make src/ importable when run from project root
sys.path.insert(0, os.path.dirname(__file__))

from feature_engineering import run_feature_engineering
from preprocessing import run_preprocessing
from models.dso1 import train_dso1
from models.dso2 import train_dso2
from models.dso3 import train_dso3
from models.dso4 import train_dso4


def run_pipeline(skip_deep: bool = False, start_from: str = "fe"):
    """
    Full DoNext 5G pipeline.

    Args:
        skip_deep:  skip BiLSTM + TabNet (faster, for CI lint/test runs)
        start_from: one of 'fe', 'preprocessing', 'dso1', 'dso2', 'dso3', 'dso4'
    """
    stages = ["fe", "preprocessing", "dso1", "dso2", "dso3", "dso4"]
    start_idx = stages.index(start_from)

    if start_idx <= 0:
        print("=" * 60)
        print("  STEP 1 — Feature Engineering")
        print("=" * 60)
        run_feature_engineering()

    if start_idx <= 1:
        print("=" * 60)
        print("  STEP 2 — Preprocessing")
        print("=" * 60)
        run_preprocessing()

    if start_idx <= 2:
        print("=" * 60)
        print("  STEP 3a — DSO1 : Binary Handover Prediction")
        print("=" * 60)
        train_dso1(skip_deep=skip_deep)

    if start_idx <= 3:
        print("=" * 60)
        print("  STEP 3b — DSO2 : RSRP Drop Prediction")
        print("=" * 60)
        train_dso2(skip_deep=skip_deep)

    if start_idx <= 4:
        print("=" * 60)
        print("  STEP 3c — DSO3 : Next Best Cell Prediction")
        print("=" * 60)
        train_dso3(skip_deep=skip_deep)

    if start_idx <= 5:
        print("=" * 60)
        print("  STEP 3d — DSO4 : Handover Type Prediction")
        print("=" * 60)
        train_dso4(skip_deep=skip_deep)

    print("\n" + "=" * 60)
    print("   FULL PIPELINE COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DoNext 5G training pipeline")
    parser.add_argument(
        "--skip-deep", action="store_true",
        help="Skip BiLSTM and TabNet (tree models only)",
    )
    parser.add_argument(
        "--start-from",
        choices=["fe", "preprocessing", "dso1", "dso2", "dso3", "dso4"],
        default="fe",
        help="Start pipeline from this stage (skips earlier stages)",
    )
    args = parser.parse_args()
    run_pipeline(skip_deep=args.skip_deep, start_from=args.start_from)