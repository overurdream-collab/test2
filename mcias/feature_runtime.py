"""Permission provisioning only. Never seeds data, entitlements or memberships."""
import os,re
from sqlalchemy import create_engine,text
from sqlalchemy.engine import make_url

def setup(engine, runtime_user):
    if not re.fullmatch(r'[a-z][a-z0-9_]{0,62}',runtime_user):raise ValueError('invalid runtime role name')
    with engine.begin() as connection:
        if not connection.scalar(text('SELECT 1 FROM pg_roles WHERE rolname=:role'),{'role':runtime_user}):
            raise ValueError('runtime role does not exist')
        role=connection.dialect.identifier_preparer.quote_identifier(runtime_user)
        connection.exec_driver_sql(f'GRANT SELECT ON feature_catalog, organization_features TO {role}')
        connection.exec_driver_sql(f'GRANT INSERT ON organization_features TO {role}')
        for table in ('users','groups','group_permissions','user_groups','user_permissions','organization_features'):
            columns='status, effective_to, closed_by, closed_at, close_reason'+(', active' if table=='users' else '')
            connection.exec_driver_sql(f'GRANT UPDATE ({columns}) ON {table} TO {role}')
        connection.exec_driver_sql(f'GRANT UPDATE (name) ON organizations TO {role}')

def main():
    # Laptop setup receives the existing owner URL; production operators use SQL.
    if os.getenv('MCIAS_ENVIRONMENT')!='development' or os.getenv('MCIAS_LAPTOP_TEST_MODE')!='synthetic_localhost':
        raise ValueError('explicit synthetic laptop provisioning profile required')
    url=os.environ['MCIAS_E2E_DATABASE_URL'];parsed=make_url(url)
    if parsed.drivername!='postgresql+psycopg' or parsed.database!='mcias_laptop_e2e' or parsed.username!='laptop_owner':
        raise ValueError('isolated laptop owner database required')
    engine=create_engine(url)
    try:setup(engine,os.getenv('MCIAS_RUNTIME_USER','laptop_runtime'))
    finally:engine.dispose()
    print('RBAC and feature runtime column privileges configured; no data or feature grants created.')

if __name__=='__main__':main()
