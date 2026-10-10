"""Measured tenant-scoped claim filters; preserve existing governance UNIQUE index."""
from alembic import op
revision = "0018_claim_query_indexes"
down_revision = "0017_operational_limits"
branch_labels = depends_on = None
INDEXES = {
    "ix_claim_org_service_date": ["organization_id", "service_date"],
    "ix_claim_org_provider_code": ["organization_id", "provider_code"],
    "ix_claim_org_beneficiary_token": ["organization_id", "beneficiary_token"],
}

def upgrade():
    for name, columns in INDEXES.items():
        op.create_index(name, "claim_entries", columns)

def downgrade():
    for name in reversed(INDEXES):
        op.drop_index(name, table_name="claim_entries")
