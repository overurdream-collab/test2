from datetime import date, datetime
from typing import Annotated, Generic, TypeVar
from uuid import UUID
from pydantic import BaseModel, ConfigDict, StringConstraints

Reason = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]
T = TypeVar("T")

class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")

class Read(BaseModel):
    model_config = ConfigDict(from_attributes=True)

class Close(Input):
    reason: Reason

class PermissionGrant(Input):
    permission_id: UUID

class MemberAdd(Input):
    user_id: UUID

class Page(BaseModel, Generic[T]):
    items: list[T]
    offset: int
    limit: int
    has_more: bool

class AssignmentRead(Read):
    id: str
    organization_id: str
    status: str
    effective_from: date
    effective_to: date | None
    version: int
    created_at: datetime
    closed_by: str | None
    closed_at: datetime | None
    close_reason: str | None

class UserGroupRead(AssignmentRead):
    user_id: str
    group_id: str

class GroupPermissionRead(AssignmentRead):
    group_id: str
    permission_id: str

class UserPermissionRead(AssignmentRead):
    user_id: str
    permission_id: str

class SeedRead(BaseModel):
    permissions_created: int
    groups_created: int
    group_permissions_created: int
