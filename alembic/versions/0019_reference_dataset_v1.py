"""Source-backed G3 dataset versions; one child of the isolated 0018 chain."""
from alembic import op
import sqlalchemy as sa

revision = "0019_reference_dataset_v1"
down_revision = "0018_claim_query_indexes"
branch_labels = depends_on = None


def upgrade():
    op.create_table("reference_dataset_versions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("owner_organization_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("family", sa.String(20), nullable=False),
        sa.Column("dataset_key", sa.String(100), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.String(36), sa.ForeignKey("ingestion_documents.id"), nullable=False),
        sa.Column("job_id", sa.String(36), sa.ForeignKey("ingestion_jobs.id"), nullable=False),
        sa.Column("source_sha256", sa.String(64), nullable=False),
        sa.Column("source_fingerprint", sa.String(64), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_until", sa.Date(), nullable=False),
        sa.Column("coverage_from", sa.Date(), nullable=False),
        sa.Column("coverage_until", sa.Date(), nullable=False),
        sa.Column("scope", sa.JSON(), nullable=False),
        sa.Column("expected_record_count", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("approved_by", sa.String(36), sa.ForeignKey("users.id")),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        sa.Column("approval_event_id", sa.String(36), sa.ForeignKey("audit_log.id")),
        sa.UniqueConstraint("organization_id", "family", "dataset_key", "version", name="uq_reference_dataset_version"),
        sa.CheckConstraint("family IN ('beneficiary','contract','tariff','policy','caps','history')", name="ck_reference_dataset_family"),
        sa.CheckConstraint("version > 0 AND expected_record_count > 0", name="ck_reference_dataset_counts"),
        sa.CheckConstraint("effective_from < effective_until AND coverage_from < coverage_until", name="ck_reference_dataset_dates"),
        sa.CheckConstraint("status IN ('draft','approved')", name="ck_reference_dataset_status"),
        sa.CheckConstraint("status <> 'approved' OR (approved_by IS NOT NULL AND approved_at IS NOT NULL AND approval_event_id IS NOT NULL)", name="ck_reference_dataset_approval"))
    op.create_index("ix_reference_dataset_versions_organization_id", "reference_dataset_versions", ["organization_id"])
    if op.get_bind().dialect.name == "postgresql":
        op.execute("""CREATE FUNCTION mcias_reference_dataset_guard() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          IF TG_OP = 'INSERT' AND NEW.status = 'approved' THEN
            RAISE EXCEPTION 'reference dataset must be reviewed after registration';
          END IF;
          IF TG_OP IN ('UPDATE', 'DELETE') AND OLD.status = 'approved' THEN
            RAISE EXCEPTION 'approved reference dataset immutable';
          END IF;
          IF TG_OP = 'UPDATE' AND NEW.status = 'approved' THEN
            IF NOT EXISTS (
              SELECT 1 FROM users u JOIN user_roles ur ON ur.user_id=u.id
              JOIN roles r ON r.id=ur.role_id
              JOIN role_permissions rp ON rp.role_id=r.id
              JOIN permissions p ON p.id=rp.permission_id
              WHERE u.id=NEW.approved_by AND u.active
                AND u.organization_id=NEW.organization_id AND r.code='super_admin'
                AND p.code='workspace.super_admin')
            OR NOT EXISTS (
              SELECT 1 FROM audit_log a WHERE a.id=NEW.approval_event_id
                AND a.actor_id=NEW.approved_by AND a.action='reference_dataset_approved'
                AND a.resource_type='reference_dataset_version' AND a.resource_id=NEW.id
                AND a.details->>'organization_id'=NEW.organization_id
                AND a.details->>'outcome'='success')
            THEN RAISE EXCEPTION 'reference dataset approval not authorized';
            END IF;
          END IF;
          IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
          RETURN NEW;
        END $$""")
        op.execute("""CREATE TRIGGER trg_reference_dataset_guard BEFORE INSERT OR UPDATE OR DELETE
            ON reference_dataset_versions FOR EACH ROW EXECUTE FUNCTION mcias_reference_dataset_guard()""")


def downgrade():
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS trg_reference_dataset_guard ON reference_dataset_versions")
        op.execute("DROP FUNCTION IF EXISTS mcias_reference_dataset_guard()")
    op.drop_index("ix_reference_dataset_versions_organization_id", table_name="reference_dataset_versions")
    op.drop_table("reference_dataset_versions")
