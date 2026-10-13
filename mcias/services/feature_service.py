"""Versioned, atomic feature entitlements. Callers own commits. No financial authority."""
from datetime import date, datetime, timezone
from hashlib import sha256
import json
from sqlalchemy import func, select
from mcias.models import AuditLog, Organization, User
from mcias.models_features import FeatureCatalog, OrganizationFeature
from mcias.services import rbac_service as rbac
from mcias.services.authorization_service import check_permission_unified

READ_PERMISSIONS = {
    "dashboard.summary": ("reports.read",),
    "inputs.contracts": ("reference.contracts.read", "reference.read"),
    "inputs.regulations": ("reference.coverage.read", "reference.read"),
    "inputs.exceptions": ("reference.exceptions.read", "reference.read"),
    "inputs.approvals": ("reference.contracts.read", "reference.read"),
    "inputs.caps": ("reference.caps.read", "reference.read"),
    "inputs.coverage": ("reference.coverage.read", "reference.read"),
    "beneficiaries.names": ("reference.beneficiaries.read",),
    "beneficiaries.categories": ("reference.categories.read", "reference.read"),
    "beneficiaries.cost_sharing": ("reference.cost_sharing.read", "reference.read"),
    **{f"providers.{kind}": ("reference.providers.read", "reference.read") for kind in ("hospitals", "clinics", "labs", "radiology", "pharmacies")},
    "providers.services": ("reference.providers.read", "reference.read"),
    "providers.prices": ("reference.prices.read", "reference.read"),
    **{f"users.{kind}": (permission,) for kind, permission in (("list", "users.read"), ("groups", "groups.read"), ("permissions", "permissions.read"))},
    **{f"claims.{kind}": ("claims.read",) for kind in ("list", "batches", "import")},
    **{f"audit.{kind}": ("audit.read", "claims.read") for kind in ("snapshots", "findings")},
    **{f"governance.{kind}": ("claims.read",) for kind in ("cases", "appeals")},
    "reports.list": ("reports.read",), "reports.export": ("reports.export",),
    "intelligence.analysis": ("intelligence.read",), "intelligence.signals": ("intelligence.read",),
    "system.audit_log": ("system.audit_log.read",), "system.health": ("system.health.read",),
}

def is_super_admin(db, user):
    return bool(rbac._live_user(user, date.today()) and rbac._technical_admin(db, user))

def permitted(db, user, *codes):
    return rbac._live_user(user, date.today()) and any(
        check_permission_unified(db, user, code) for code in codes)

def permission_codes(db, user):
    from mcias.services.authorization_service import permission_codes as current_codes
    return current_codes(db,user)


def list_features(db):
    return list(db.scalars(select(FeatureCatalog).order_by(FeatureCatalog.display_order, FeatureCatalog.code)))

def list_feature_tree(db):
    rows = list_features(db)
    nodes = {r.code: {"code": r.code, "name_ar": r.name_ar, "name_en": r.name_en,
        "is_container": r.is_container, "display_order": r.display_order, "children": []} for r in rows}
    roots = []
    for row in rows:
        if row.parent_code:
            if row.parent_code not in nodes or not nodes[row.parent_code]["is_container"]:
                raise ValueError("Invalid feature tree parent")
            cursor, seen = row, set()
            by_code = {r.code: r for r in rows}
            while cursor.parent_code:
                if cursor.code in seen:
                    raise ValueError("Cyclic feature tree")
                seen.add(cursor.code)
                cursor = by_code[cursor.parent_code]
            nodes[row.parent_code]["children"].append(nodes[row.code])
        else:
            roots.append(nodes[row.code])
    return roots

def get_org_features(db, org_id):
    return list(db.scalars(select(OrganizationFeature).where(
        OrganizationFeature.organization_id == org_id, *rbac._live(OrganizationFeature, date.today())
    ).order_by(OrganizationFeature.feature_code)))

def check_feature(db, org_id, code):
    leaf = db.get(FeatureCatalog, code)
    if leaf is None or leaf.is_container:
        return False
    return db.scalar(select(OrganizationFeature.id).where(OrganizationFeature.organization_id == org_id,
        OrganizationFeature.feature_code == code, *rbac._live(OrganizationFeature, date.today())).limit(1)) is not None

def _actor(db, actor_id, org_id):
    actor = db.scalar(select(User).where(User.id == actor_id).with_for_update().execution_options(populate_existing=True))
    if not is_super_admin(db, actor):
        raise ValueError("MFA-enabled active super_admin required")
    org = db.scalar(select(Organization).where(Organization.id == org_id).with_for_update())
    if org is None:
        raise ValueError("Organization does not exist")
    return actor

def _leaf(db, code):
    leaf = db.get(FeatureCatalog, code)
    if leaf is None or leaf.is_container:
        raise ValueError("An existing leaf feature is required; containers cannot be granted")
    return leaf

def _audit(db, actor, org_id, action, row, before, after):
    db.add(AuditLog(actor_id=actor.id, organization_id=org_id, actor_username=actor.username,
        action=action, resource_type="organization_feature", resource_id=row.id,
        category="features", before_state=before, after_state=after, details={"feature_code": row.feature_code}))

def grant_feature(db, org_id, code, granted_by):
    with rbac._atomic(db):
        actor = _actor(db, granted_by, org_id)
        _leaf(db, code)
        existing = db.scalar(select(OrganizationFeature.id).where(
            OrganizationFeature.organization_id == org_id, OrganizationFeature.feature_code == code,
            OrganizationFeature.status == "open"))
        if existing:
            raise ValueError("An open or future grant already exists")
        version = (db.scalar(select(func.max(OrganizationFeature.version)).where(
            OrganizationFeature.organization_id == org_id, OrganizationFeature.feature_code == code)) or 0) + 1
        row = OrganizationFeature(organization_id=org_id, feature_code=code, status="open",
            effective_from=date.today(), version=version, granted_by=actor.id)
        db.add(row); db.flush()
        _audit(db, actor, org_id, "feature.grant", row, None, {"status": "open", "version": version})
        return row

def revoke_feature(db, org_id, code, closed_by, reason):
    with rbac._atomic(db):
        actor = _actor(db, closed_by, org_id)
        _leaf(db, code)
        rows = [r for r in get_org_features(db, org_id) if r.feature_code == code]
        if len(rows) != 1:
            raise ValueError("Exactly one current open grant is required")
        row = rows[0]
        rbac._close(row, actor, reason, date.today())
        db.flush()
        _audit(db, actor, org_id, "feature.revoke", row, {"status": "open"},
            {"status": "closed", "version": row.version, "reason": row.close_reason})
        return row

def grant_revision(db, org_id):
    # Includes historical versions, so a grant/revoke cycle invalidates stale editors.
    rows = db.scalars(select(OrganizationFeature).where(OrganizationFeature.organization_id == org_id)
        .order_by(OrganizationFeature.feature_code, OrganizationFeature.version))
    content = [(r.feature_code, r.version, r.status, str(r.effective_from), str(r.effective_to)) for r in rows]
    return sha256(json.dumps(content, separators=(",", ":")).encode()).hexdigest()

def replace_features(db, org_id, codes, actor_id, reason, expected_revision):
    with rbac._atomic(db):
        _actor(db, actor_id, org_id)
        if grant_revision(db, org_id) != expected_revision:
            raise ValueError("Features changed; reload before saving")
        if len(codes) != len(set(codes)):
            raise ValueError("Duplicate feature codes")
        for code in codes:
            _leaf(db, code)
        before = {r.feature_code for r in get_org_features(db, org_id)}
        wanted = set(codes)
        for code in sorted(before - wanted):
            revoke_feature(db, org_id, code, actor_id, reason)
        for code in sorted(wanted - before):
            grant_feature(db, org_id, code, actor_id)
        return get_org_features(db, org_id)

def get_visible_features(db, user):
    if not rbac._live_user(user, date.today()) or not user.organization_id:
        return []
    if is_super_admin(db, user):
        return [r.code for r in list_features(db) if not r.is_container]
    return [r.feature_code for r in get_org_features(db, user.organization_id)
        if permitted(db, user, *READ_PERMISSIONS.get(r.feature_code, ()))]
