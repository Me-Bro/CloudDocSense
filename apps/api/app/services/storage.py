"""S3 / MinIO storage for uploaded documents."""
from functools import lru_cache

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.config import settings


@lru_cache(maxsize=1)
def _client():
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )


def ensure_bucket() -> None:
    c = _client()
    try:
        c.head_bucket(Bucket=settings.s3_bucket)
    except ClientError:
        c.create_bucket(Bucket=settings.s3_bucket)


def upload_bytes(key: str, data: bytes, content_type: str | None = None) -> str:
    ensure_bucket()
    _client().put_object(
        Bucket=settings.s3_bucket,
        Key=key,
        Body=data,
        ContentType=content_type or "application/octet-stream",
    )
    return key


def download_bytes(key: str) -> tuple[bytes, str]:
    """Return (raw bytes, content_type) for an S3 object."""
    obj = _client().get_object(Bucket=settings.s3_bucket, Key=key)
    data = obj["Body"].read()
    content_type = obj.get("ContentType", "application/octet-stream")
    return data, content_type


def delete_object(key: str) -> None:
    _client().delete_object(Bucket=settings.s3_bucket, Key=key)
