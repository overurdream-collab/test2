"""G8 append-only analysis tasks and snapshots with PostgreSQL provenance guards."""
from alembic import op
import sqlalchemy as sa

revision = "0015_g8_intelligence"
down_revision = "0014_g7_reporting"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "g8_analysis_tasks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36),
                  sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("configuration", sa.JSON(), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("organization_id", "code", "version",
                            name="uq_g8_task_code_version"),
        sa.CheckConstraint("version > 0", name="ck_g8_task_positive_version"),
    )
    op.create_index("ix_g8_task_org", "g8_analysis_tasks", ["organization_id"])
    op.create_table(
        "g8_analysis_task_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36),
                  sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("task_id", sa.String(36),
                  sa.ForeignKey("g8_analysis_tasks.id"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("actor_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("task_id", "version", name="uq_g8_task_event_version"),
        sa.CheckConstraint("version > 0", name="ck_g8_event_positive_version"),
        sa.CheckConstraint("kind IN ('tested','activated','deactivated')",
                           name="ck_g8_event_kind"),
    )
    op.create_index("ix_g8_event_org", "g8_analysis_task_events", ["organization_id"])
    op.create_index("ix_g8_event_task", "g8_analysis_task_events", ["task_id"])
    op.create_table(
        "g8_analysis_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36),
                  sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("task_id", sa.String(36),
                  sa.ForeignKey("g8_analysis_tasks.id")),
        sa.Column("kind", sa.String(24), nullable=False),
        sa.Column("sources", sa.JSON(), nullable=False),
        sa.Column("parameters", sa.JSON(), nullable=False),
        sa.Column("result", sa.JSON(), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("kind IN ('summary','signals','simulation')",
                           name="ck_g8_run_kind"),
    )
    op.create_index("ix_g8_run_org", "g8_analysis_runs", ["organization_id"])
    op.create_index("ix_g8_run_task", "g8_analysis_runs", ["task_id"])

    op.execute("""
        CREATE FUNCTION mcias_g8_evidence_guard() RETURNS trigger AS $$
        DECLARE src jsonb;
        BEGIN
          IF TG_OP <> 'INSERT' THEN
            RAISE EXCEPTION 'G8 analysis evidence is immutable';
          END IF;
          IF NOT EXISTS (
            SELECT 1 FROM users u
            WHERE u.id = CASE WHEN TG_TABLE_NAME = 'g8_analysis_task_events'
                              THEN NEW.actor_id ELSE NEW.created_by END
              AND u.organization_id = NEW.organization_id AND u.active
          ) THEN
            RAISE EXCEPTION 'G8 analyst identity or organization mismatch';
          END IF;
          IF TG_TABLE_NAME = 'g8_analysis_task_events' THEN
            IF NOT EXISTS (
              SELECT 1 FROM g8_analysis_tasks t
              WHERE t.id=NEW.task_id AND t.organization_id=NEW.organization_id
            ) THEN
              RAISE EXCEPTION 'G8 task event organization mismatch';
            END IF;
          ELSIF TG_TABLE_NAME = 'g8_analysis_runs' THEN
            IF NEW.task_id IS NOT NULL AND NOT EXISTS (
              SELECT 1 FROM g8_analysis_tasks t
              WHERE t.id=NEW.task_id AND t.organization_id=NEW.organization_id
            ) THEN
              RAISE EXCEPTION 'G8 analysis task organization mismatch';
            END IF;
            IF jsonb_typeof(NEW.sources::jsonb) <> 'array'
               OR jsonb_array_length(NEW.sources::jsonb) < 1 THEN
              RAISE EXCEPTION 'G8 analysis requires frozen source report provenance';
            END IF;
            FOR src IN SELECT * FROM jsonb_array_elements(NEW.sources::jsonb) LOOP
              IF NOT EXISTS (
                SELECT 1 FROM report_snapshots r
                WHERE r.id=src->>'report_id'
                  AND r.organization_id=NEW.organization_id
                  AND r.fingerprint=src->>'fingerprint'
              ) THEN
                RAISE EXCEPTION 'G8 report source provenance mismatch';
              END IF;
            END LOOP;
          END IF;
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """)
    # Table-specific branches avoid referencing columns absent from other tables.
    op.execute("""
        CREATE FUNCTION mcias_g8_task_guard() RETURNS trigger AS $$
        BEGIN
          IF TG_OP <> 'INSERT' THEN
            RAISE EXCEPTION 'G8 task definitions are immutable';
          END IF;
          IF NOT EXISTS (SELECT 1 FROM users u WHERE u.id=NEW.created_by
            AND u.organization_id=NEW.organization_id AND u.active) THEN
            RAISE EXCEPTION 'G8 task owner mismatch';
          END IF;
          RETURN NEW;
        END; $$ LANGUAGE plpgsql
    """)
    op.execute("""CREATE TRIGGER trg_g8_task_immutable
        BEFORE INSERT OR UPDATE OR DELETE ON g8_analysis_tasks
        FOR EACH ROW EXECUTE FUNCTION mcias_g8_task_guard()""")
    op.execute("""
        CREATE FUNCTION mcias_g8_event_guard() RETURNS trigger AS $$
        BEGIN
          IF TG_OP <> 'INSERT' THEN
            RAISE EXCEPTION 'G8 lifecycle evidence is immutable';
          END IF;
          IF NOT EXISTS (
            SELECT 1 FROM g8_analysis_tasks t JOIN users u ON u.id=NEW.actor_id
            WHERE t.id=NEW.task_id AND t.organization_id=NEW.organization_id
              AND u.organization_id=NEW.organization_id AND u.active
          ) THEN RAISE EXCEPTION 'G8 event organization mismatch'; END IF;
          RETURN NEW;
        END; $$ LANGUAGE plpgsql
    """)
    op.execute("""CREATE TRIGGER trg_g8_event_immutable
        BEFORE INSERT OR UPDATE OR DELETE ON g8_analysis_task_events
        FOR EACH ROW EXECUTE FUNCTION mcias_g8_event_guard()""")
    op.execute("""
        CREATE FUNCTION mcias_g8_run_guard() RETURNS trigger AS $$
        DECLARE src jsonb;
        BEGIN
          IF TG_OP <> 'INSERT' THEN RAISE EXCEPTION 'G8 analysis results are immutable'; END IF;
          IF NOT EXISTS (SELECT 1 FROM users u WHERE u.id=NEW.created_by
              AND u.organization_id=NEW.organization_id AND u.active) THEN
            RAISE EXCEPTION 'G8 analyst organization mismatch';
          END IF;
          IF NEW.task_id IS NOT NULL AND NOT EXISTS (
             SELECT 1 FROM g8_analysis_tasks t WHERE t.id=NEW.task_id
               AND t.organization_id=NEW.organization_id
          ) THEN RAISE EXCEPTION 'G8 task organization mismatch'; END IF;
          IF jsonb_typeof(NEW.sources::jsonb) <> 'array'
             OR jsonb_array_length(NEW.sources::jsonb) < 1 THEN
            RAISE EXCEPTION 'G8 report sources missing';
          END IF;
          FOR src IN SELECT * FROM jsonb_array_elements(NEW.sources::jsonb) LOOP
            IF NOT EXISTS (SELECT 1 FROM report_snapshots r
                WHERE r.id=src->>'report_id' AND r.organization_id=NEW.organization_id
                  AND r.fingerprint=src->>'fingerprint') THEN
              RAISE EXCEPTION 'G8 frozen source mismatch';
            END IF;
          END LOOP;
          RETURN NEW;
        END; $$ LANGUAGE plpgsql
    """)
    op.execute("""CREATE TRIGGER trg_g8_run_immutable
        BEFORE INSERT OR UPDATE OR DELETE ON g8_analysis_runs
        FOR EACH ROW EXECUTE FUNCTION mcias_g8_run_guard()""")

def downgrade():
    raise RuntimeError("immutable G8 analysis evidence cannot be dropped; use verified backup")
