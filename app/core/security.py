from uuid import UUID

import jwt

from app.core.config import settings
from app.core.exceptions import UnauthorizedError
from app.schemas.auth import CurrentUser


def validate_access_token(token: str) -> CurrentUser:
    """Validate a shared-secret access token without querying Auth Service."""
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        subject = payload.get("sub") or payload.get("user_id")
        return CurrentUser(id=UUID(str(subject)), email=payload["email"], role=payload["role"])
    except (jwt.PyJWTError, KeyError, TypeError, ValueError) as exc:
        raise UnauthorizedError("Invalid or expired access token.") from exc
