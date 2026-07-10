from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest

from app.core.exceptions import UnauthorizedError
from app.core.security import validate_access_token


def token(**overrides):
    payload = {
        "sub": str(uuid4()),
        "email": "coach@example.com",
        "role": "coach",
        "exp": datetime.now(UTC) + timedelta(minutes=5),
    }
    payload.update(overrides)
    return jwt.encode(payload, "test-secret", algorithm="HS256")


def test_valid_coach_token():
    assert validate_access_token(token()).role.value == "coach"


@pytest.mark.parametrize("value", ["invalid", token(exp=datetime.now(UTC) - timedelta(seconds=1))])
def test_invalid_and_expired_token(value):
    with pytest.raises(UnauthorizedError):
        validate_access_token(value)
