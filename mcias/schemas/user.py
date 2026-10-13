from datetime import date, datetime
from uuid import UUID
from pydantic import Field, SecretStr
from mcias.schemas.common import Input, Read, Reason

class UserCreate(Input):
    username: str = Field(min_length=1, max_length=120)
    password: SecretStr = Field(min_length=12, max_length=1024)
    full_name_ar: str | None = Field(default=None, max_length=200)
    email: str | None = Field(default=None, max_length=200)

class UserRead(Read):
    id: str
    organization_id: str | None
    username: str
    full_name_ar: str | None
    full_name_en: str | None
    email: str | None
    active: bool
    status: str
    effective_from: date
    effective_to: date | None
    version: int
    created_at: datetime

class GroupTransfer(Input):
    from_group_id: UUID
    to_group_id: UUID
    reason: Reason
