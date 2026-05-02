import os
from huggingface_hub import snapshot_download

HF_REPO    = "user-nermine/5g-handover-dvc-storage"
LOCAL_DIR  = "/opt/airflow"

def download_from_huggingface():
    token = os.environ.get("HF_TOKEN")
    if not token:
        print("HF_TOKEN not set â€” skipping HuggingFace download, using local data")
        return

    print(f"Downloading data from HuggingFace: {HF_REPO}")
    snapshot_download(
        repo_id=HF_REPO,
        repo_type="dataset",
        local_dir=LOCAL_DIR,
        token=token,
        ignore_patterns=["*.git*", "*.md"],
    )
    print("Download complete")

if __name__ == "__main__":
    download_from_huggingface()
