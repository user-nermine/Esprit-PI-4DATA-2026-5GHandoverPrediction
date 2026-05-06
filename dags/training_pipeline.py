# dags/training_pipeline.py
# Airflow DAG — replaces Makefile as orchestration tool (Excellence)
# Triggers: every 6 hours automatically + manual trigger
# Tasks: fetch_data → lint → security → tests → validate → train DSO1→4 → MLflow check

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

PROJECT_DIR = "/opt/airflow"

def fetch_data_from_hf():
    import sys
    sys.path.insert(0, "/opt/airflow")
    from src.data.hf_loader import download_from_huggingface
    download_from_huggingface()

with DAG(
    dag_id="training_pipeline",
    description="5G Handover ML Pipeline — CI checks + training + MLflow logging",
    default_args=default_args,
    start_date=days_ago(1),
    schedule_interval="0 */6 * * *",
    catchup=False,
    tags=["mlops", "5g", "training"],
) as dag:

    fetch_data = PythonOperator(
        task_id="fetch_data_huggingface",
        python_callable=fetch_data_from_hf,
    )

    lint = BashOperator(
        task_id="lint_ruff",
        bash_command=f"cd {PROJECT_DIR} && python -m ruff check src/",
    )

    security = BashOperator(
        task_id="security_bandit",
        bash_command=f"cd {PROJECT_DIR} && python -m bandit -r src/ -ll -q",
    )

    tests = BashOperator(
        task_id="tests_pytest",
        bash_command=f"cd {PROJECT_DIR} && python -m pytest tests/ -q --tb=short",
    )

    validate_data = BashOperator(
        task_id="validate_data",
        bash_command=f"cd {PROJECT_DIR} && python scripts/validate_data.py",
    )

    train_dso1 = BashOperator(
        task_id="train_dso1",
        bash_command=f"cd {PROJECT_DIR} && python -m src.models.dso1",
        execution_timeout=timedelta(hours=2),
    )

    train_dso2 = BashOperator(
        task_id="train_dso2",
        bash_command=f"cd {PROJECT_DIR} && python -m src.models.dso2",
        execution_timeout=timedelta(hours=2),
    )

    train_dso3 = BashOperator(
        task_id="train_dso3",
        bash_command=f"cd {PROJECT_DIR} && python -m src.models.dso3",
        execution_timeout=timedelta(hours=2),
    )

    train_dso4 = BashOperator(
        task_id="train_dso4",
        bash_command=f"cd {PROJECT_DIR} && python -m src.models.dso4",
        execution_timeout=timedelta(hours=2),
    )

    check_mlflow = BashOperator(
        task_id="check_mlflow",
        bash_command=(
            "curl -f http://mlflow_server:5000/api/2.0/mlflow/experiments/list "
            "&& echo 'MLflow OK'"
        ),
    )

    fetch_data >> [lint, security] >> validate_data
    fetch_data >> tests >> validate_data
    validate_data >> [train_dso1, train_dso2, train_dso3, train_dso4]
    [train_dso1, train_dso2, train_dso3, train_dso4] >> check_mlflow
