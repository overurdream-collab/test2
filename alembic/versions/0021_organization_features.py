"""Organization feature catalog and temporal grants.

Revision ID: 0021_organization_features
Revises: 0019_rbac

Catalog entries describe capabilities, not backend readiness or permissions.
No organization receives a feature grant from this migration.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import TIMESTAMP

revision = "0021_organization_features"
down_revision = "0019_rbac"
branch_labels = None
depends_on = None


_CONTAINERS = (
    ("dashboard", "الملخص", "Dashboard", 5),
    ("inputs", "المدخلات", "Inputs", 10),
    ("beneficiaries", "المستفيدون", "Beneficiaries", 20),
    ("providers", "مقدمو الخدمة", "Providers", 30),
    ("users", "المستخدمون", "Users", 40),
    ("claims", "المطالبات", "Claims", 50),
    ("audit", "التدقيق", "Audit", 60),
    ("governance", "الحوكمة", "Governance", 70),
    ("reports", "التقارير", "Reports", 80),
    ("intelligence", "التحليل", "Intelligence", 90),
    ("system", "النظام", "System", 100),
)
_LEAVES = (
    ("dashboard.summary", "الملخص التنفيذي", "Executive summary", 6),
    ("inputs.contracts", "العقود", "Contracts", 11),
    ("inputs.regulations", "الآليات واللوائح", "Regulations", 12),
    ("inputs.exceptions", "الاستثناءات", "Exceptions", 13),
    ("inputs.approvals", "الموافقات والتفويضات", "Approvals", 14),
    ("inputs.caps", "السقوف", "Caps", 15),
    ("inputs.coverage", "التغطية", "Coverage", 16),
    ("beneficiaries.names", "أسماء المستفيدين", "Beneficiary names", 21),
    ("beneficiaries.categories", "فئات المستفيدين", "Beneficiary categories", 22),
    ("beneficiaries.cost_sharing", "المشاركة في التكلفة", "Cost sharing", 23),
    ("providers.hospitals", "المستشفيات", "Hospitals", 31),
    ("providers.clinics", "العيادات", "Clinics", 32),
    ("providers.labs", "المختبرات", "Laboratories", 33),
    ("providers.radiology", "الأشعة", "Radiology", 34),
    ("providers.pharmacies", "الصيدليات", "Pharmacies", 35),
    ("providers.services", "الخدمات", "Services", 36),
    ("providers.prices", "التسعيرات", "Prices", 37),
    ("users.list", "قائمة المستخدمين", "User list", 41),
    ("users.groups", "فئات المستخدمين", "User groups", 42),
    ("users.permissions", "صلاحيات المستخدمين", "User permissions", 43),
    ("claims.list", "قائمة المطالبات", "Claim list", 51),
    ("claims.batches", "دفعات المطالبات", "Claim batches", 52),
    ("claims.import", "استيراد المطالبات", "Claim import", 53),
    ("audit.snapshots", "لقطات التدقيق", "Audit snapshots", 61),
    ("audit.findings", "نتائج التدقيق", "Audit findings", 62),
    ("governance.cases", "حالات المراجعة", "Review cases", 71),
    ("governance.appeals", "الاعتراضات والتظلمات", "Appeals", 72),
    ("reports.list", "قائمة التقارير", "Report list", 81),
    ("reports.export", "تصدير التقارير", "Report export", 82),
    ("intelligence.analysis", "التحليلات", "Analysis", 91),
    ("intelligence.signals", "الإشارات التحليلية", "Analysis signals", 92),
    ("system.audit_log", "سجل التدقيق", "Audit log", 101),
    ("system.health", "صحة النظام", "System health", 102),
)


def _catalog_rows():
    """Validate the frozen catalog and return parents before children."""
    rows = []
    for definitions, is_container in ((_CONTAINERS, True), (_LEAVES, False)):
        for code, name_ar, name_en, order in definitions:
            rows.append({
                "code": code,
                "category": code.split(".", 1)[0],
                "parent_code": None if is_container else code.rsplit(".", 1)[0],
                "name_ar": name_ar,
                "name_en": name_en,
                "is_container": is_container,
                "display_order": order,
            })
    if (len(rows) != 44 or sum(row["is_container"] for row in rows) != 11
            or sum(not row["is_container"] for row in rows) != 33):
        raise ValueError("Feature catalog must contain 11 containers and 33 leaves")
    by_code = {row["code"]: row for row in rows}
    if len(by_code) != len(rows):
        raise ValueError("Feature catalog codes must be unique")
    for row in rows:
        parent = row["parent_code"]
        if parent == row["code"]:
            raise ValueError("Feature cannot be its own parent")
        if parent is not None and (parent not in by_code or not by_code[parent]["is_container"]):
            raise ValueError("Feature parent must exist and be a container")

    visiting, visited, ordered = set(), set(), []

    def visit(code):
        if code in visiting:
            raise ValueError("Feature catalog must not contain cycles")
        if code in visited:
            return
        visiting.add(code)
        parent = by_code[code]["parent_code"]
        if parent is not None:
            visit(parent)
        visiting.remove(code)
        visited.add(code)
        ordered.append(by_code[code])

    for row in sorted(rows, key=lambda item: (item["display_order"], item["code"])):
        visit(row["code"])
    return ordered


def upgrade():
    # Validate before changing the schema or inserting any reference data.
    catalog = _catalog_rows()
    op.create_table(
        "feature_catalog",
        sa.Column("code", sa.String(100), primary_key=True),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("parent_code", sa.String(100), nullable=True),
        sa.Column("name_ar", sa.String(200), nullable=False),
        sa.Column("name_en", sa.String(200), nullable=True),
        sa.Column("description_ar", sa.Text, nullable=True),
        sa.Column("description_en", sa.Text, nullable=True),
        sa.Column("is_container", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("display_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_system", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["parent_code"], ["feature_catalog.code"]),
        sa.CheckConstraint("parent_code IS NULL OR parent_code != code", name="ck_feature_catalog_parent"),
    )
    op.create_index("ix_feature_catalog_parent", "feature_catalog", ["parent_code"])
    op.create_index("ix_feature_catalog_category", "feature_catalog", ["category"])

    op.create_table(
        "organization_features",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("feature_code", sa.String(100), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("effective_from", sa.Date, nullable=False),
        sa.Column("effective_to", sa.Date, nullable=True),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("granted_by", sa.String(36), nullable=False),
        sa.Column("granted_at", TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("closed_by", sa.String(36), nullable=True),
        sa.Column("closed_at", TIMESTAMP(timezone=True), nullable=True),
        sa.Column("close_reason", sa.Text, nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["feature_code"], ["feature_catalog.code"]),
        sa.ForeignKeyConstraint(["granted_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["closed_by"], ["users.id"]),
        sa.CheckConstraint("status IN ('open', 'closed')", name="ck_org_features_status"),
        sa.CheckConstraint("version >= 1", name="ck_org_features_version"),
        sa.CheckConstraint(
            "(status = 'open' AND effective_to IS NULL AND closed_by IS NULL "
            "AND closed_at IS NULL AND close_reason IS NULL) OR "
            "(status = 'closed' AND effective_to IS NOT NULL AND closed_by IS NOT NULL "
            "AND closed_at IS NOT NULL AND close_reason IS NOT NULL "
            "AND length(trim(close_reason)) > 0)",
            name="ck_org_features_lifecycle",
        ),
        sa.CheckConstraint("effective_to IS NULL OR effective_to >= effective_from", name="ck_org_features_dates"),
        sa.UniqueConstraint("organization_id", "feature_code", "version", name="uq_org_features_org_code_version"),
    )
    op.create_index("ix_org_features_org", "organization_features", ["organization_id"])
    op.create_index("ix_org_features_code", "organization_features", ["feature_code"])
    op.create_index("ix_org_features_status", "organization_features", ["status"])
    op.create_index("ix_org_features_lookup", "organization_features", ["organization_id", "feature_code", "status"])
    # btree_gist is already installed by ancestor revision 0008_g3_guards.
    op.execute("""
        ALTER TABLE organization_features
        ADD CONSTRAINT ex_org_features_unique_open
        EXCLUDE USING gist (
            organization_id WITH =,
            feature_code WITH =,
            daterange(effective_from, COALESCE(effective_to, 'infinity'::date), '[)') WITH &&
        ) WHERE (status = 'open')
    """)
    op.execute("""
        CREATE TRIGGER trg_prevent_delete_organization_features
        BEFORE DELETE ON organization_features
        FOR EACH ROW EXECUTE FUNCTION mcias_prevent_delete()
    """)
    op.execute("""
        CREATE TRIGGER trg_check_close_organization_features
        BEFORE UPDATE ON organization_features
        FOR EACH ROW EXECUTE FUNCTION mcias_check_close()
    """)
    for row in catalog:
        # Direct parameterized SQL; no imports from changing Models or Services.
        op.execute(sa.text("""
            INSERT INTO feature_catalog
                (code, category, parent_code, name_ar, name_en, is_container, display_order)
            VALUES
                (:code, :category, :parent_code, :name_ar, :name_en, :is_container, :display_order)
        """).bindparams(**row))


def downgrade():
    op.execute("DROP TRIGGER IF EXISTS trg_prevent_delete_organization_features ON organization_features")
    op.execute("DROP TRIGGER IF EXISTS trg_check_close_organization_features ON organization_features")
    op.drop_table("organization_features")
    op.drop_table("feature_catalog")
