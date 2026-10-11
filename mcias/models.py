from decimal import Decimal
from datetime import date, datetime, timezone
from uuid import uuid4
from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint, JSON, Boolean, event, func, text
from sqlalchemy.dialects.postgresql import ExcludeConstraint, JSONB, TIMESTAMP
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

def now_utc():
    return datetime.now(timezone.utc)

def uid():
    return str(uuid4())

class Base(DeclarativeBase):
    pass

class Organization(Base):
    __tablename__ = "organizations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)

class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    organization_id: Mapped[str | None] = mapped_column(ForeignKey("organizations.id"))
    username: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="open", server_default="open", nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, server_default=text("CURRENT_DATE"), nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)
    is_super_admin: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"), nullable=False)
    # 0019 deliberately has no foreign key on users.closed_by.
    closed_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    close_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    full_name_ar: Mapped[str | None] = mapped_column(String(200), nullable=True)
    full_name_en: Mapped[str | None] = mapped_column(String(200), nullable=True)
    email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    __table_args__ = (
        Index("ix_users_status", "status"),
        Index("ix_users_org_status", "organization_id", "status"),
        Index("ix_users_super", "is_super_admin", postgresql_where=text("is_super_admin = true")),
        CheckConstraint("status IN ('open', 'closed')", name="ck_users_status"),
        CheckConstraint("(status = 'open' AND effective_to IS NULL) OR (status = 'closed' AND effective_to IS NOT NULL)", name="ck_users_dates"),
    )

class Role(Base):
    __tablename__ = "roles"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

class UserRole(Base):
    __tablename__ = "user_roles"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    role_id: Mapped[str] = mapped_column(ForeignKey("roles.id"), primary_key=True)

class SourceFile(Base):
    __tablename__ = "source_files"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    original_filename: Mapped[str] = mapped_column(Text, nullable=False)
    storage_key: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)

class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    actor_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(150), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(36))
    details: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)
    organization_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    actor_username: Mapped[str | None] = mapped_column(String(120), nullable=True)
    actor_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    actor_user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    session_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    category: Mapped[str | None] = mapped_column(String(80), nullable=True)
    severity: Mapped[str | None] = mapped_column(String(20), server_default="info", nullable=True)
    resource_snapshot: Mapped[dict | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    before_state: Mapped[dict | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    after_state: Mapped[dict | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    trace_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    endpoint: Mapped[str | None] = mapped_column(String(250), nullable=True)
    method: Mapped[str | None] = mapped_column(String(10), nullable=True)
    result: Mapped[str | None] = mapped_column(String(20), server_default="success", nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # PostgreSQL's 0019 trigger populates these; the ORM does not compute hashes.
    hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    previous_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    __table_args__ = (
        Index("ix_audit_actor_ts", "actor_id", created_at.desc()),
        Index("ix_audit_resource_ts", "resource_type", "resource_id", created_at.desc()),
        Index("ix_audit_action_ts", "action", created_at.desc()),
        Index("ix_audit_category_ts", "category", created_at.desc()),
        Index("ix_audit_result_ts", "result", created_at.desc()),
        Index("ix_audit_org_ts", "organization_id", created_at.desc()),
        Index("ix_audit_request", "request_id"),
        CheckConstraint("severity IS NULL OR severity IN ('info', 'warning', 'error', 'critical')", name="ck_audit_severity"),
        CheckConstraint("result IS NULL OR result IN ('success', 'failure', 'denied')", name="ck_audit_result"),
    )

class Claim(Base):
    __tablename__ = "claims"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    source_id: Mapped[str] = mapped_column(ForeignKey("source_files.id"), nullable=False)
    original_payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    original_claimed_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="imported")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)
    __table_args__ = (CheckConstraint("original_claimed_amount >= 0", name="ck_claim_nonnegative"),)

class Permission(Base):
    __tablename__ = "permissions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    code: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    category: Mapped[str | None] = mapped_column(String(80), nullable=True)
    description_ar: Mapped[str | None] = mapped_column(String(300), nullable=True)
    description_en: Mapped[str | None] = mapped_column(String(300), nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=now_utc, server_default=func.now(), nullable=False)
    __table_args__ = (Index("ix_permissions_category", "category"),)


def _open_assignment_exclusion(name, *identity_columns):
    """Match 0019's PostgreSQL-only temporal exclusions without breaking SQLite."""
    return ExcludeConstraint(
        *((column, "=") for column in identity_columns),
        (text("daterange(effective_from, COALESCE(effective_to, 'infinity'::date), '[)')"), "&&"),
        where=text("status = 'open'"), using="gist", name=name,
    ).ddl_if(dialect="postgresql")


class Group(Base):
    __tablename__ = "groups"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False)
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    name_ar: Mapped[str] = mapped_column(String(200), nullable=False)
    name_en: Mapped[str | None] = mapped_column(String(200), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="open", server_default="open", nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=now_utc, server_default=func.now(), nullable=False)
    closed_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    close_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    __table_args__ = (
        Index("ix_groups_org", "organization_id"),
        Index("ix_groups_status", "status"),
        UniqueConstraint("organization_id", "code", "effective_from", name="uq_groups_org_code_from"),
        CheckConstraint("status IN ('open', 'closed')", name="ck_groups_status"),
        CheckConstraint("(status = 'open' AND effective_to IS NULL) OR (status = 'closed' AND effective_to IS NOT NULL)", name="ck_groups_dates"),
    )


class GroupPermission(Base):
    __tablename__ = "group_permissions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False)
    group_id: Mapped[str] = mapped_column(String(36), ForeignKey("groups.id"), nullable=False)
    permission_id: Mapped[str] = mapped_column(String(36), ForeignKey("permissions.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="open", server_default="open", nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)
    granted_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=now_utc, server_default=func.now(), nullable=False)
    closed_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    close_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    __table_args__ = (
        Index("ix_group_perms_group", "group_id", "status"),
        Index("ix_group_perms_perm", "permission_id"),
        Index("ix_group_perms_org", "organization_id"),
        CheckConstraint("status IN ('open', 'closed')", name="ck_group_perms_status"),
        _open_assignment_exclusion("ex_group_perms_unique_open", "group_id", "permission_id"),
    )


class UserGroup(Base):
    __tablename__ = "user_groups"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    group_id: Mapped[str] = mapped_column(String(36), ForeignKey("groups.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="open", server_default="open", nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)
    added_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=now_utc, server_default=func.now(), nullable=False)
    closed_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    close_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    __table_args__ = (
        Index("ix_user_groups_user", "user_id", "status"),
        Index("ix_user_groups_group", "group_id", "status"),
        Index("ix_user_groups_org", "organization_id"),
        CheckConstraint("status IN ('open', 'closed')", name="ck_user_groups_status"),
        _open_assignment_exclusion("ex_user_groups_unique_open", "user_id", "group_id"),
    )


class UserPermission(Base):
    __tablename__ = "user_permissions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    permission_id: Mapped[str] = mapped_column(String(36), ForeignKey("permissions.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="open", server_default="open", nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)
    granted_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=now_utc, server_default=func.now(), nullable=False)
    closed_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    close_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    __table_args__ = (
        Index("ix_user_perms_user", "user_id", "status"),
        Index("ix_user_perms_org", "organization_id"),
        CheckConstraint("status IN ('open', 'closed')", name="ck_user_perms_status"),
        _open_assignment_exclusion("ex_user_perms_unique_open", "user_id", "permission_id"),
    )

class RolePermission(Base):
    __tablename__ = "role_permissions"
    role_id: Mapped[str] = mapped_column(ForeignKey("roles.id"), primary_key=True)
    permission_id: Mapped[str] = mapped_column(ForeignKey("permissions.id"), primary_key=True)

class SessionToken(Base):
    __tablename__ = "session_tokens"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

class WrittenAuthorization(Base):
    __tablename__ = "written_authorizations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    source_id: Mapped[str] = mapped_column(ForeignKey("source_files.id"), nullable=False)
    approved_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    approved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

class RuleVersion(Base):
    __tablename__ = "rule_versions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    rule_type: Mapped[str] = mapped_column(String(60), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="draft", nullable=False)
    written_authorization_id: Mapped[str | None] = mapped_column(ForeignKey("written_authorizations.id"))

@event.listens_for(Claim, "before_update")
def prevent_original_mutation(mapper, connection, target):
    from sqlalchemy import inspect
    if target.status == "approved":
        raise ValueError("approved claim cannot be modified")
    for field in ("source_id", "original_payload", "original_claimed_amount", "currency"):
        if inspect(target).attrs[field].history.has_changes():
            raise ValueError("original claim fields are immutable")

@event.listens_for(AuditLog, "before_update")
def prevent_audit_mutation(mapper, connection, target):
    raise ValueError("audit log is append-only")

@event.listens_for(AuditLog, "before_delete")
def prevent_audit_deletion(mapper, connection, target):
    raise ValueError("audit log is append-only")

class MFAFactor(Base):
    __tablename__ = "mfa_factors"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    encrypted_secret: Mapped[bytes] = mapped_column(__import__("sqlalchemy").LargeBinary, nullable=False)
    last_accepted_counter: Mapped[int] = mapped_column(Integer, nullable=False, default=-1)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

class LoginAttempt(Base):
    __tablename__ = "login_attempts"
    identity_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    failures: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=now_utc)
