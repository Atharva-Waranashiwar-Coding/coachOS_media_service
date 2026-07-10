from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.core.exceptions import BadRequestError, ConflictError, PayloadTooLargeError, UnsupportedMediaTypeError
from app.models.enums import SessionStatus, SessionType, UploadStatus
from app.schemas.media import PracticeSessionCreate, PracticeSessionUpdate, UploadCompletionRequest, UploadUrlRequest
from app.services.media import PracticeSessionService, VideoService
from app.storage.base import ObjectMetadata


class Athletes:
    def __init__(self, allowed=True):
        self.allowed, self.calls = allowed, 0

    def verify_access(self, athlete_id, token):
        self.calls += 1
        if not self.allowed:
            from app.core.exceptions import NotFoundError

            raise NotFoundError("Athlete not found.")


class Storage:
    def __init__(self):
        self.metadata = ObjectMetadata(True, 100, "video/mp4", "storage-etag")
        self.deleted = []
        self.urls = []

    def generate_upload_url(self, key, content_type, expires_in):
        self.urls.append((key, content_type, expires_in))
        return "https://upload.invalid/signed"

    def head_object(self, key):
        return self.metadata

    def delete_object(self, key):
        self.deleted.append(key)

    def bucket_accessible(self):
        return True


class Timeline:
    def __init__(self):
        self.calls = []

    def publish_video_uploaded(self, **kwargs):
        self.calls.append(kwargs)


def create_session(db, status=SessionStatus.DRAFT):
    service = PracticeSessionService(db, Athletes())
    created = service.create(
        PracticeSessionCreate(
            athlete_id=uuid4(), title=" Bullpen ", session_date=datetime.now(UTC), session_type=SessionType.BULLPEN
        ),
        uuid4(),
        "token",
    )
    if status != SessionStatus.DRAFT:
        item = service.repo.owned_session(created.id, created.coach_user_id)
        item.status = status
        db.commit()
    return service, created


def test_create_update_complete_and_terminal_rule(db):
    service, created = create_session(db)
    assert created.title == "Bullpen"
    updated = service.update(created.id, PracticeSessionUpdate(title="Command work"), created.coach_user_id, "token")
    assert updated.title == "Command work"
    completed = service.transition(created.id, SessionStatus.COMPLETED, created.coach_user_id, "token")
    assert completed.completed_at and completed.status == SessionStatus.COMPLETED
    with pytest.raises(BadRequestError):
        service.update(created.id, PracticeSessionUpdate(title="No"), created.coach_user_id, "token")


def test_cancelled_session_cannot_complete(db):
    service, created = create_session(db)
    service.transition(created.id, SessionStatus.CANCELLED, created.coach_user_id, "token")
    with pytest.raises(BadRequestError):
        service.transition(created.id, SessionStatus.COMPLETED, created.coach_user_id, "token")


def test_upload_url_creates_pending_record_and_safe_key(db):
    sessions, created = create_session(db)
    storage = Storage()
    videos = VideoService(db, storage, Athletes(), Timeline())
    result = videos.request_upload(
        sessions.get_model(created.id, created.coach_user_id, "token"),
        UploadUrlRequest(filename="../../Game Clip.MP4", content_type="video/mp4", file_size_bytes=100),
    )
    assert result.required_headers == {"Content-Type": "video/mp4"}
    assert result.storage_key.startswith(
        f"athletes/{created.athlete_id}/sessions/{created.id}/videos/{result.video_id}/"
    )
    assert (
        ".." not in result.storage_key
        and videos.repo.owned_video(result.video_id, created.coach_user_id).upload_status == UploadStatus.PENDING
    )


def test_upload_validation(db, monkeypatch):
    sessions, created = create_session(db)
    videos = VideoService(db, Storage(), Athletes(), Timeline())
    model = sessions.get_model(created.id, created.coach_user_id, "token")
    with pytest.raises(UnsupportedMediaTypeError):
        videos.request_upload(model, UploadUrlRequest(filename="x.mp4", content_type="text/plain", file_size_bytes=1))
    monkeypatch.setattr("app.services.media.settings.max_video_size_bytes", 5)
    with pytest.raises(PayloadTooLargeError):
        videos.request_upload(model, UploadUrlRequest(filename="x.mp4", content_type="video/mp4", file_size_bytes=6))
    with pytest.raises(BadRequestError):
        videos.request_upload(model, UploadUrlRequest(filename="x.exe", content_type="video/mp4", file_size_bytes=1))


def test_complete_verifies_storage_and_is_idempotent(db):
    sessions, created = create_session(db)
    storage, timeline = Storage(), Timeline()
    videos = VideoService(db, storage, Athletes(), timeline)
    upload = videos.request_upload(
        sessions.get_model(created.id, created.coach_user_id, "token"),
        UploadUrlRequest(filename="clip.mp4", content_type="video/mp4", file_size_bytes=100),
    )
    first = videos.complete(upload.video_id, UploadCompletionRequest(checksum="sha"), created.coach_user_id, "token")
    second = videos.complete(upload.video_id, UploadCompletionRequest(), created.coach_user_id, "token")
    assert first.upload_status == second.upload_status == UploadStatus.UPLOADED
    assert first.etag == "storage-etag" and len(timeline.calls) == 1


@pytest.mark.parametrize(
    "metadata,error",
    [
        (ObjectMetadata(False), ConflictError),
        (ObjectMetadata(True, 99, "video/mp4"), ConflictError),
        (ObjectMetadata(True, 100, "text/plain"), UnsupportedMediaTypeError),
    ],
)
def test_completion_rejects_invalid_object(db, metadata, error):
    sessions, created = create_session(db)
    storage = Storage()
    storage.metadata = metadata
    videos = VideoService(db, storage, Athletes(), Timeline())
    upload = videos.request_upload(
        sessions.get_model(created.id, created.coach_user_id, "token"),
        UploadUrlRequest(filename="clip.mp4", content_type="video/mp4", file_size_bytes=100),
    )
    with pytest.raises(error):
        videos.complete(upload.video_id, UploadCompletionRequest(), created.coach_user_id, "token")


def test_delete_is_soft_and_idempotent(db):
    sessions, created = create_session(db)
    storage = Storage()
    videos = VideoService(db, storage, Athletes(), Timeline())
    upload = videos.request_upload(
        sessions.get_model(created.id, created.coach_user_id, "token"),
        UploadUrlRequest(filename="clip.mp4", content_type="video/mp4", file_size_bytes=100),
    )
    videos.delete(upload.video_id, created.coach_user_id, "token")
    videos.delete(upload.video_id, created.coach_user_id, "token")
    assert len(storage.deleted) == 1


def test_timeline_failure_does_not_undo_completion(db):
    class FailingTimeline:
        def publish_video_uploaded(self, **kwargs):
            raise RuntimeError("upstream unavailable")

    sessions, created = create_session(db)
    videos = VideoService(db, Storage(), Athletes(), FailingTimeline())
    upload = videos.request_upload(
        sessions.get_model(created.id, created.coach_user_id, "token"),
        UploadUrlRequest(filename="clip.mp4", content_type="video/mp4", file_size_bytes=100),
    )
    result = videos.complete(upload.video_id, UploadCompletionRequest(), created.coach_user_id, "token")
    assert result.upload_status == UploadStatus.UPLOADED
