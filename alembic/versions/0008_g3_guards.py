"""PostgreSQL race-proof temporal exclusion constraints and reference immutability.

Revision ID: 0008_g3_guards
Revises: 0007_reference
"""
from alembic import op
revision = "0008_g3_guards"
down_revision = "0007_reference"
branch_labels = None
depends_on = None

def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
    op.execute("""
        ALTER TABLE contract_versions ADD CONSTRAINT ex_g3_approved_contract_period
        EXCLUDE USING gist (
          organization_id WITH =,
          provider_code WITH =,
          daterange(effective_from, effective_until, '[)') WITH &&
        ) WHERE (status = 'approved')
    """)
    op.execute("""
        ALTER TABLE beneficiary_enrollments ADD CONSTRAINT ex_g3_beneficiary_period
        EXCLUDE USING gist (
          organization_id WITH =,
          beneficiary_token WITH =,
          daterange(effective_from, effective_until, '[)') WITH &&
        )
    """)
    op.execute("""
        CREATE FUNCTION mcias_g3_guard_contract() RETURNS trigger AS $$
        BEGIN
          IF TG_OP = 'DELETE' THEN
            IF OLD.status = 'approved' THEN
              RAISE EXCEPTION 'approved contract immutable';
            END IF;
            RETURN OLD;
          END IF;
          IF OLD.status = 'approved' THEN
            RAISE EXCEPTION 'approved contract immutable';
          END IF;
          IF NEW.status = 'approved' AND OLD.status <> 'draft' THEN
            RAISE EXCEPTION 'invalid contract transition';
          END IF;
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """)
    op.execute("""
        CREATE TRIGGER trg_g3_contract_guard BEFORE UPDATE OR DELETE ON contract_versions
        FOR EACH ROW EXECUTE FUNCTION mcias_g3_guard_contract()
    """)
    op.execute("""
        CREATE FUNCTION mcias_g3_guard_tariff() RETURNS trigger AS $$
        BEGIN
          IF TG_OP = 'DELETE' THEN
            IF EXISTS (SELECT 1 FROM contract_versions WHERE id = OLD.contract_id AND status = 'approved') THEN
              RAISE EXCEPTION 'approved tariff immutable';
            END IF;
            RETURN OLD;
          END IF;
          IF EXISTS (SELECT 1 FROM contract_versions WHERE id = OLD.contract_id AND status = 'approved')
             OR EXISTS (SELECT 1 FROM contract_versions WHERE id = NEW.contract_id AND status = 'approved') THEN
            RAISE EXCEPTION 'approved tariff immutable';
          END IF;
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """)
    op.execute("""
        CREATE TRIGGER trg_g3_tariff_guard BEFORE UPDATE OR DELETE ON provider_tariffs
        FOR EACH ROW EXECUTE FUNCTION mcias_g3_guard_tariff()
    """)
    op.execute("""
        CREATE FUNCTION mcias_g3_guard_enrollment() RETURNS trigger AS $$
        BEGIN
          IF NOT EXISTS (
            SELECT 1 FROM beneficiary_categories
            WHERE id = NEW.category_id AND organization_id = NEW.organization_id
          ) THEN
            RAISE EXCEPTION 'cross-tenant beneficiary category';
          END IF;
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """)
    op.execute("""
        CREATE TRIGGER trg_g3_enrollment_guard BEFORE INSERT OR UPDATE ON beneficiary_enrollments
        FOR EACH ROW EXECUTE FUNCTION mcias_g3_guard_enrollment()
    """)

def downgrade():
    raise RuntimeError("G3 approved reference history downgrade forbidden; restore verified backup.")
