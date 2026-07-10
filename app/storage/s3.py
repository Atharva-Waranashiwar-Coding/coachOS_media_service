from typing import cast

import boto3
from botocore.client import BaseClient
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import settings
from app.core.exceptions import StorageServiceError
from app.storage.base import ObjectMetadata


class S3StorageProvider:
    """Private S3-compatible object storage adapter."""

    def __init__(self, client: BaseClient | None = None) -> None:
        self.client = client or boto3.client(
            "s3",
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            endpoint_url=settings.s3_endpoint_url,
        )
        self.bucket = settings.s3_bucket_name

    def generate_upload_url(self, key: str, content_type: str, expires_in: int) -> str:
        try:
            return cast(
                str,
                self.client.generate_presigned_url(
                    "put_object",
                    Params={"Bucket": self.bucket, "Key": key, "ContentType": content_type},
                    ExpiresIn=expires_in,
                    HttpMethod="PUT",
                ),
            )
        except (BotoCoreError, ClientError) as exc:
            raise StorageServiceError("Could not prepare object upload.") from exc

    def head_object(self, key: str) -> ObjectMetadata:
        try:
            data = self.client.head_object(Bucket=self.bucket, Key=key)
            return ObjectMetadata(
                True, data.get("ContentLength"), data.get("ContentType"), str(data.get("ETag", "")).strip('"') or None
            )
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in {"404", "NoSuchKey", "NotFound"}:
                return ObjectMetadata(False)
            raise StorageServiceError("Could not verify stored object.") from exc
        except BotoCoreError as exc:
            raise StorageServiceError("Could not verify stored object.") from exc

    def delete_object(self, key: str) -> None:
        try:
            self.client.delete_object(Bucket=self.bucket, Key=key)
        except (BotoCoreError, ClientError) as exc:
            raise StorageServiceError("Could not delete stored object.") from exc

    def bucket_accessible(self) -> bool:
        try:
            self.client.head_bucket(Bucket=self.bucket)
            return True
        except (BotoCoreError, ClientError):
            return False
