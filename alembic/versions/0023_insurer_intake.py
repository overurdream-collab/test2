"""Add explicit insurer-contract intake; no organization grants or business data.

Revision ID: 0023_insurer_intake
Revises: 0022_rbac_authority
"""
from alembic import op
import sqlalchemy as sa

revision = "0023_insurer_intake"
down_revision = "0022_rbac_authority"
branch_labels = None
depends_on = None

FEATURE = {'code': 'inputs.insurers', 'category': 'inputs', 'parent_code': 'inputs',
    'name_ar': 'شركات التأمين وعقودها', 'name_en': 'Insurance companies and contracts',
    'is_container': False, 'display_order': 17, 'is_system': True}


def upgrade():
    op.execute(sa.text("""
        INSERT INTO feature_catalog
            (code, category, parent_code, name_ar, name_en, is_container, display_order, is_system)
        VALUES ('inputs.insurers', 'inputs', 'inputs', 'شركات التأمين وعقودها',
                'Insurance companies and contracts', false, 17, true)
    """))


def downgrade():
    # FK protection intentionally refuses removal if an organization has a grant.
    op.execute(sa.text("DELETE FROM feature_catalog WHERE code = 'inputs.insurers'"))
