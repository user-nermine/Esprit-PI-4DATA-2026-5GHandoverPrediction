import os
from huggingface_hub import HfApi

token   = os.environ.get("HF_TOKEN")
api     = HfApi()
REPO_ID = "user-nermine/5g-handover-dvc-storage"

folders = ["PT_output", "FE_output", "FE_data"]

for folder in folders:
    if not os.path.exists(folder):
        print(f"SKIP (not found): {folder}")
        continue
    print(f"Uploading {folder} ...")
    api.upload_folder(
        folder_path=folder,
        repo_id=REPO_ID,
        repo_type="dataset",
        path_in_repo=folder,
        token=token,
        delete_patterns="*",
    )
    print(f"Done: {folder}")

print("All uploads complete!")
