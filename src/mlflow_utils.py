# src/mlflow_utils.py
import os
import mlflow

MLFLOW_TRACKING_URI = os.environ.get("MLFLOW_TRACKING_URI", "http://localhost:5000")

# Map experiment name string → MLflow experiment id (cached per process)
_EXP_CACHE: dict = {}


def get_or_create_experiment(name: str) -> str:
    if name in _EXP_CACHE:
        return _EXP_CACHE[name]
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    exp = mlflow.get_experiment_by_name(name)
    exp_id = exp.experiment_id if exp else mlflow.create_experiment(name)
    _EXP_CACHE[name] = exp_id
    return exp_id


def log_model_run(
    experiment_name: str,
    model_name: str,
    params: dict,
    metrics: dict,
    artifacts: list = None,
    tags: dict = None,
):
    """
    Log one model run to the MLflow server.

    Args:
        experiment_name:  e.g. "DSO1-Handover", "DSO2-RSRP-Drop", …
        model_name:       e.g. "XGBoost", "LightGBM", "RandomForest", "BiLSTM", "TabNet"
        params:           hyperparameter dict (logged as MLflow params)
        metrics:          evaluation metrics dict (logged as MLflow metrics)
        artifacts:        list of file paths to upload (PNGs, pkl, h5, …)
        tags:             extra key-value tags (dso, task, skip_deep, …)
    """
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    exp_id = get_or_create_experiment(experiment_name)

    with mlflow.start_run(experiment_id=exp_id, run_name=model_name):
        if tags:
            mlflow.set_tags(tags)
        if params:
            mlflow.log_params(params)
        if metrics:
            mlflow.log_metrics(metrics)
        if artifacts:
            for path in artifacts:
                if os.path.exists(path):
                    mlflow.log_artifact(path)
                else:
                    print(f"  [MLflow] Artifact not found, skipping: {path}")

    print(f"  [MLflow] {model_name}->'{experiment_name}'")