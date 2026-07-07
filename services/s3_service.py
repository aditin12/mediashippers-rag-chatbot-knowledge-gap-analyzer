"""
s3_service.py
Uploads docs to AWS S3 and lists bucket contents.
Completely optional — all functions return safely if AWS not configured.
"""
from pathlib import Path
from config.settings import settings

def _get_client():
    try:
        if not settings.AWS_ACCESS_KEY_ID or "your-aws" in settings.AWS_ACCESS_KEY_ID:
            return None
        import boto3
        return boto3.client(
            "s3",
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )
    except Exception:
        return None

def upload_file(file_path: Path) -> str:
    """Upload file to S3. Returns S3 URI or empty string if not configured."""
    client = _get_client()
    if not client:
        return ""
    try:
        key = f"training_docs/{file_path.name}"
        client.upload_file(str(file_path), settings.S3_BUCKET_NAME, key)
        uri = f"s3://{settings.S3_BUCKET_NAME}/{key}"
        print(f"    ✅ S3: {uri}")
        return uri
    except Exception as e:
        print(f"    ⚠️  S3 skipped: {e}")
        return ""

def list_s3_docs() -> list[str]:
    """List all docs in S3 bucket."""
    client = _get_client()
    if not client:
        return []
    try:
        res  = client.list_objects_v2(Bucket=settings.S3_BUCKET_NAME, Prefix="training_docs/")
        return [obj["Key"] for obj in res.get("Contents", [])]
    except Exception:
        return []
