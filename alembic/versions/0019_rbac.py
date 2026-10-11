"""RBAC foundation — groups, permissions, temporal user lifecycle.

Revision ID: 0019_rbac
Revises: 0018_claim_query_indexes
Create Date: 2026-10-12
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP

revision = "0019_rbac"
down_revision = "0018_claim_query_indexes"
branch_labels = None
depends_on = None


def upgrade():
    # ============================================================
    # 1) توسيع جدول users
    # ============================================================
    op.add_column("users", sa.Column("status", sa.String(20), nullable=False, server_default="open"))
    op.add_column("users", sa.Column("effective_from", sa.Date, nullable=True))
    op.add_column("users", sa.Column("effective_to", sa.Date, nullable=True))
    op.add_column("users", sa.Column("version", sa.Integer, nullable=False, server_default="1"))
    op.add_column("users", sa.Column("is_super_admin", sa.Boolean, nullable=False, server_default=sa.text("false")))
    op.add_column("users", sa.Column("closed_by", sa.String(36), nullable=True))
    op.add_column("users", sa.Column("closed_at", TIMESTAMP(timezone=True), nullable=True))
    op.add_column("users", sa.Column("close_reason", sa.Text, nullable=True))
    op.add_column("users", sa.Column("full_name_ar", sa.String(200), nullable=True))
    op.add_column("users", sa.Column("full_name_en", sa.String(200), nullable=True))
    op.add_column("users", sa.Column("email", sa.String(200), nullable=True))
    op.add_column("users", sa.Column("last_login_at", TIMESTAMP(timezone=True), nullable=True))

    op.execute("UPDATE users SET effective_from = created_at::date WHERE effective_from IS NULL")
    op.alter_column("users", "effective_from", nullable=False)

    op.create_index("ix_users_status", "users", ["status"])
    op.create_index("ix_users_org_status", "users", ["organization_id", "status"])
    op.create_index(
        "ix_users_super",
        "users",
        ["is_super_admin"],
        postgresql_where=sa.text("is_super_admin = true"),
    )

    op.create_check_constraint("ck_users_status", "users", "status IN ('open', 'closed')")
    op.create_check_constraint(
        "ck_users_dates",
        "users",
        "(status = 'open' AND effective_to IS NULL) OR (status = 'closed' AND effective_to IS NOT NULL)",
    )

    # ============================================================
    # 2) توسيع جدول permissions
    # ============================================================
    op.add_column("permissions", sa.Column("category", sa.String(80), nullable=True))
    op.add_column("permissions", sa.Column("description_ar", sa.String(300), nullable=True))
    op.add_column("permissions", sa.Column("description_en", sa.String(300), nullable=True))
    op.add_column(
        "permissions",
        sa.Column("is_system", sa.Boolean, nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "permissions",
        sa.Column(
            "created_at",
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_index("ix_permissions_category", "permissions", ["category"])

    # ============================================================
    # 3) جدول groups
    # ============================================================
    op.create_table(
        "groups",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("code", sa.String(80), nullable=False),
        sa.Column("name_ar", sa.String(200), nullable=False),
        sa.Column("name_en", sa.String(200), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("is_system", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("effective_from", sa.Date, nullable=False),
        sa.Column("effective_to", sa.Date, nullable=True),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("created_by", sa.String(36), nullable=False),
        sa.Column(
            "created_at",
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("closed_by", sa.String(36), nullable=True),
        sa.Column("closed_at", TIMESTAMP(timezone=True), nullable=True),
        sa.Column("close_reason", sa.Text, nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["closed_by"], ["users.id"]),
        sa.UniqueConstraint("organization_id", "code", "effective_from", name="uq_groups_org_code_from"),
        sa.CheckConstraint("status IN ('open', 'closed')", name="ck_groups_status"),
        sa.CheckConstraint(
            "(status = 'open' AND effective_to IS NULL) OR (status = 'closed' AND effective_to IS NOT NULL)",
            name="ck_groups_dates",
        ),
    )
    op.create_index("ix_groups_org", "groups", ["organization_id"])
    op.create_index("ix_groups_status", "groups", ["status"])

    # ============================================================
    # 4) جدول group_permissions
    # ============================================================
    op.create_table(
        "group_permissions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("group_id", sa.String(36), nullable=False),
        sa.Column("permission_id", sa.String(36), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("effective_from", sa.Date, nullable=False),
        sa.Column("effective_to", sa.Date, nullable=True),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("granted_by", sa.String(36), nullable=False),
        sa.Column(
            "created_at",
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("closed_by", sa.String(36), nullable=True),
        sa.Column("closed_at", TIMESTAMP(timezone=True), nullable=True),
        sa.Column("close_reason", sa.Text, nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"]),
        sa.ForeignKeyConstraint(["permission_id"], ["permissions.id"]),
        sa.ForeignKeyConstraint(["granted_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["closed_by"], ["users.id"]),
        sa.CheckConstraint("status IN ('open', 'closed')", name="ck_group_perms_status"),
    )
    op.create_index("ix_group_perms_group", "group_permissions", ["group_id", "status"])
    op.create_index("ix_group_perms_perm", "group_permissions", ["permission_id"])
    op.create_index("ix_group_perms_org", "group_permissions", ["organization_id"])

    op.execute("""
        ALTER TABLE group_permissions
        ADD CONSTRAINT ex_group_perms_unique_open
        EXCLUDE USING gist (
            group_id WITH =,
            permission_id WITH =,
            daterange(effective_from, COALESCE(effective_to, 'infinity'::date), '[)') WITH &&
        ) WHERE (status = 'open')
    """)

    # ============================================================
    # 5) جدول user_groups
    # ============================================================
    op.create_table(
        "user_groups",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("group_id", sa.String(36), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("effective_from", sa.Date, nullable=False),
        sa.Column("effective_to", sa.Date, nullable=True),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("added_by", sa.String(36), nullable=False),
        sa.Column(
            "created_at",
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("closed_by", sa.String(36), nullable=True),
        sa.Column("closed_at", TIMESTAMP(timezone=True), nullable=True),
        sa.Column("close_reason", sa.Text, nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"]),
        sa.ForeignKeyConstraint(["added_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["closed_by"], ["users.id"]),
        sa.CheckConstraint("status IN ('open', 'closed')", name="ck_user_groups_status"),
    )
    op.create_index("ix_user_groups_user", "user_groups", ["user_id", "status"])
    op.create_index("ix_user_groups_group", "user_groups", ["group_id", "status"])
    op.create_index("ix_user_groups_org", "user_groups", ["organization_id"])

    op.execute("""
        ALTER TABLE user_groups
        ADD CONSTRAINT ex_user_groups_unique_open
        EXCLUDE USING gist (
            user_id WITH =,
            group_id WITH =,
            daterange(effective_from, COALESCE(effective_to, 'infinity'::date), '[)') WITH &&
        ) WHERE (status = 'open')
    """)

    # ============================================================
    # 6) جدول user_permissions
    # ============================================================
    op.create_table(
        "user_permissions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("permission_id", sa.String(36), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("effective_from", sa.Date, nullable=False),
        sa.Column("effective_to", sa.Date, nullable=True),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("granted_by", sa.String(36), nullable=False),
        sa.Column(
            "created_at",
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("closed_by", sa.String(36), nullable=True),
        sa.Column("closed_at", TIMESTAMP(timezone=True), nullable=True),
        sa.Column("close_reason", sa.Text, nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["permission_id"], ["permissions.id"]),
        sa.ForeignKeyConstraint(["granted_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["closed_by"], ["users.id"]),
        sa.CheckConstraint("status IN ('open', 'closed')", name="ck_user_perms_status"),
    )
    op.create_index("ix_user_perms_user", "user_permissions", ["user_id", "status"])
    op.create_index("ix_user_perms_org", "user_permissions", ["organization_id"])

    op.execute("""
        ALTER TABLE user_permissions
        ADD CONSTRAINT ex_user_perms_unique_open
        EXCLUDE USING gist (
            user_id WITH =,
            permission_id WITH =,
            daterange(effective_from, COALESCE(effective_to, 'infinity'::date), '[)') WITH &&
        ) WHERE (status = 'open')
    """)

    # ============================================================
    # 7) تعديل جدول audit_log
    # ============================================================
    op.add_column("audit_log", sa.Column("organization_id", sa.String(36), nullable=True))
    op.add_column("audit_log", sa.Column("actor_username", sa.String(120), nullable=True))
    op.add_column("audit_log", sa.Column("actor_ip", sa.String(45), nullable=True))
    op.add_column("audit_log", sa.Column("actor_user_agent", sa.Text, nullable=True))
    op.add_column("audit_log", sa.Column("session_id", sa.String(36), nullable=True))
    op.add_column("audit_log", sa.Column("category", sa.String(80), nullable=True))
    op.add_column(
        "audit_log",
        sa.Column("severity", sa.String(20), nullable=True, server_default="info"),
    )
    op.add_column("audit_log", sa.Column("resource_snapshot", JSONB, nullable=True))
    op.add_column("audit_log", sa.Column("before_state", JSONB, nullable=True))
    op.add_column("audit_log", sa.Column("after_state", JSONB, nullable=True))
    op.add_column("audit_log", sa.Column("request_id", sa.String(36), nullable=True))
    op.add_column("audit_log", sa.Column("trace_id", sa.String(36), nullable=True))
    op.add_column("audit_log", sa.Column("endpoint", sa.String(250), nullable=True))
    op.add_column("audit_log", sa.Column("method", sa.String(10), nullable=True))
    op.add_column(
        "audit_log",
        sa.Column("result", sa.String(20), nullable=True, server_default="success"),
    )
    op.add_column("audit_log", sa.Column("error_message", sa.Text, nullable=True))
    op.add_column("audit_log", sa.Column("error_code", sa.String(50), nullable=True))
    op.add_column("audit_log", sa.Column("hash", sa.String(64), nullable=True))
    op.add_column("audit_log", sa.Column("previous_hash", sa.String(64), nullable=True))

    op.create_index("ix_audit_actor_ts", "audit_log", ["actor_id", sa.text("created_at DESC")])
    op.create_index(
        "ix_audit_resource_ts",
        "audit_log",
        ["resource_type", "resource_id", sa.text("created_at DESC")],
    )
    op.create_index("ix_audit_action_ts", "audit_log", ["action", sa.text("created_at DESC")])
    op.create_index("ix_audit_category_ts", "audit_log", ["category", sa.text("created_at DESC")])
    op.create_index("ix_audit_result_ts", "audit_log", ["result", sa.text("created_at DESC")])
    op.create_index(
        "ix_audit_org_ts",
        "audit_log",
        ["organization_id", sa.text("created_at DESC")],
    )
    op.create_index("ix_audit_request", "audit_log", ["request_id"])

    op.create_check_constraint(
        "ck_audit_severity",
        "audit_log",
        "severity IS NULL OR severity IN ('info', 'warning', 'error', 'critical')",
    )
    op.create_check_constraint(
        "ck_audit_result",
        "audit_log",
        "result IS NULL OR result IN ('success', 'failure', 'denied')",
    )

    # ============================================================
    # 8) Triggers
    # ============================================================
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.execute("""
        CREATE OR REPLACE FUNCTION mcias_prevent_delete()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'Deletion is forbidden. Close record with date instead.';
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        CREATE OR REPLACE FUNCTION mcias_check_close()
        RETURNS TRIGGER AS $$
        BEGIN
            IF OLD.status = 'open' AND NEW.status = 'closed' THEN
                IF NEW.effective_to IS NULL THEN
                    RAISE EXCEPTION 'Closed record must have effective_to.';
                END IF;
                IF NEW.effective_to < OLD.effective_from THEN
                    RAISE EXCEPTION 'effective_to cannot be before effective_from.';
                END IF;
                NEW.closed_at := COALESCE(NEW.closed_at, now());
                NEW.version := OLD.version;
            END IF;

            IF OLD.status = 'closed' AND NEW.status = 'open' THEN
                RAISE EXCEPTION 'Cannot reopen closed record. Create a new record instead.';
            END IF;

            IF OLD.status = 'closed' THEN
                RAISE EXCEPTION 'Closed records are immutable.';
            END IF;

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    for table in [
        "groups",
        "group_permissions",
        "user_groups",
        "user_permissions",
    ]:
        op.execute(f"""
            CREATE TRIGGER trg_prevent_delete_{table}
            BEFORE DELETE ON {table}
            FOR EACH ROW EXECUTE FUNCTION mcias_prevent_delete();
        """)
        op.execute(f"""
            CREATE TRIGGER trg_check_close_{table}
            BEFORE UPDATE ON {table}
            FOR EACH ROW EXECUTE FUNCTION mcias_check_close();
        """)

    op.execute("""
        CREATE TRIGGER trg_prevent_delete_users
        BEFORE DELETE ON users
        FOR EACH ROW EXECUTE FUNCTION mcias_prevent_delete();
    """)
    op.execute("""
        CREATE TRIGGER trg_check_close_users
        BEFORE UPDATE ON users
        FOR EACH ROW EXECUTE FUNCTION mcias_check_close();
    """)

    op.execute("""
        CREATE OR REPLACE FUNCTION mcias_prevent_audit_update()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'Audit log is append-only. No updates allowed.';
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE OR REPLACE FUNCTION mcias_prevent_audit_delete()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'Audit log is append-only. No deletes allowed.';
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER trg_prevent_audit_update
        BEFORE UPDATE ON audit_log
        FOR EACH ROW EXECUTE FUNCTION mcias_prevent_audit_update();
    """)
    op.execute("""
        CREATE TRIGGER trg_prevent_audit_delete
        BEFORE DELETE ON audit_log
        FOR EACH ROW EXECUTE FUNCTION mcias_prevent_audit_delete();
    """)

    op.execute("""
        CREATE OR REPLACE FUNCTION mcias_compute_audit_hash()
        RETURNS TRIGGER AS $$
        DECLARE
            prev_hash VARCHAR(64);
            content TEXT;
        BEGIN
            SELECT hash INTO prev_hash
            FROM audit_log
            WHERE hash IS NOT NULL
            ORDER BY created_at DESC
            LIMIT 1;

            NEW.previous_hash := prev_hash;

            content := COALESCE(NEW.id, '') || '|' ||
                       COALESCE(NEW.actor_id, '') || '|' ||
                       COALESCE(NEW.action, '') || '|' ||
                       COALESCE(NEW.resource_type, '') || '|' ||
                       COALESCE(NEW.resource_id, '') || '|' ||
                       COALESCE(NEW.result, '') || '|' ||
                       NEW.created_at::text || '|' ||
                       COALESCE(prev_hash, '');

            NEW.hash := encode(digest(content, 'sha256'), 'hex');

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        CREATE TRIGGER trg_compute_audit_hash
        BEFORE INSERT ON audit_log
        FOR EACH ROW EXECUTE FUNCTION mcias_compute_audit_hash();
    """)

    # ============================================================
    # 9) الفئات الافتراضية (لكل جهة موجودة)
    # ============================================================
    op.execute("""
        INSERT INTO groups (
            id, organization_id, code, name_ar, name_en,
            is_system, status, effective_from, created_by
        )
        SELECT
            gen_random_uuid()::text,
            o.id,
            g.code,
            g.name_ar,
            g.name_en,
            true,
            'open',
            CURRENT_DATE,
            (SELECT id FROM users WHERE is_super_admin = true LIMIT 1)
        FROM organizations o
        CROSS JOIN (VALUES
            ('admin',              'مدير الجهة',       'Entity Admin'),
            ('reference_manager',  'مدير المراجع',     'Reference Manager'),
            ('ingestion_operator', 'مشغل الاستيعاب',   'Ingestion Operator'),
            ('claims_reviewer',    'مراجع المطالبات',  'Claims Reviewer'),
            ('claims_approver',    'معتمد المطالبات',  'Claims Approver'),
            ('auditor',            'مدقق',             'Auditor'),
            ('reporter',           'معد التقارير',     'Reporter'),
            ('viewer',             'مشاهد',            'Viewer')
        ) AS g(code, name_ar, name_en)
    """)


def downgrade():
    for table in ["groups", "group_permissions", "user_groups", "user_permissions", "users"]:
        op.execute(f"DROP TRIGGER IF EXISTS trg_prevent_delete_{table} ON {table}")
        op.execute(f"DROP TRIGGER IF EXISTS trg_check_close_{table} ON {table}")
    op.execute("DROP TRIGGER IF EXISTS trg_prevent_audit_update ON audit_log")
    op.execute("DROP TRIGGER IF EXISTS trg_prevent_audit_delete ON audit_log")
    op.execute("DROP TRIGGER IF EXISTS trg_compute_audit_hash ON audit_log")

    op.execute("DROP FUNCTION IF EXISTS mcias_prevent_delete()")
    op.execute("DROP FUNCTION IF EXISTS mcias_check_close()")
    op.execute("DROP FUNCTION IF EXISTS mcias_prevent_audit_update()")
    op.execute("DROP FUNCTION IF EXISTS mcias_prevent_audit_delete()")
    op.execute("DROP FUNCTION IF EXISTS mcias_compute_audit_hash()")

    op.drop_table("user_permissions")
    op.drop_table("user_groups")
    op.drop_table("group_permissions")
    op.drop_table("groups")

    for col in [
        "organization_id", "actor_username", "actor_ip", "actor_user_agent",
        "session_id", "category", "severity", "resource_snapshot",
        "before_state", "after_state", "request_id", "trace_id",
        "endpoint", "method", "result", "error_message", "error_code",
        "hash", "previous_hash",
    ]:
        op.drop_column("audit_log", col)

    for col in ["category", "description_ar", "description_en", "is_system", "created_at"]:
        op.drop_column("permissions", col)

    for col in [
        "status", "effective_from", "effective_to", "version",
        "is_super_admin", "closed_by", "closed_at", "close_reason",
        "full_name_ar", "full_name_en", "email", "last_login_at",
    ]:
        op.drop_column("users", col)
