from datetime import datetime
from pydantic import BaseModel
from mcias.schemas.common import Read
from mcias.schemas.user import UserRead

class PermissionRead(Read):
    id: str
    code: str
    category: str | None
    description_ar: str | None
    description_en: str | None
    is_system: bool
    created_at: datetime

class PermissionContext(BaseModel):
    user: UserRead
    permission_ids: list[str]
    permission_codes: list[str]
    group_ids: list[str]
    legacy_roles: list[str]
    technical_rbac_admin: bool
    expires_at: datetime
