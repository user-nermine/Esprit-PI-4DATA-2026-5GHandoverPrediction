import boto3
from botocore.client import Config
from pathlib import Path

s3 = boto3.client('s3', endpoint_url='http://localhost:9000',
    aws_access_key_id='admin', aws_secret_access_key='admin123',
    config=Config(signature_version='s3v4'), region_name='us-east-1')

BUCKET = 'mlops-data'
ROOT   = Path('D:/pipline_c')

FOLDERS = [
    'FE_data',
    'FE_output',
    'MODEL_output',
    'PT_output',
    'PT_input',
    'dags',
]

for folder in FOLDERS:
    local = ROOT / folder
    if not local.exists():
        print(f'SKIP (not found): {folder}')
        continue
    files = [f for f in local.rglob('*') if f.is_file()]
    print(f'\n[{folder}] — {len(files)} files')
    for f in files:
        key = f'files/{folder}/{f.relative_to(local)}'.replace('\\', '/')
        print(f'  -> {key}')
        s3.upload_file(str(f), BUCKET, key)

print('\nDone!')