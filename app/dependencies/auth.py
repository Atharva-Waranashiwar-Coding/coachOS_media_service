from collections.abc import Callable

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import validate_access_token
from app.models.enums import UserRole
from app.schemas.auth import CurrentUser

bearer = HTTPBearer(auto_error=False)


def get_bearer_token(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> str:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise UnauthorizedError("Bearer authentication is required.")
    return credentials.credentials


def get_current_user(token: str = Depends(get_bearer_token)) -> CurrentUser:
    return validate_access_token(token)


def require_roles(*roles: UserRole) -> Callable[..., CurrentUser]:
    def check(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in roles:
            raise ForbiddenError("Coach role is required.")
        return user

    return check


def require_coach(user: CurrentUser = Depends(require_roles(UserRole.COACH))) -> CurrentUser:
    return user
