# tests/test_pipeline.py
# pytest test suite for DoNext 5G pipeline
# Covers: structure, imports, function signatures, metrics helper

import os
import sys
import json
import importlib

import numpy as np
import pytest

# ── Make src/ importable from project root ────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


# ══════════════════════════════════════════════════════════════════════════════
#  1. STRUCTURE TESTS — do the expected files/folders exist?
# ══════════════════════════════════════════════════════════════════════════════

class TestProjectStructure:

    def test_src_folder_exists(self):
        assert os.path.isdir("src"), "src/ folder is missing"

    def test_models_folder_exists(self):
        assert os.path.isdir(os.path.join("src", "models")), \
            "src/models/ folder is missing"

    def test_tests_folder_exists(self):
        assert os.path.isdir("tests"), "tests/ folder is missing"

    def test_src_init_exists(self):
        assert os.path.isfile(os.path.join("src", "__init__.py")), \
            "src/__init__.py is missing"

    def test_models_init_exists(self):
        assert os.path.isfile(os.path.join("src", "models", "__init__.py")), \
            "src/models/__init__.py is missing"

    def test_train_py_exists(self):
        assert os.path.isfile(os.path.join("src", "train.py")), \
            "src/train.py is missing"

    def test_dso1_exists(self):
        assert os.path.isfile(os.path.join("src", "models", "dso1.py")), \
            "src/models/dso1.py is missing"

    def test_dso2_exists(self):
        assert os.path.isfile(os.path.join("src", "models", "dso2.py")), \
            "src/models/dso2.py is missing"

    def test_dso3_exists(self):
        assert os.path.isfile(os.path.join("src", "models", "dso3.py")), \
            "src/models/dso3.py is missing"

    def test_dso4_exists(self):
        assert os.path.isfile(os.path.join("src", "models", "dso4.py")), \
            "src/models/dso4.py is missing"

    def test_requirements_exists(self):
        assert os.path.isfile("requirements.txt"), \
            "requirements.txt is missing"

    def test_ci_yml_exists(self):
        assert os.path.isfile(os.path.join(".github", "workflows", "ci.yml")), \
            ".github/workflows/ci.yml is missing"

    def test_dvcignore_exists(self):
        assert os.path.isfile(".dvcignore"), ".dvcignore is missing"

    def test_gitignore_exists(self):
        assert os.path.isfile(".gitignore"), ".gitignore is missing"


# ══════════════════════════════════════════════════════════════════════════════
#  2. IMPORT TESTS — do all modules import without error?
# ══════════════════════════════════════════════════════════════════════════════

class TestImports:

    def test_import_dso1(self):
        mod = importlib.import_module("models.dso1")
        assert hasattr(mod, "train_dso1"), \
            "train_dso1 function not found in dso1.py"

    def test_import_dso2(self):
        mod = importlib.import_module("models.dso2")
        assert hasattr(mod, "train_dso2"), \
            "train_dso2 function not found in dso2.py"

    def test_import_dso3(self):
        mod = importlib.import_module("models.dso3")
        assert hasattr(mod, "train_dso3"), \
            "train_dso3 function not found in dso3.py"

    def test_import_dso4(self):
        mod = importlib.import_module("models.dso4")
        assert hasattr(mod, "train_dso4"), \
            "train_dso4 function not found in dso4.py"

    def test_import_train(self):
        mod = importlib.import_module("train")
        assert hasattr(mod, "run_pipeline"), \
            "run_pipeline function not found in train.py"

    def test_train_has_correct_stages(self):
        mod = importlib.import_module("train")
        import inspect
        src = inspect.getsource(mod.run_pipeline)
        for stage in ["fe", "preprocessing", "dso1", "dso2", "dso3", "dso4"]:
            assert stage in src, \
                f"Stage '{stage}' not found in run_pipeline()"


# ══════════════════════════════════════════════════════════════════════════════
#  3. FUNCTION SIGNATURE TESTS — do train functions accept the right args?
# ══════════════════════════════════════════════════════════════════════════════

class TestFunctionSignatures:

    @pytest.fixture(autouse=True)
    def _import_modules(self):
        self.dso1 = importlib.import_module("models.dso1")
        self.dso2 = importlib.import_module("models.dso2")
        self.dso3 = importlib.import_module("models.dso3")
        self.dso4 = importlib.import_module("models.dso4")
        self.train = importlib.import_module("train")

    def _get_params(self, func):
        import inspect
        return list(inspect.signature(func).parameters.keys())

    def test_dso1_has_skip_deep(self):
        params = self._get_params(self.dso1.train_dso1)
        assert "skip_deep" in params, \
            "train_dso1 must accept skip_deep parameter"

    def test_dso2_has_skip_deep(self):
        params = self._get_params(self.dso2.train_dso2)
        assert "skip_deep" in params, \
            "train_dso2 must accept skip_deep parameter"

    def test_dso3_has_skip_deep(self):
        params = self._get_params(self.dso3.train_dso3)
        assert "skip_deep" in params, \
            "train_dso3 must accept skip_deep parameter"

    def test_dso4_has_skip_deep(self):
        params = self._get_params(self.dso4.train_dso4)
        assert "skip_deep" in params, \
            "train_dso4 must accept skip_deep parameter"

    def test_dso1_has_pt_out_dir(self):
        params = self._get_params(self.dso1.train_dso1)
        assert "pt_out_dir" in params, \
            "train_dso1 must accept pt_out_dir parameter"

    def test_dso1_has_model_out_dir(self):
        params = self._get_params(self.dso1.train_dso1)
        assert "model_out_dir" in params, \
            "train_dso1 must accept model_out_dir parameter"

    def test_run_pipeline_has_skip_deep(self):
        params = self._get_params(self.train.run_pipeline)
        assert "skip_deep" in params, \
            "run_pipeline must accept skip_deep parameter"

    def test_run_pipeline_has_start_from(self):
        params = self._get_params(self.train.run_pipeline)
        assert "start_from" in params, \
            "run_pipeline must accept start_from parameter"


# ══════════════════════════════════════════════════════════════════════════════
#  4. METRICS HELPER TESTS — unit test _metrics_binary with dummy data
# ══════════════════════════════════════════════════════════════════════════════

class TestMetricsHelper:

    @pytest.fixture(autouse=True)
    def _load_helper(self):
        self.dso1 = importlib.import_module("models.dso1")

    def _make_dummy(self):
        """Perfect predictions on a balanced dummy dataset."""
        rng = np.random.default_rng(0)
        y_true = rng.integers(0, 2, size=100)
        y_pred = y_true.copy()                        # perfect predictions
        y_prob = y_true.astype(float)                 # prob=1 for class 1
        return y_true, y_pred, y_prob

    def test_metrics_returns_dict(self):
        y_true, y_pred, y_prob = self._make_dummy()
        result = self.dso1._metrics_binary("TestModel", y_true, y_pred, y_prob)
        assert isinstance(result, dict), "metrics must return a dict"

    def test_metrics_has_required_keys(self):
        y_true, y_pred, y_prob = self._make_dummy()
        result = self.dso1._metrics_binary("TestModel", y_true, y_pred, y_prob)
        for key in ["model", "f1", "precision", "recall", "auc_roc", "auc_pr"]:
            assert key in result, f"metrics dict missing key: {key}"

    def test_metrics_model_name(self):
        y_true, y_pred, y_prob = self._make_dummy()
        result = self.dso1._metrics_binary("XGBoost", y_true, y_pred, y_prob)
        assert result["model"] == "XGBoost"

    def test_metrics_f1_range(self):
        y_true, y_pred, y_prob = self._make_dummy()
        result = self.dso1._metrics_binary("T", y_true, y_pred, y_prob)
        assert 0.0 <= result["f1"] <= 1.0, "f1 must be between 0 and 1"

    def test_metrics_auc_roc_range(self):
        y_true, y_pred, y_prob = self._make_dummy()
        result = self.dso1._metrics_binary("T", y_true, y_pred, y_prob)
        assert 0.0 <= result["auc_roc"] <= 1.0, "auc_roc must be between 0 and 1"

    def test_metrics_perfect_predictions(self):
        """Perfect preds should give f1=1.0."""
        y_true, y_pred, y_prob = self._make_dummy()
        result = self.dso1._metrics_binary("T", y_true, y_pred, y_prob)
        assert result["f1"] == 1.0, \
            f"Perfect predictions should yield f1=1.0, got {result['f1']}"

    def test_metrics_values_are_rounded(self):
        """Values should be rounded to 4 decimal places."""
        rng = np.random.default_rng(1)
        y_true = rng.integers(0, 2, size=200)
        y_pred = rng.integers(0, 2, size=200)
        y_prob = rng.random(size=200)
        result = self.dso1._metrics_binary("T", y_true, y_pred, y_prob)
        for key in ["f1", "precision", "recall", "auc_roc", "auc_pr"]:
            val = result[key]
            assert val == round(val, 4), \
                f"{key} should be rounded to 4 decimals, got {val}"


# ══════════════════════════════════════════════════════════════════════════════
#  5. REQUIREMENTS TESTS — are key packages listed?
# ══════════════════════════════════════════════════════════════════════════════

class TestRequirements:

    @pytest.fixture(autouse=True)
    def _load_reqs(self):
        with open("requirements.txt") as f:
            self.reqs = f.read().lower()

    def test_xgboost_in_requirements(self):
        assert "xgboost" in self.reqs, "xgboost missing from requirements.txt"

    def test_lightgbm_in_requirements(self):
        assert "lightgbm" in self.reqs, "lightgbm missing from requirements.txt"

    def test_scikit_learn_in_requirements(self):
        assert "scikit-learn" in self.reqs or "sklearn" in self.reqs, \
            "scikit-learn missing from requirements.txt"

    def test_pandas_in_requirements(self):
        assert "pandas" in self.reqs, "pandas missing from requirements.txt"

    def test_numpy_in_requirements(self):
        assert "numpy" in self.reqs, "numpy missing from requirements.txt"