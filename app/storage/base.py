from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ObjectMetadata:
    exists: bool
    content_length: int | None = None
    content_type: str | None = None
    etag: str | None = None


class StorageProvider(Protocol):
    def generate_upload_url(self, key: str, content_type: str, expires_in: int) -> str: ...
    def head_object(self, key: str) -> ObjectMetadata: ...
    def delete_object(self, key: str) -> None: ...
    def bucket_accessible(self) -> bool: ...
