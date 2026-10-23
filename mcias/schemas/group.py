from datetime import date, datetime
from typing import Annotated, Literal
from pydantic import Field, StringConstraints
from mcias.schemas.common import Input, Page, Read

class GroupCreate(Input):
    management_scope: Literal["functional", "institution_admin"] = "functional"
    code: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,79}$")
    name_ar: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
    name_en: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=2000)

class GroupRead(Read):
    management_scope: str
    id: str
    organization_id: str
    code: str
    name_ar: str
    name_en: str | None
    description: str | None
    is_system: bool
    status: str
    effective_from: date
    effective_to: date | None
    version: int
    created_at: datetime

class GroupDetail(GroupRead):
    members: Page[str]
    permission_ids: Page[str]
