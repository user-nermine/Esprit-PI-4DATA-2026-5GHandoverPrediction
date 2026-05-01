from huggingface_hub import HfApi

import os
token = os.environ.get("HF_TOKEN")
api.upload_folder(
    folder_path='PT_output',
    repo_id='user-nermine/5g-handover-dvc-storage',
    repo_type='dataset',
    path_in_repo='PT_output',
)
print('Done!')