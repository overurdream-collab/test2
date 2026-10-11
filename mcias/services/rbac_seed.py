"""Explicit RBAC catalog initialization: 94 permissions and eight tenant groups.

This is configuration, not synthetic claims or an institutional approval.
It never assigns memberships or restores grants on existing groups.
"""
from datetime import date

from sqlalchemy import select

from mcias.models import Group, GroupPermission, Organization, Permission
from mcias.services import rbac_service as rbac

_CATALOG = {
    "system": "read configure backup restore audit_log.read audit_log.export health.read feature_flags.manage",
    "organizations": "read create update deactivate features.manage settings.manage",
    "users": "read create update close reopen reset_password mfa.manage permissions.grant permissions.revoke",
    "groups": "read create update close permissions.grant permissions.revoke members.add members.remove",
    "permissions": "read assign",
    "reference": "contracts.read contracts.create contracts.update contracts.close contracts.approve "
        "prices.read prices.create prices.update prices.close beneficiaries.read beneficiaries.create beneficiaries.close "
        "categories.read categories.create categories.close cost_sharing.read cost_sharing.create cost_sharing.close "
        "caps.read caps.create caps.close coverage.read coverage.create coverage.close "
        "exceptions.read exceptions.create exceptions.close providers.read providers.create providers.close",
    "ingestion": "read upload quarantine.read quarantine.resolve reprocess",
    "claims": "read import review approve reject",
    "audit": "read run export reconcile",
    "governance": "propose review approve object reaudit",
    "reports": "read create export beneficiary.read originals.export medical.read",
    "intelligence": "read run review studio.manage",
    "retention": "read archive",
}
_LABELS = {
    "system": ("النظام", "System"), "organizations": ("الجهات", "Organizations"),
    "users": ("المستخدمون", "Users"), "groups": ("المجموعات", "Groups"),
    "permissions": ("الصلاحيات", "Permissions"), "reference": ("البيانات المرجعية", "Reference data"),
    "ingestion": ("الاستيعاب", "Ingestion"), "claims": ("المطالبات", "Claims"),
    "audit": ("التدقيق", "Audit"), "governance": ("الحوكمة", "Governance"),
    "reports": ("التقارير", "Reports"), "intelligence": ("التحليلات", "Intelligence"),
    "retention": ("الاحتفاظ", "Retention"), "audit_log": ("سجل التدقيق", "Audit log"),
    "health": ("حالة النظام", "Health"), "feature_flags": ("الميزات", "Feature flags"),
    "features": ("الميزات", "Features"), "settings": ("الإعدادات", "Settings"),
    "mfa": ("المصادقة متعددة العوامل", "MFA"), "members": ("الأعضاء", "Members"),
    "contracts": ("العقود", "Contracts"), "prices": ("التسعيرات", "Prices"),
    "beneficiaries": ("المستفيدون", "Beneficiaries"), "categories": ("الفئات", "Categories"),
    "cost_sharing": ("المشاركة في التكلفة", "Cost sharing"), "caps": ("السقوف", "Caps"),
    "coverage": ("التغطية", "Coverage"), "exceptions": ("الاستثناءات", "Exceptions"),
    "providers": ("مقدمو الخدمات", "Providers"), "quarantine": ("العزل", "Quarantine"),
    "beneficiary": ("المستفيد", "Beneficiary"), "originals": ("الأصول", "Originals"),
    "medical": ("البيانات الطبية", "Medical data"), "studio": ("استوديو التحليل", "Analysis studio"),
}
_ACTIONS = {
    "read": ("قراءة", "Read"), "configure": ("تهيئة", "Configure"),
    "backup": ("نسخ احتياطي", "Back up"), "restore": ("استعادة", "Restore"),
    "export": ("تصدير", "Export"), "manage": ("إدارة", "Manage"),
    "create": ("إنشاء", "Create"), "update": ("تحديث", "Update"),
    "deactivate": ("تعطيل", "Deactivate"), "close": ("إغلاق", "Close"),
    "reopen": ("طلب إنشاء بديل للسجل المغلق", "Request a replacement for a closed record"),
    "reset_password": ("إعادة تعيين كلمة المرور", "Reset password"),
    "grant": ("منح", "Grant"), "revoke": ("سحب", "Revoke"),
    "add": ("إضافة", "Add"), "remove": ("إزالة", "Remove"),
    "assign": ("إسناد", "Assign"), "approve": ("اعتماد", "Approve"),
    "upload": ("رفع", "Upload"), "resolve": ("معالجة", "Resolve"),
    "reprocess": ("إعادة معالجة", "Reprocess"), "import": ("استيراد", "Import"),
    "review": ("مراجعة", "Review"), "reject": ("رفض", "Reject"),
    "run": ("تشغيل", "Run"), "reconcile": ("مطابقة", "Reconcile"),
    "propose": ("اقتراح", "Propose"), "object": ("اعتراض", "Object"),
    "reaudit": ("إعادة تدقيق", "Re-audit"), "archive": ("أرشفة", "Archive"),
}


def get_all_permissions():
    result = []
    for category, suffixes in _CATALOG.items():
        for suffix in suffixes.split():
            parts = [category, *suffix.split(".")]
            action_ar, action_en = _ACTIONS[parts[-1]]
            labels = [_LABELS[part] for part in parts[:-1]]
            result.append({"code": ".".join(parts), "category": category.upper(),
                "description_ar": action_ar + " — " + " / ".join(label[0] for label in labels),
                "description_en": action_en + " — " + " / ".join(label[1] for label in labels),
                "is_system": True})
    return result


def get_default_groups():
    codes = [permission["code"] for permission in get_all_permissions()]
    viewer_exclusions = {"reports.medical.read", "reports.beneficiary.read", "reference.beneficiaries.read"}
    definitions = [
        ("admin", "مدير الجهة", "Entity Admin", [c for c in codes if not c.startswith(("system.", "organizations."))]),
        ("reference_manager", "مدير المراجع", "Reference Manager", [c for c in codes if c.startswith("reference.")]),
        ("ingestion_operator", "مشغل الاستيعاب", "Ingestion Operator", [c for c in codes if c.startswith("ingestion.")]),
        ("claims_reviewer", "مراجع المطالبات", "Claims Reviewer", ["claims.read", "claims.review", "audit.read", "reports.read"]),
        ("claims_approver", "معتمد المطالبات", "Claims Approver", ["claims.read", "claims.approve", "claims.reject", "audit.read", "reports.read", "governance.approve"]),
        ("auditor", "مدقق", "Auditor", [c for c in codes if c.startswith("audit.")] + ["reports.read", "reports.export", "governance.propose", "governance.review", "governance.reaudit"]),
        ("reporter", "معد التقارير", "Reporter", ["reports.read", "reports.create", "reports.export", "reports.beneficiary.read"]),
        ("viewer", "مشاهد", "Viewer", [c for c in codes if c.endswith(".read") and not c.startswith(("system.", "organizations.")) and c not in viewer_exclusions]),
    ]
    return [{"code": code, "name_ar": ar, "name_en": en, "permissions": sorted(permissions)}
            for code, ar, en, permissions in definitions]


def seed_organization(db, organization_id, created_by):
    today = date.today()
    counts = {"permissions_created": 0, "groups_created": 0, "group_permissions_created": 0}
    with rbac._atomic(db):
        actor = rbac._actor(db, created_by, organization_id, (), today)
        if not rbac._technical_admin(db, actor):
            raise ValueError("RBAC initialization requires the existing MFA-enabled super_admin role")
        organization = db.scalar(select(Organization).where(Organization.id == organization_id).with_for_update())
        if organization is None:
            raise ValueError("Organization does not exist")
        # Serialize the shared catalog as well as tenant initialization on PostgreSQL.
        if db.get_bind().dialect.name == "postgresql":
            from sqlalchemy import text
            db.execute(text("SELECT pg_advisory_xact_lock(194094)"))
        catalog = {}
        for definition in get_all_permissions():
            permission = db.scalar(select(Permission).where(Permission.code == definition["code"]))
            if permission is None:
                permission = Permission(**definition)
                db.add(permission)
                db.flush()
                counts["permissions_created"] += 1
            catalog[permission.code] = permission
        for definition in get_default_groups():
            if db.scalar(select(Group.id).where(Group.organization_id == organization_id,
                                               Group.code == definition["code"]).limit(1)) is not None:
                continue
            group = Group(organization_id=organization_id, code=definition["code"],
                name_ar=definition["name_ar"], name_en=definition["name_en"], is_system=True,
                status="open", effective_from=today, version=1, created_by=actor.id)
            db.add(group)
            db.flush()
            counts["groups_created"] += 1
            for code in definition["permissions"]:
                permission = catalog[code]
                record = GroupPermission(organization_id=organization_id, group_id=group.id,
                    permission_id=permission.id, status="open", effective_from=today, version=1, granted_by=actor.id)
                db.add(record)
                db.flush()
                counts["group_permissions_created"] += 1
                rbac._audit(db, actor, "group_permission.grant", "group_permission", record,
                            after={"group_id": group.id, "permission_id": permission.id, "status": "open"})
            rbac._audit(db, actor, "group.create", "group", group,
                        after={"code": group.code, "status": "open"})
        if any(counts.values()):
            rbac._audit(db, actor, "rbac.seed", "organization", organization, after=dict(counts))
    return counts
