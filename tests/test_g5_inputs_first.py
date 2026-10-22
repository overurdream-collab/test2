"""Real native G2/G3/G4/G5/Shared Audit on isolated synthetic PostgreSQL 16.

These fixtures do not invent the missing six-family completeness attestations.
A local tariff comparison may be proven while overall coverage stays unresolved.
"""
from datetime import date
from decimal import Decimal
from io import BytesIO
import hashlib
import hmac
import json
import os
from uuid import uuid4

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from openpyxl import Workbook
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from mcias.audit_agents import inspect_claim
from mcias.audit_engine import AuditPolicy, PolicyBlocked
from mcias.audit_service import fingerprint_policy, run_audit
from mcias.audit_authorization import verify_registered_policy
from mcias.claim_batches import approve_source_scope, attach, resume, stage
from mcias.ingestion.orchestrator import ingest
from mcias.models import (Base, AuditLog, Organization, Permission, Role, RolePermission,
                          SourceFile, User, UserRole, WrittenAuthorization)
from mcias.models_audit import AuditSnapshot
from mcias.models_audit_policy import AuditPolicyGrant
from mcias.models_claims import ClaimEntry
from mcias.models_ingestion import IngestionDocument
from mcias.models_reference import ContractVersion, ProviderTariff
from mcias.storage import EncryptedStore
from mcias.production_authorization import signed_payload, verify_production_approval

pytestmark = pytest.mark.skipif(not os.getenv("MCIAS_TEST_DATABASE_URL"), reason="isolated PG16 required")


def _workbook(amount="100", service_date="2026-06-01", duplicate=False):
    book=Workbook()
    sheet=book.active
    sheet.title="CLAIMS"
    sheet.append(["claim_reference","beneficiary_token","provider_code","service_code",
                  "service_date","claimed_amount","currency"])
    sheet.append(["SYN-CLAIM","SYN-BENEFICIARY","SYN-PROVIDER","SYN-SERVICE",service_date,amount,"USD"])
    if duplicate:
        sheet.append(["SYN-CLAIM","SYN-BENEFICIARY","SYN-PROVIDER","SYN-SERVICE",service_date,amount,"USD"])
    payment=book.create_sheet("PAYMENT")
    payment.append(["claim_reference","beneficiary_token","provider_code","service_code",
                    "service_date","claimed_amount","currency"])
    payment.append(["SYN-PAYMENT","SYN-BENEFICIARY","SYN-PROVIDER","SYN-SERVICE",service_date,"999","USD"])
    buf=BytesIO()
    book.save(buf)
    book.close()
    return buf.getvalue()


@pytest.fixture
def real_case(tmp_path,monkeypatch):
    url=os.environ["MCIAS_TEST_DATABASE_URL"]
    engine=create_engine(url)
    assert engine.dialect.name=="postgresql", "this suite requires actual PostgreSQL"
    with engine.connect() as conn:
        assert conn.scalar(text("SHOW server_version_num")) is not None
        assert 160000<=int(conn.scalar(text("SHOW server_version_num")))<170000
    # Each case owns an ephemeral schema; existing application databases and
    # migration state are not modified by this owner-specific integration suite.
    schema="g5_inputs_"+uuid4().hex
    with engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    isolated=engine.execution_options(schema_translate_map={None:schema})
    Base.metadata.create_all(isolated)
    key="synthetic-only-policy-key-"+"x"*32
    monkeypatch.setenv("MCIAS_G5_POLICY_VERIFICATION_KEY",key)
    store=EncryptedStore(str(tmp_path),b"g"*32)
    with Session(isolated,expire_on_commit=False) as db:
        org=Organization(name="SYN-G5-INPUTS")
        db.add(org);db.flush()
        users=[User(organization_id=org.id,username="SYN-"+uuid4().hex,password_hash="synthetic") for _ in range(3)]
        db.add_all(users);db.flush()
        actor,approver,reviewer=users
        for user,codes in ((actor,["claims.import"]),(approver,["policies.approve"]),(reviewer,["policies.review"])):
            role=Role(code="SYN-role-"+uuid4().hex)
            db.add(role);db.flush()
            db.add(UserRole(user_id=user.id,role_id=role.id))
            for code in codes:
                permission=Permission(code=code)
                db.add(permission);db.flush()
                db.add(RolePermission(role_id=role.id,permission_id=permission.id))
        policy=AuditPolicy(policy_id="SYN-POLICY-v1",currency="USD",rounding="HALF_UP",precision=2,
            order=("exclusion","tariff","cap","copay"),copay_percent=Decimal("20"),
            cap=Decimal("80"),exclusion=Decimal("0"),tariff=Decimal("100"),approved=True)
        fingerprint=fingerprint_policy(policy)
        message="|".join((org.id,fingerprint,approver.id,reviewer.id)).encode()
        db.add(AuditPolicyGrant(organization_id=org.id,policy_id=policy.policy_id,
            policy_fingerprint=fingerprint,approver_id=approver.id,reviewer_id=reviewer.id,
            signature=hmac.new(key.encode(),message,hashlib.sha256).hexdigest()))
        auth_bytes=b"SYN authorized provider SYN-PROVIDER/service SYN-SERVICE: v1 USD100 2026-01-01 to2026-07-01; v2 USD300 2026-07-01 to2027-01-01. Synthetic only."
        auth_key,auth_digest=store.put(auth_bytes)
        source=SourceFile(sha256=auth_digest,original_filename="SYN-authorization.txt",storage_key=auth_key)
        assert store.get(auth_key,auth_digest)==auth_bytes
        db.add(source);db.flush()
        from mcias.models import now_utc
        auth=WrittenAuthorization(organization_id=org.id,source_id=source.id,
            approved_by=approver.id,approved_at=now_utc())
        auth_v2=WrittenAuthorization(organization_id=org.id,source_id=source.id,
            approved_by=approver.id,approved_at=now_utc())
        db.add_all([auth,auth_v2]);db.flush()
        historical=ContractVersion(organization_id=org.id,provider_code="SYN-PROVIDER",version=1,
            effective_from=date(2026,1,1),effective_until=date(2026,7,1),status="approved",authorization_id=auth.id)
        newer=ContractVersion(organization_id=org.id,provider_code="SYN-PROVIDER",version=2,
            effective_from=date(2026,7,1),effective_until=date(2027,1,1),status="approved",authorization_id=auth_v2.id)
        db.add_all([historical,newer]);db.flush()
        db.add_all([ProviderTariff(contract_id=historical.id,service_code="SYN-SERVICE",amount=Decimal("100"),currency="USD"),
                    ProviderTariff(contract_id=newer.id,service_code="SYN-SERVICE",amount=Decimal("300"),currency="USD")])
        db.commit()
        private=Ed25519PrivateKey.generate()
        public=private.public_key().public_bytes(encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw)
        registry={"trusted_heads":{org.id:{approver.id:public.hex()}},"approvals":{}}
        for contract,approval in ((historical,auth),(newer,auth_v2)):
            registry["approvals"][approval.id]={"rule_id":contract.id,
                "authorization_id":approval.id,
                "signature":private.sign(signed_payload(contract,approval,source)).hex()}
        registry_path=tmp_path/"SYN-trusted-heads.json"
        registry_path.write_text(json.dumps(registry),encoding="utf-8")
        registry_path.chmod(0o600)
        monkeypatch.setenv("MCIAS_AUTHORIZATION_REGISTRY",str(registry_path))
        assert verify_production_approval(db,historical,auth)
        assert verify_production_approval(db,newer,auth_v2)

        def import_claims(**values):
            original=_workbook(**values)
            imported=ingest(db,store,org.id,actor.id,"SYN-claims.xlsx",original)
            assert imported["status"]=="extracted"
            document=db.get(IngestionDocument,imported["document_id"])
            original_source=db.get(SourceFile,document.source_id)
            assert store.get(original_source.storage_key,document.sha256)==original
            approve_source_scope(db,actor,imported["document_id"],{1:"CLAIMS",2:"PAYMENT"})
            batch=stage(db,actor,imported["document_id"])
            outcome=resume(db,actor,batch.id)
            assert outcome["status"]=="imported"
            claims=db.scalars(select(ClaimEntry).where(ClaimEntry.batch_id==batch.id)).all()
            assert all(c.claim_reference!="SYN-PAYMENT" for c in claims)
            attach(db,actor,claims[0].id,imported["document_id"])
            return claims
        yield db,actor,policy,import_claims,isolated,historical,newer
    with engine.begin() as conn:
        conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
    engine.dispose()


@pytest.mark.parametrize("amount,expected",[("100","VERIFIED_MATCH"),("120","PROVEN_VIOLATION")])
def test_native_tariff_match_or_violation_with_historical_reference(real_case,amount,expected):
    db,actor,policy,import_claims,engine,historical,newer=real_case
    claim=import_claims(amount=amount)[0]
    checks=inspect_claim(db,claim,policy,actor=actor)
    tariff=next(f for f in checks["findings"] if f["agent"]=="tariff")
    assert tariff["audit_state"]==expected
    assert checks["tariff"].contract_id==historical.id
    assert checks["tariff"].amount==Decimal("100")
    assert checks["audit_state"]=="UNRESOLVED_OR_MISSING_REFERENCE"
    assert checks["coverage"]["blocked"]>0
    assert checks["source_evidence"]["source_record_id"]==claim.extracted_record_id
    assert len(checks["reference_certificates"])==6


def test_conflicting_approved_policy_and_historical_tariff_remains_unresolved(real_case):
    db,actor,policy,import_claims,engine,historical,newer=real_case
    claim=import_claims(service_date="2026-09-01",amount="120")[0]
    checks=inspect_claim(db,claim,policy,actor=actor)
    tariff=next(f for f in checks["findings"] if f["agent"]=="tariff")
    assert checks["tariff"].contract_id==newer.id
    assert checks["tariff"].amount==Decimal("300")
    assert policy.tariff==Decimal("100")
    assert tariff["status"]=="hold"
    assert tariff["audit_state"]=="UNRESOLVED_OR_MISSING_REFERENCE"


def test_missing_beneficiary_caps_and_costsharing_never_become_violation(real_case):
    db,actor,policy,import_claims,*_=real_case
    claim=import_claims()[0]
    checks=inspect_claim(db,claim,policy,actor=actor)
    findings={f["agent"]:f for f in checks["findings"]}
    for agent in ("eligibility","contract","exclusion","caps","cost_sharing","duplicates"):
        assert findings[agent]["audit_state"]=="UNRESOLVED_OR_MISSING_REFERENCE"
        assert findings[agent]["status"]=="hold"
    assert checks["eligible"] is False
    assert checks["review_required"]


def test_duplicate_reference_is_review_signal_without_complete_history(real_case):
    db,actor,policy,import_claims,*_=real_case
    claims=import_claims(duplicate=True)
    checks=inspect_claim(db,claims[0],policy,actor=actor)
    duplicate=next(f for f in checks["findings"] if f["agent"]=="duplicates")
    assert duplicate["status"]=="review"
    assert duplicate["audit_state"]=="UNRESOLVED_OR_MISSING_REFERENCE"
    assert duplicate["reference"]==[claims[1].id]


def test_expired_tariff_is_unresolved_not_proven_mismatch(real_case):
    db,actor,policy,import_claims,*_=real_case
    claim=import_claims(service_date="2027-01-01",amount="999")[0]
    checks=inspect_claim(db,claim,policy,actor=actor)
    tariff=next(f for f in checks["findings"] if f["agent"]=="tariff")
    assert tariff["audit_state"]=="UNRESOLVED_OR_MISSING_REFERENCE"
    assert checks["contract"] is None


def test_source_contradiction_cannot_be_audited_or_become_tariff_violation(real_case):
    db,actor,policy,import_claims,*_=real_case
    claim=import_claims(amount="999")[0]
    # Simulate an inconsistent in-memory object without persisting an illegal
    # update to immutable G4 data; the consumer must reject caller-provided data.
    from sqlalchemy.orm import attributes
    attributes.set_committed_value(claim,"source_values",{"claimed_amount":"0"})
    checks=inspect_claim(db,claim,policy,actor=actor)
    assert checks["audit_state"]=="AUDIT_NOT_POSSIBLE"
    assert checks["source_evidence"] is None
    assert all(f["audit_state"]!="PROVEN_VIOLATION" for f in checks["findings"])


def test_actual_audit_commit_reopen_event_dedup_and_tenant_isolation(real_case):
    db,actor,policy,import_claims,engine,*_=real_case
    claim=import_claims(amount="120")[0]
    verified=verify_registered_policy(db,organization_id=actor.organization_id,
        policy_fingerprint=fingerprint_policy(policy))
    snapshot=run_audit(db,actor,claim.id,policy,verified_authorization=verified)
    snapshot_id,claim_id,org_id=snapshot.id,claim.id,actor.organization_id
    assert snapshot.findings["audit_state"]=="UNRESOLVED_OR_MISSING_REFERENCE"
    assert snapshot.calculation["status"]=="held"
    assert snapshot.calculation["payable"] is None and snapshot.calculation["deductions"]==[]
    repeated=run_audit(db,actor,claim.id,policy,verified_authorization=verified)
    assert repeated.id==snapshot_id
    db.commit()
    with Session(engine) as independent:
        saved=independent.get(AuditSnapshot,snapshot_id)
        assert saved.organization_id==org_id and saved.claim_id==claim_id
        events=independent.scalars(select(AuditLog).where(AuditLog.action=="claim_inputs_audited",
            AuditLog.resource_id==claim_id)).all()
        assert len(events)==1
        event=events[0]
        assert event.details["audit_snapshot_id"]==snapshot_id
        assert len(event.details["references"])==6
        serialized=str(event.details)
        assert "SYN-BENEFICIARY" not in serialized and "SYN-CLAIM" not in serialized
        assert "claimed_amount" not in serialized and "source_values" not in serialized
    # Tenant access is checked before the claim lookup can cross organizations;
    # a valid policy grant is organization-bound and cannot be reused elsewhere.
    from types import SimpleNamespace
    intruder=SimpleNamespace(active=True,organization_id=str(uuid4()),id=str(uuid4()))
    with pytest.raises(PolicyBlocked,match="invalid"):
        run_audit(db,intruder,claim_id,policy,verified_authorization=verified)
