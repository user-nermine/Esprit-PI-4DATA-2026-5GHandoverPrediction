from huggingface_hub import snapshot_download
import shutil, os

os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

path = snapshot_download(
    repo_id="user-nermine/5g-handover-dvc-storage",
    repo_type="dataset",
    local_dir_use_symlinks=False,
)
print(f"Downloaded to: {path}")

for folder in ["PT_output", "FE_data", "FE_output", "MODEL_output"]:
    src = os.path.join(path, folder)
    if os.path.exists(src):
        shutil.copytree(src, folder, dirs_exist_ok=True)
        print(f"{folder} copied successfully")
    else:
        print(f"WARNING: {folder} not found in HF repo!")