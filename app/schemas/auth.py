from uuid import UUID

from pydantic import BaseModel, EmailStr

from app.models.enums import UserRole


class CurrentUser(BaseModel):
    id: UUID
    email: EmailStr
    role: UserRole
