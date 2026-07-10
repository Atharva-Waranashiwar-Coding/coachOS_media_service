# CoachOS Media Service

Standalone FastAPI service owning practice sessions, private video records, signed S3-compatible uploads, upload verification, and upload lifecycle state.

## Architecture

Thin versioned endpoints call domain services. Repositories own SQLAlchemy queries, `S3StorageProvider` owns boto3 behavior, and `AthleteServiceClient` verifies coach access without cross-service database reads. JWTs are validated locally with the shared Auth Service secret. Timeline publication is best-effort after a verified upload commits, forming the boundary for a future transactional outbox.

Owned tables are `practice_sessions` and `videos`. Athlete and user UUIDs are external references; only `videos.practice_session_id` is a local foreign key.

## Upload Workflow

1. Coach creates or opens a non-terminal practice session.
2. `POST .../videos/upload-url` validates athlete access, filename, MIME type, and size.
3. The service creates a pending video and returns a presigned PUT URL requiring `Content-Type`.
4. The browser uploads bytes directly to private S3 or MinIO.
5. `POST /videos/{id}/complete-upload` performs S3 `HEAD`, validates size and MIME type, and marks the video uploaded.
6. The service optionally publishes a safe `video_uploaded` timeline event. Failure does not undo upload completion.

## API

- `POST/GET /api/v1/practice-sessions`
- `GET/PATCH /api/v1/practice-sessions/{id}`
- `POST /api/v1/practice-sessions/{id}/complete`
- `POST /api/v1/practice-sessions/{id}/cancel`
- `POST /api/v1/practice-sessions/{id}/videos/upload-url`
- `GET /api/v1/practice-sessions/{id}/videos`
- `POST /api/v1/videos/{id}/complete-upload`
- `GET/DELETE /api/v1/videos/{id}`
- `GET /api/v1/athletes/{id}/videos`
- `GET /health/live`, `GET /health/ready`, OpenAPI at `/docs`

## Setup

Use `.env.example` as the configuration reference. Important groups are database and JWT settings, Athlete Service URLs, S3 credentials/bucket/endpoint, upload expiry and limits, timeline service credentials, pagination, logging, and CORS. `VITE_*`-style public variables are not used here.

```bash
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8003
```

Docker Compose starts PostgreSQL on `5434`, MinIO on `9000` with console `9001`, creates the private `coachos-videos` bucket, and starts the API on `8003`:

```bash
docker compose up --build
docker compose exec media-service alembic upgrade head
```

## Quality

```bash
black --check app tests alembic
ruff check app tests alembic
mypy app
pytest -q
```

Security decisions include private buckets, short-lived signed PUT URLs, signed content type, no proxied bytes, no permanent media URLs, no logged tokens/URLs/credentials, soft deletion, hidden cross-coach resources, and storage verification before trusting completion.

Known limitations: single-part uploads only, no media probing/transcoding/thumbnails, synchronous best-effort timeline delivery, shared-secret JWT validation, and storage deletion preceding the database soft-delete transaction. AI Review can later consume uploaded video IDs and private storage references through trusted service APIs without changing public bucket policy.
