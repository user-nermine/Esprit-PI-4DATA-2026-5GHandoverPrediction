from huggingface_hub import snapshot_download

snapshot_download(
    repo_id="user-nermine/5g-handover-dvc-storage",
    repo_type="dataset",
    local_dir=".",
)
print("PT_output downloaded successfully")