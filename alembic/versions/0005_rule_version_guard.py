"""Protect activated rule versions at the database boundary.

Revision ID: 0005_rule_guard
Revises: 0004_login
"""
from alembic import op

revision = "0005_rule_guard"
down_revision = "0004_login"
branch_labels = None
depends_on = None

def upgrade():
    op.execute("""
    CREATE FUNCTION mcias_active_rule_guard() RETURNS trigger
    LANGUAGE plpgsql AS $$
    BEGIN
      IF TG_OP = 'DELETE' THEN
        IF OLD.status = 'active' THEN
          RAISE EXCEPTION 'active rule version cannot be deleted';
        END IF;
        RETURN OLD;
      END IF;
      IF OLD.status = 'active' THEN
        RAISE EXCEPTION 'active rule version cannot be modified';
      END IF;
      RETURN NEW;
    END $$;
    """)
    op.execute("CREATE TRIGGER trg_mcias_active_rule_guard BEFORE UPDATE OR DELETE ON rule_versions FOR EACH ROW EXECUTE FUNCTION mcias_active_rule_guard()")

def downgrade():
    raise RuntimeError("Rule immutability guard downgrade forbidden; restore a validated backup instead.")
