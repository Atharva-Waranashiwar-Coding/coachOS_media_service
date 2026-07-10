from enum import StrEnum


class UserRole(StrEnum):
    COACH = "coach"
    ATHLETE = "athlete"
    ADMIN = "admin"


class SessionType(StrEnum):
    PRACTICE = "practice"
    GAME = "game"
    BULLPEN = "bullpen"
    BATTING = "batting"
    FIELDING = "fielding"
    STRENGTH = "strength"
    ASSESSMENT = "assessment"
    OTHER = "other"


class SessionStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class UploadStatus(StrEnum):
    PENDING = "pending"
    UPLOADING = "uploading"
    UPLOADED = "uploaded"
    FAILED = "failed"
    EXPIRED = "expired"
    DELETED = "deleted"


class ProcessingStatus(StrEnum):
    NOT_STARTED = "not_started"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
