# CoachOS Media Service

Video upload, storage metadata, and practice session service for CoachOS.

## Responsibilities

- Practice session records
- Video upload metadata
- Signed upload URL flow
- Cloud storage integration
- Video status tracking
- Athlete and session video linking

## Tech Stack

- Python
- FastAPI
- PostgreSQL
- SQLAlchemy
- Alembic
- Docker
- Cloud object storage later

## Project Structure

- `app/api`: API route modules
- `app/core`: configuration
- `app/db`: database connection and session setup
- `app/models`: database models
- `app/schemas`: request and response schemas
- `app/services`: media and storage business logic
- `app/utils`: shared utilities
- `alembic`: database migrations
- `tests`: service tests

## Environment

Copy `.env.example` to `.env` for local development. Do not commit `.env`.

Required values:

- `APP_NAME`
- `ENVIRONMENT`
- `DATABASE_URL`

Future storage values:

- `STORAGE_PROVIDER`
- `STORAGE_BUCKET`
- `STORAGE_REGION`

## Running Locally

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The service exposes:

- Local app: `http://localhost:8000`
- Docker Compose port: `http://localhost:8003`
- Health check: `GET /health`

## Docker

```bash
docker compose up --build
```

## Planned API

- `POST /practice-sessions`
- `GET /practice-sessions/{session_id}`
- `POST /videos/upload-url`
- `POST /videos/{video_id}/complete-upload`
- `GET /videos/{video_id}`
- `GET /athletes/{athlete_id}/videos`

## Testing

```bash
pytest
```

## Status

Stage 0: service skeleton created. Practice session models, signed upload flow, storage integration, and tests are next.
