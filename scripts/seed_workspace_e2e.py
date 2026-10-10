"""Create reproducible synthetic data only in an explicitly named *_e2e database.

No financial policy or approved decision is fabricated. All seeded claims are held.
The fixture is private to development/CI and does not provision a production admin.
"""
import json,os
from datetime import date
from decimal import Decimal
from pathlib import Path
from uuid import uuid4
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from mcias.models import Organization,User,Role,Permission,RolePermission,UserRole,SourceFile
from mcias.models_ingestion import IngestionDocument,IngestionJob,ExtractedSourceRecord
from mcias.models_claims import ClaimBatch,ClaimEntry
from mcias.reporting_g7 import create_snapshot
from mcias.security import hash_password

url=os.environ['MCIAS_E2E_DATABASE_URL']
assert make_url(url).database.endswith('_e2e'),'Only a dedicated *_e2e database may be seeded'
os.environ['MCIAS_TEST_DATABASE_URL']=url
config=Config('alembic.ini');config.set_main_option('sqlalchemy.url',url);command.upgrade(config,'head')
engine=create_engine(url);unique=uuid4().hex[:12]
with Session(engine,expire_on_commit=False) as db:
 org=Organization(name='SYNTHETIC E2E — not an institution');db.add(org);db.flush()
 actor=User(organization_id=org.id,username='workspace-e2e-'+unique,password_hash=hash_password('synthetic_e2e_password_only'))
 outsider=Organization(name='SYNTHETIC E2E foreign scope');db.add_all([actor,outsider]);db.flush()
 role=Role(code='workspace_e2e_'+unique);db.add(role);db.flush();db.add(UserRole(user_id=actor.id,role_id=role.id))
 for code in ['profile.read','claims.read','reports.read','reports.details.read']:
  permission=db.query(Permission).filter_by(code=code).first()
  if not permission:permission=Permission(code=code);db.add(permission);db.flush()
  db.add(RolePermission(role_id=role.id,permission_id=permission.id))
 source=SourceFile(sha256='a'*64,original_filename='synthetic.csv',storage_key='e2e-'+unique);db.add(source);db.flush()
 doc=IngestionDocument(organization_id=org.id,source_id=source.id,sha256=source.sha256,filename='synthetic.csv',status='extracted');db.add(doc);db.flush()
 job=IngestionJob(organization_id=org.id,document_id=doc.id,status='extracted',manifest={'complete':True});db.add(job);db.flush()
 batch=ClaimBatch(organization_id=org.id,ingestion_document_id=doc.id,created_by=actor.id,status='imported',source_sha256=source.sha256,record_count=12,imported_count=12);db.add(batch);db.flush()
 ids=[]
 for i in range(12):
  values={'claim_reference':'SYN-E2E-'+str(i+1),'claimed_amount':'1000.0000','diagnosis':'SYNTHETIC_PRIVATE_FIELD_NOT_DISCLOSED'}
  record=ExtractedSourceRecord(job_id=job.id,locator={'row':i+2},values=values);db.add(record);db.flush()
  claim=ClaimEntry(organization_id=org.id,batch_id=batch.id,extracted_record_id=record.id,source_locator=record.locator,source_values=values,claim_reference=values['claim_reference'],beneficiary_token='synthetic-only',provider_code='SYN-PROVIDER',service_code='SYN-SERVICE',service_date=date(2026,9,i+1),claimed_amount=Decimal('1000'),currency='LYD');db.add(claim);db.flush();ids.append(claim.id)
 db.commit();report=create_snapshot(db,actor,batch.id)
 manifest={'username':actor.username,'password':'synthetic_e2e_password_only','organization_id':org.id,'claim_ids':ids,'report_id':report.id,'batch_id':batch.id,'expected':report.summary}
 output=Path('.e2e-output/live-fixture.json');output.parent.mkdir(exist_ok=True);output.write_text(json.dumps(manifest,indent=2)+'\n')
 print('Synthetic fixture created in dedicated E2E database; all claims held.')
engine.dispose()
