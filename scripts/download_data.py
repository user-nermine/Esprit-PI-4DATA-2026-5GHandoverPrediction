from huggingface_hub import snapshot_download
import shutil, os

path = snapshot_download(
    repo_id="user-nermine/5g-handover-dvc-storage",
    repo_type="dataset",
)
print(f"Downloaded to: {path}")
if os.path.exists(os.path.join(path, "PT_output")):
    shutil.copytree(os.path.join(path, "PT_output"), "PT_output", dirs_exist_ok=True)
    print("PT_output copied successfully")
else:
    print("ERROR: PT_output not found!")