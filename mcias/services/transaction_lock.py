"""Transaction-scoped serialization without UPDATE grants on immutable records."""
from sqlalchemy import text

def lock_record(db,namespace,organization_id,record_id):
    if db.get_bind().dialect.name=='postgresql':
        db.execute(text('SELECT pg_advisory_xact_lock(hashtextextended(:identity, 0))'),
            {'identity':f'mcias:{namespace}:{organization_id}:{record_id}'})
