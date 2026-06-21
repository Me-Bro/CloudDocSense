"""S3 / MinIO object storage access."""
from functools import lru_cache

import boto3
from botocore.config import Config

from worker.config import settings


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


def download_bytes(s3_key: str) -> bytes:
    """Fetch an object's raw bytes from the configured bucket."""
    resp = _client().get_object(Bucket=settings.s3_bucket, Key=s3_key)
    return resp["Body"].read()
