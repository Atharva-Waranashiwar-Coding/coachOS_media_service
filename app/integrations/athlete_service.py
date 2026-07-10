from uuid import UUID

import httpx

from app.core.config import settings
from app.core.exceptions import NotFoundError, UnauthorizedError, UpstreamServiceError


class AthleteServiceClient:
    """Verify athlete access through the Athlete Service public API."""

    def verify_access(self, athlete_id: UUID, bearer_token: str) -> None:
        try:
            response = httpx.get(
                f"{settings.athlete_service_url.rstrip('/')}/api/v1/athletes/{athlete_id}",
                headers={"Authorization": f"Bearer {bearer_token}"},
                timeout=settings.upstream_timeout_seconds,
            )
        except httpx.HTTPError as exc:
            raise UpstreamServiceError("Athlete Service is unavailable.") from exc
        if response.status_code == 200:
            return
        if response.status_code == 404:
            raise NotFoundError("Athlete not found.")
        if response.status_code in {401, 403}:
            raise UnauthorizedError("Athlete access could not be verified.")
        raise UpstreamServiceError("Athlete Service is unavailable.")
