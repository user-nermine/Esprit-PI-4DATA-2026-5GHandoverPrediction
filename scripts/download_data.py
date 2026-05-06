from huggingface_hub import snapshot_download
import shutil, os

token = os.environ.get("HF_TOKEN")
if not token:
    print("WARNING: HF_TOKEN not set — skipping download")
    exit(0)

path = snapshot_download(
    repo_id="user-nermine/5g-handover-dvc-storage",
    repo_type="dataset",
    token=token,
)
print(f"Downloaded to: {path}")

for folder in ["PT_output", "FE_data", "FE_output", "MODEL_output"]:
    src = os.path.join(path, folder)
    if os.path.exists(src):
        shutil.copytree(src, folder, dirs_exist_ok=True)
        print(f"{folder} copied successfully")
    else:
        print(f"WARNING: {folder} not found in HF repo!")
