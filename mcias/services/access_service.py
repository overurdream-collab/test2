"""Owner-approved interim authority: explicit super-admin grants, no implicit roles.

Old grants remain intact for history. Only records explicitly activated through
this service confer permissions in the default ``super_admin`` authority mode.
Administrative approvals happen outside MCIAS; grant/revoke facts remain logged.
"""
from datetime import date
from hashlib import sha256
import json

from sqlalchemy import select
from mcias.models import AuditLog, Permission, User, UserPermission
from mcias.services import authorization_service as auth
from mcias.services.transaction_lock import lock_record

AUTHORITY = "super_admin_v1"

def registry_codes():
    from mcias.schemas.registry import SCHEMAS
    return {f"registry.{feature}.{operation}" for feature in SCHEMAS for operation in ("read", "create", "update")}

def catalog(db):
    result = {p.code: {"code":p.code, "description_ar":p.description_ar,
        "description_en":p.description_en, "category":p.category} for p in db.scalars(select(Permission))}
    from mcias.schemas.registry import SCHEMAS
    for feature in SCHEMAS:
        for operation, label in (("read","عرض"),("create","إضافة"),("update","تعديل")):
            code=f"registry.{feature}.{operation}"
            result.setdefault(code,{"code":code,"description_ar":f"{label}: {feature}",
                "description_en":f"{operation}: {feature}","category":"reference_intake"})
    return sorted(result.values(),key=lambda p:p['code'])


def _activations(db, organization_id, user_id):
    return list(db.scalars(select(AuditLog).where(
        AuditLog.organization_id == organization_id,
        AuditLog.action == "access.grant",
        AuditLog.resource_type == "user_permission",
        AuditLog.details["authority"].as_string() == AUTHORITY,
        AuditLog.details["user_id"].as_string() == user_id)))


def permission_records(db, user, code=None):
    if not auth.live_user(user) or not user.organization_id:
        return []
    activated = {event.resource_id for event in _activations(db, user.organization_id, user.id)}
    if not activated:
        return []
    query = select(Permission).join(UserPermission, UserPermission.permission_id == Permission.id).where(
        UserPermission.id.in_(activated), UserPermission.user_id == user.id,
        UserPermission.organization_id == user.organization_id,
        *auth.live(UserPermission, date.today()))
    if code:
        query = query.where(Permission.code == code)
    # Delegation administration always stays with the technical super-admin.
    return [p for p in db.scalars(query.order_by(Permission.code)).unique()
            if p.code not in auth.TECHNICAL_ONLY and not p.code.startswith(("system.", "organizations."))]


def revision(db, user):
    events = list(db.scalars(select(AuditLog).where(
        AuditLog.organization_id == user.organization_id,
        AuditLog.category == "access_control",
        AuditLog.details["user_id"].as_string() == user.id).order_by(AuditLog.id)))
    data = [(e.id, e.action, e.resource_id) for e in events]
    return sha256(json.dumps(data, separators=(",", ":")).encode()).hexdigest()


def state(db, actor, user_id):
    if not auth.technical_admin(db, actor):
        raise PermissionError("MFA-enabled super-admin required")
    user = db.get(User, user_id)
    if not user or user.organization_id != actor.organization_id:
        raise LookupError("User not found")
    return {"user_id": user.id, "username": user.username,
            "codes": [p.code for p in permission_records(db, user)],
            "revision": revision(db, user), "authority": AUTHORITY,
            "frozen": not bool(permission_records(db, user)),
            "technical_account": auth.technical_identity(db, user)}


def replace_grants(db, actor, user_id, codes, expected_revision, reason):
    from mcias.services import rbac_service as rbac
    if not auth.technical_admin(db, actor):
        raise PermissionError("MFA-enabled super-admin required")
    if not reason.strip():
        raise ValueError("Administrative action reason required")
    with rbac._atomic(db):
        lock_record(db, "access_user", actor.organization_id, user_id)
        user = db.scalar(select(User).where(User.id == user_id).with_for_update())
        if not user or user.organization_id != actor.organization_id:
            raise LookupError("User not found")
        if auth.technical_identity(db, user):
            raise ValueError("Technical accounts cannot receive functional or financial grants")
        if not auth.live_user(user):
            raise ValueError("Active user required")
        if revision(db, user) != expected_revision:
            raise ValueError("Permissions changed; reload before saving")
        if len(codes) != len(set(codes)):
            raise ValueError("Duplicate permission code")
        permissions = {p.code: p for p in db.scalars(select(Permission))}
        virtual = registry_codes()
        for code in codes:
            if (code not in permissions and code not in virtual) or code in auth.TECHNICAL_ONLY or code.startswith(("system.", "organizations.")):
                raise ValueError("Permission is not delegable: " + code)
        for code in sorted(set(codes) - permissions.keys()):
            permission = Permission(code=code,category="reference_intake",description_ar=code,is_system=True)
            db.add(permission);db.flush();permissions[code]=permission
        wanted = set(codes)
        existing = list(db.scalars(select(UserPermission).where(
            UserPermission.organization_id == user.organization_id,
            UserPermission.user_id == user.id, UserPermission.status == "open").with_for_update()))
        active_ids = {e.resource_id for e in _activations(db, user.organization_id, user.id)}
        for row in existing:
            code = db.get(Permission, row.permission_id).code
            if row.id in active_ids and code not in wanted:
                rbac._close(row, actor, reason, date.today())
                db.add(AuditLog(actor_id=actor.id, organization_id=user.organization_id,
                    action="access.revoke", category="access_control", resource_type="user_permission",
                    resource_id=row.id, details={"authority": AUTHORITY, "user_id": user.id,
                    "code": code, "reason": reason.strip()}))
        db.flush()
        current = {p.code for p in permission_records(db, user)}
        for code in sorted(wanted - current):
            candidates = [r for r in existing if r.status == "open" and r.permission_id == permissions[code].id]
            if len(candidates) > 1 or any(r.effective_from > date.today() or (r.effective_to is not None and r.effective_to<=date.today()) for r in candidates):
                raise ValueError("Future or ambiguous grant requires review")
            row = candidates[0] if candidates else UserPermission(
                organization_id=user.organization_id, user_id=user.id, permission_id=permissions[code].id,
                effective_from=date.today(), status="open", version=1, granted_by=actor.id)
            db.add(row); db.flush()
            db.add(AuditLog(actor_id=actor.id, organization_id=user.organization_id,
                action="access.grant", category="access_control", resource_type="user_permission",
                resource_id=row.id, details={"authority": AUTHORITY, "user_id": user.id,
                    "code": code, "reason": reason.strip()}))
        db.flush()
        return state(db, actor, user.id)
