# dags/training_pipeline.py
# Airflow DAG — replaces Makefile as orchestration tool (Excellence)
# Triggers: every 6 hours automatically + manual trigger
# Tasks: fetch_data → lint → security → tests → validate → train DSO1→4 → MLflow check

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago

# ── Constants ─────────────────────────────────────────────────────────────────
PROJECT_DIR = "/opt/airflow"

# Passed to every training BashOperator as environment variables.
# N_JOBS=2  → XGBoost / LightGBM / sklearn use at most 2 threads (was -1 = all cores)
# CI=true   → DSO scripts load only row_group_0 (fast, low memory)
TRAIN_ENV = {
    "N_JOBS": "2",
    "CI": "true",
    "PYTHONUNBUFFERED": "1",
    "MLFLOW_TRACKING_URI": "http://mlflow_server:5000",
}

# ── Default args ──────────────────────────────────────────────────────────────
default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}


# ── Python callable — fetch data from HuggingFace ────────────────────────────
def fetch_data_from_hf():
    import sys
    sys.path.insert(0, "/opt/airflow")
    from src.data.hf_loader import download_from_huggingface
    download_from_huggingface()


# ── DAG definition ────────────────────────────────────────────────────────────
with DAG(
    dag_id="training_pipeline",
    description="5G Handover ML Pipeline — CI checks + training + MLflow logging",
    default_args=default_args,
    start_date=days_ago(1),
    schedule_interval="0 */6 * * *",
    catchup=False,
    max_active_runs=1,          # never run two instances of this DAG in parallel
    tags=["mlops", "5g", "training"],
) as dag:

    # ── Step 1: fetch data from HuggingFace ───────────────────────────────────
    fetch_data = PythonOperator(
        task_id="fetch_data_huggingface",
        python_callable=fetch_data_from_hf,
        execution_timeout=timedelta(minutes=30),
    )

    # ── Step 2a: lint (ruff) ──────────────────────────────────────────────────
    lint = BashOperator(
        task_id="lint_ruff",
        bash_command=f"cd {PROJECT_DIR} && python -m ruff check src/",
        execution_timeout=timedelta(minutes=5),
    )

    # ── Step 2b: security scan (bandit) ───────────────────────────────────────
    security = BashOperator(
        task_id="security_bandit",
        bash_command=f"cd {PROJECT_DIR} && python -m bandit -r src/ -ll -q",
        execution_timeout=timedelta(minutes=5),
    )

    # ── Step 2c: unit tests (pytest) ──────────────────────────────────────────
    tests = BashOperator(
        task_id="tests_pytest",
        bash_command=f"cd {PROJECT_DIR} && python -m pytest tests/ -q --tb=short",
        execution_timeout=timedelta(minutes=10),
    )

    # ── Step 3: validate data ─────────────────────────────────────────────────
    validate_data = BashOperator(
        task_id="validate_data",
        bash_command=f"cd {PROJECT_DIR} && python scripts/validate_data.py",
        execution_timeout=timedelta(minutes=10),
    )

    # ── Step 4: train DSO1 — Binary handover prediction ──────────────────────
    # pool="training_pool" (slots=2) means at most 2 DSO tasks run simultaneously.
    # Create this pool in Airflow UI: Admin → Pools → + → name=training_pool slots=2
    train_dso1 = BashOperator(
        task_id="train_dso1",
        bash_command=f"cd {PROJECT_DIR} && python -m src.models.dso1",
        env=TRAIN_ENV,
        pool="training_pool",
        execution_timeout=timedelta(hours=2),
    )

    # ── Step 4: train DSO2 — RSRP drop prediction ────────────────────────────
    train_dso2 = BashOperator(
        task_id="train_dso2",
        bash_command=f"cd {PROJECT_DIR} && python -m src.models.dso2",
        env=TRAIN_ENV,
        pool="training_pool",
        execution_timeout=timedelta(hours=2),
    )

    # ── Step 4: train DSO3 — Next cell multiclass ────────────────────────────
    train_dso3 = BashOperator(
        task_id="train_dso3",
        bash_command=f"cd {PROJECT_DIR} && python -m src.models.dso3",
        env=TRAIN_ENV,
        pool="training_pool",
        execution_timeout=timedelta(hours=2),
    )

    # ── Step 4: train DSO4 — Handover type multiclass ────────────────────────
    train_dso4 = BashOperator(
        task_id="train_dso4",
        bash_command=f"cd {PROJECT_DIR} && python -m src.models.dso4",
        env=TRAIN_ENV,
        pool="training_pool",
        execution_timeout=timedelta(hours=2),
    )

    # ── Step 5: verify MLflow received the experiment runs ───────────────────
    check_mlflow = BashOperator(
        task_id="check_mlflow",
        bash_command=(
            "curl -f http://mlflow_server:5000/api/2.0/mlflow/experiments/list "
            "&& echo 'MLflow OK'"
        ),
        execution_timeout=timedelta(minutes=2),
    )

    # ── Pipeline order ────────────────────────────────────────────────────────
    #
    #  fetch_data ──┬── lint ──────┐
    #               ├── security ──┤── validate_data ──┬── train_dso1 ──┐
    #               └── tests ─────┘                   ├── train_dso2 ──┤── check_mlflow
    #                                                   ├── train_dso3 ──┤
    #                                                   └── train_dso4 ──┘
    #
    # pool="training_pool" (slots=2) ensures only 2 trains run at once,
    # so CPU stays at ~4 cores max instead of 16.

    fetch_data >> [lint, security] >> validate_data
    fetch_data >> tests >> validate_data
    validate_data >> [train_dso1, train_dso2, train_dso3, train_dso4]
    [train_dso1, train_dso2, train_dso3, train_dso4] >> check_mlflow