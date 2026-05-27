import io
import uuid

import boto3
from botocore.client import Config

from config import get_settings

settings = get_settings()


def get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=f"{'https' if settings.minio_secure else 'http'}://{settings.minio_endpoint}",
        aws_access_key_id=settings.minio_access_key,
        aws_secret_access_key=settings.minio_secret_key,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )


def upload_file(content: bytes, filename: str, mime_type: str, project_id: uuid.UUID) -> str:
    client = get_s3_client()
    key = f"projects/{project_id}/{uuid.uuid4()}/{filename}"
    client.put_object(
        Bucket=settings.minio_bucket,
        Key=key,
        Body=content,
        ContentType=mime_type,
    )
    return key


def download_file(storage_key: str) -> bytes:
    client = get_s3_client()
    buffer = io.BytesIO()
    client.download_fileobj(settings.minio_bucket, storage_key, buffer)
    return buffer.getvalue()


def delete_file(storage_key: str) -> None:
    client = get_s3_client()
    client.delete_object(Bucket=settings.minio_bucket, Key=storage_key)
