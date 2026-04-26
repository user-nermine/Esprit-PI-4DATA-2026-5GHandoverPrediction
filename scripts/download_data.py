from huggingface_hub import snapshot_download
import shutil, os

path = snapshot_download(
    repo_id="user-nermine/5g-handover-dvc-storage",
    repo_type="dataset",
)
print(f"Downloaded to: {path}")

for folder in ["PT_output", "FE_output", "FE_data"]:
    src = os.path.join(path, folder)
    if os.path.exists(src):
        shutil.copytree(src, folder, dirs_exist_ok=True)
        print(f"{folder} copied successfully")
    else:
        print(f"ERROR: {folder} not found in HF repo!")