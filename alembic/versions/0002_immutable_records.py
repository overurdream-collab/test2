"""Database-enforced immutability for approved claims and audit log.

Revision ID: 0002_immutable
Revises: 0001_g1
"""
from alembic import op

revision = "0002_immutable"
down_revision = "0001_g1"
branch_labels = None
depends_on = None

def upgrade():
    op.execute("""
    CREATE FUNCTION mcias_claim_guard() RETURNS trigger
    LANGUAGE plpgsql AS $$
    BEGIN
      IF OLD.status = 'approved' THEN
        RAISE EXCEPTION 'approved claim cannot be modified';
      END IF;
      IF NEW.source_id IS DISTINCT FROM OLD.source_id
         OR NEW.original_payload IS DISTINCT FROM OLD.original_payload
         OR NEW.original_claimed_amount IS DISTINCT FROM OLD.original_claimed_amount
         OR NEW.currency IS DISTINCT FROM OLD.currency THEN
        RAISE EXCEPTION 'original claim values are immutable';
      END IF;
      RETURN NEW;
    END $$;
    """)
    op.execute("CREATE TRIGGER trg_mcias_claim_guard BEFORE UPDATE ON claims FOR EACH ROW EXECUTE FUNCTION mcias_claim_guard()")
    op.execute("""
    CREATE FUNCTION mcias_audit_guard() RETURNS trigger
    LANGUAGE plpgsql AS $$
    BEGIN
      RAISE EXCEPTION 'audit events are append-only';
    END $$;
    """)
    op.execute("CREATE TRIGGER trg_mcias_audit_guard BEFORE UPDATE OR DELETE ON audit_log FOR EACH ROW EXECUTE FUNCTION mcias_audit_guard()")

def downgrade():
    raise RuntimeError("Security guard downgrade forbidden; restore a validated backup instead.")
