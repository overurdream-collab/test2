"""Synthetic actual G2 encrypted CSV -> G4 -> typed A1 adapter / historical G3 tests.

No patient data, no paid model. SQLite is an integration smoke, not PostgreSQL
institutional acceptance. CI full PostgreSQL tests run independently.
"""
from datetime import date
from hashlib import sha256
from decimal import Decimal
from pathlib import Path
from io import BytesIO
from openpyxl import Workbook
from mcias.ingestion.parsers import excel_parser

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from mcias.models import (Base,Organization,User,Role,Permission,
                          UserRole,RolePermission,SourceFile)
from mcias.models_ingestion import IngestionDocument,IngestionJob,ExtractedSourceRecord
from mcias.models_claims import ClaimBatch,ClaimEntry,ClaimAttachment
from mcias.models_reference import ContractVersion,ProviderTariff
from mcias.storage import EncryptedStore
from mcias.ingestion.parsers import csv_parser
from mcias.ingestion.provenance import locator_dict
from mcias.agents.a1_trusted_input import (A1Input,A1AccessDenied,A1SourceBlocked,
    SCHEMA_VERSION, REQUIRED_SENSITIVE, REQUIRED_LINE, build_a1_snapshot,preview_a1_from_g4)

def _setup(tmp_path):
    engine=create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread":False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db=Session(engine,expire_on_commit=False)
    store=EncryptedStore(str(tmp_path/"stored"),b"\x07"*32)
    org=Organization(name="SYN-A1 tenant")
    actor=User(username="SYN-A1-auditor",password_hash="synthetic",active=True)
    db.add_all([org,actor]);db.flush()
    actor.organization_id=org.id
    role=Role(code="SYN-A1-readable")
    db.add(role);db.flush()
    db.add(UserRole(user_id=actor.id,role_id=role.id))
    for code in ("claims.read","ingestion.read",*REQUIRED_SENSITIVE):
        perm=Permission(code=code)
        db.add(perm);db.flush()
        db.add(RolePermission(role_id=role.id,permission_id=perm.id))
    db.commit()
    return engine,db,store,org,actor

def _document(db,store,org,filename,data):
    key,digest=store.put(data)
    source=SourceFile(sha256=digest,original_filename=filename,storage_key=key)
    db.add(source);db.flush()
    doc=IngestionDocument(organization_id=org.id,source_id=source.id,
                           sha256=digest,filename=filename,status="extracted")
    db.add(doc);db.flush()
    job=IngestionJob(organization_id=org.id,document_id=doc.id,status="extracted",
                     manifest={"complete":True})
    db.add(job);db.flush()
    rows=[]
    extraction=excel_parser.parse(data) if filename.lower().endswith(".xlsx") else csv_parser.parse(data)
    for raw in extraction.records:
        row=ExtractedSourceRecord(job_id=job.id,locator=locator_dict(raw.locator),
                                  values=raw.values,confidence=100)
        db.add(row);rows.append(row)
    db.commit()
    return doc, rows

def _claim(db,store,org,actor,provider="H1",service_date="2026-06-30",amount="20",
           claim_id="SYN-001",invoice=True):
    source=("claim_reference,beneficiary_token,provider_code,service_code,"
            "service_date,claimed_amount,currency\n"
            f"{claim_id},SYN-BEN,{provider},CONSULT,{service_date},{amount},YER\n").encode()
    doc,rows=_document(db,store,org,"claims.csv",source)
    batch=ClaimBatch(organization_id=org.id,ingestion_document_id=doc.id,
                     created_by=actor.id,status="imported",source_sha256=doc.sha256,
                     record_count=1,imported_count=1)
    db.add(batch);db.flush()
    claim=ClaimEntry(organization_id=org.id,batch_id=batch.id,
                     extracted_record_id=rows[0].id,source_locator=rows[0].locator,
                     source_values=rows[0].values,claim_reference=claim_id,
                     beneficiary_token="SYN-BEN",provider_code=provider,
                     service_code="CONSULT",service_date=date.fromisoformat(service_date),
                     claimed_amount=Decimal(amount),currency="YER")
    db.add(claim);db.flush()
    invoice_doc=None
    if invoice:
        inv=("line_item_id,service_code,unit,quantity,unit_price,line_total,"
             "invoice_total,claim_reference,provider_code,currency\n"
             f"SYN-L1,CONSULT,visit,2,10,20,20,{claim_id},{provider},YER\n").encode()
        invoice_doc,_=_document(db,store,org,"invoice.csv",inv)
        db.add(ClaimAttachment(organization_id=org.id,claim_id=claim.id,
                  ingestion_document_id=invoice_doc.id,document_sha256=invoice_doc.sha256,
                  linked_by=actor.id))
    db.commit()
    return claim,doc,invoice_doc

def _historical(db,org):
    for provider, version, start, end,price in [
        ("H1",1,"2026-01-01","2026-07-01","5000"),
        ("H1",2,"2026-07-01","2027-01-01","5500"),
        ("H2",1,"2026-01-01","2027-01-01","7000"),
    ]:
        contract=ContractVersion(organization_id=org.id,provider_code=provider,
                version=version,effective_from=date.fromisoformat(start),
                effective_until=date.fromisoformat(end),status="approved",precedence=0)
        db.add(contract);db.flush()
        db.add(ProviderTariff(contract_id=contract.id,service_code="CONSULT",
                              amount=Decimal(price),currency="YER"))
    db.commit()

def test_actual_encrypted_g2_g4_rows_and_Pydantic_positive(tmp_path):
    engine,db,store,org,actor=_setup(tmp_path)
    try:
        claim,_,invoice=_claim(db,store,org,actor)
        data=build_a1_snapshot(db,actor,claim.id,store,run_id="SYN-run")
        v=data["snapshot"]
        assert isinstance(v,A1Input)
        assert v.schema_version==SCHEMA_VERSION
        assert v.invoice.items[0].quantity=="2"
        assert len(v.source_verifications)==2
        assert all(s.original_sha256_verified and s.extracted_rows_equal_original
                   for s in v.source_verifications)
        assert data["g3_reference"]["status"]=="MISSING"
        out=preview_a1_from_g4(db,actor,claim.id,store,run_id="SYN-preview")
        assert out["a1"]["finding_status"]=="INSUFFICIENT_EVIDENCE"
        assert out["financial_decision"]=="NOT_AUTHORIZED"
        assert "approved_unit_mapping" in out["missing_evidence"]
        assert out["review_packet"]["provisional_four_way_code"]=="HUMAN_REVIEW"
        assert out["review_packet"]["g7_realized_savings"] is None
    finally:
        db.close();engine.dispose()

def test_g4_claim_without_invoice_does_not_create_unit_or_line(tmp_path):
    engine,db,store,org,actor=_setup(tmp_path)
    try:
        claim,_,_=_claim(db,store,org,actor,invoice=False)
        out=preview_a1_from_g4(db,actor,claim.id,store,run_id="SYN-no-invoice")
        assert out["a1"]["finding_status"]=="INSUFFICIENT_EVIDENCE"
        assert "no_unique_verified_itemized_invoice" in out["missing_evidence"]
        assert out["review_packet"]["provisional_four_way_code"]=="MISSING_ATTACHMENTS"
    finally:
        db.close();engine.dispose()

def test_altered_original_sha_chain_is_blocked(tmp_path):
    engine,db,store,org,actor=_setup(tmp_path)
    try:
        claim,doc,_=_claim(db,store,org,actor)
        doc.sha256="0"*64;db.commit()
        with pytest.raises(A1SourceBlocked,match="source_hash_chain_mismatch"):
            build_a1_snapshot(db,actor,claim.id,store,run_id="SYN-tampered")
    finally:
        db.close();engine.dispose()

def test_altered_g2_extraction_is_not_accepted(tmp_path):
    engine,db,store,org,actor=_setup(tmp_path)
    try:
        claim,_,invoice=_claim(db,store,org,actor)
        row=db.query(ExtractedSourceRecord).join(IngestionJob,
              ExtractedSourceRecord.job_id==IngestionJob.id).filter(
              IngestionJob.document_id==invoice.id).one()
        row.values={**row.values,"unit_price":"999"};db.commit()
        out=preview_a1_from_g4(db,actor,claim.id,store,run_id="SYN-tamper-extraction")
        assert "stored_extraction_not_equal_original" in out["missing_evidence"]
        assert out["a1"]["finding_status"]=="INSUFFICIENT_EVIDENCE"
    finally:
        db.close();engine.dispose()

def test_cross_tenant_and_missing_permissions_fail_before_source_read(tmp_path):
    engine,db,store,org,actor=_setup(tmp_path)
    try:
        claim,_,_=_claim(db,store,org,actor)
        other=Organization(name="SYN-other")
        outsider=User(username="SYN-outsider",password_hash="x",active=True)
        db.add_all([other,outsider]);db.flush()
        outsider.organization_id=other.id;db.commit()
        with pytest.raises(A1AccessDenied):
            build_a1_snapshot(db,outsider,claim.id,store,run_id="SYN-wrong-tenant")
        with pytest.raises(A1AccessDenied):
            build_a1_snapshot(db,actor,"SYN-missing-claim",store,run_id="SYN-other-claim")
    finally:
        db.close();engine.dispose()

def test_schema_rejects_nonfinite_floats_and_cross_tenant(tmp_path):
    engine,db,store,org,actor=_setup(tmp_path)
    try:
        claim,_,_=_claim(db,store,org,actor)
        result=build_a1_snapshot(db,actor,claim.id,store,run_id="SYN-valid").get("snapshot")
        payload=result.model_dump()
        payload["claim"]["amount"]="NaN"
        with pytest.raises(ValueError): A1Input.model_validate(payload)
        payload=result.model_dump()
        payload["invoice"]["tenant_id"]="SYN-other"
        with pytest.raises(ValueError): A1Input.model_validate(payload)
        payload=result.model_dump()
        payload["invoice"]["stated_total"]=float("inf")
        with pytest.raises(ValueError): A1Input.model_validate(payload)
    finally:
        db.close();engine.dispose()

def test_h1_h2_half_open_tariffs_but_no_invented_unit_authority(tmp_path):
    engine,db,store,org,actor=_setup(tmp_path)
    try:
        _historical(db,org)
        for provider,day,rate in [
            ("H1","2026-06-30","5000"),("H1","2026-07-01","5500"),
            ("H2","2026-07-01","7000")
        ]:
            claim,_,_=_claim(db,store,org,actor,provider=provider,
                             service_date=day,claim_id="SYN-"+provider+day,invoice=False)
            result=build_a1_snapshot(db,actor,claim.id,store,run_id="SYN-period")
            ref=result["g3_reference"]
            assert Decimal(ref["reference_amount"])==Decimal(rate)
            assert ref["status"]=="REFERENCE_ONLY_UNIT_UNPROVEN"
            assert result["snapshot"].contracts==[]
            assert "approved_unit_mapping" in result["snapshot"].missing_evidence
    finally:
        db.close();engine.dispose()


def test_actual_xlsx_invoice_matches_encrypted_original_with_sheet_row(tmp_path):
    engine,db,store,org,actor=_setup(tmp_path)
    try:
        claim,_,_=_claim(db,store,org,actor,invoice=False)
        book=Workbook()
        sheet=book.active
        sheet.append(list(REQUIRED_LINE))
        sheet.append(["SYN-L1","CONSULT","visit","2","10","20","20",
                      claim.claim_reference,"H1","YER"])
        buffer=BytesIO()
        book.save(buffer)
        book.close()
        doc,_=_document(db,store,org,"invoice.xlsx",buffer.getvalue())
        db.add(ClaimAttachment(organization_id=org.id,claim_id=claim.id,
                  ingestion_document_id=doc.id,document_sha256=doc.sha256,linked_by=actor.id))
        db.commit()
        result=build_a1_snapshot(db,actor,claim.id,store,run_id="SYN-xlsx")
        assert len(result["snapshot"].invoice.items)==1
        assert result["snapshot"].invoice.items[0].source.locator=="xlsx:sheet:1:row:2"
        assert len(result["snapshot"].source_verifications)==2
    finally:
        db.close();engine.dispose()


def test_g4_normalized_claim_amount_cannot_diverge_from_original_source(tmp_path):
    engine,db,store,org,actor=_setup(tmp_path)
    try:
        claim,_,_=_claim(db,store,org,actor)
        # Attacker-like direct SQL modification on an ephemeral synthetic SQLite
        # database deliberately bypasses the ORM guard to test A1 independence.
        db.execute(text("UPDATE claim_entries SET claimed_amount = :amount WHERE id = :id"),
                   {"amount": "999.0000", "id": claim.id})
        db.commit()
        db.expire_all()
        with pytest.raises(A1SourceBlocked,match="normalized_G4_claim_field_changed"):
            build_a1_snapshot(db,actor,claim.id,store,run_id="SYN-altered-claim")
    finally:
        db.close();engine.dispose()


def test_original_invoice_explicit_fee_kind_is_preserved_without_financial_authority(tmp_path):
    """Trusted G2 bytes, not code-name inference, determine whether a line is a fee."""
    engine,db,store,org,actor=_setup(tmp_path)
    try:
        claim,_,_=_claim(db,store,org,actor,invoice=False,amount="25")
        invoice_csv=(
            "line_item_id,service_code,unit,quantity,unit_price,line_total,"
            "invoice_total,claim_reference,provider_code,currency,item_kind\n"
            f"SYN-L1,CONSULT,visit,2,10,20,25,{claim.claim_reference},H1,YER,service\n"
            f"SYN-F1,ADMIN,fee,1,5,5,25,{claim.claim_reference},H1,YER,fee\n"
        ).encode()
        doc,_=_document(db,store,org,"mixed_invoice.csv",invoice_csv)
        db.add(ClaimAttachment(organization_id=org.id,claim_id=claim.id,
            ingestion_document_id=doc.id,document_sha256=doc.sha256,linked_by=actor.id))
        db.commit()
        result=build_a1_snapshot(db,actor,claim.id,store,run_id="SYN-explicit-fee")
        items=result["snapshot"].invoice.items
        assert [(item.code,item.kind) for item in items]==[
            ("CONSULT","service"),("ADMIN","fee")]
        assert len(result["snapshot"].source_verifications)==2
        preview=preview_a1_from_g4(db,actor,claim.id,store,run_id="SYN-fee-preview")
        assert preview["financial_decision"]=="NOT_AUTHORIZED"
        assert "approved_unit_mapping" in preview["missing_evidence"]
        assert "approved_contract_fee_clause" in preview["missing_evidence"]
        assert preview["review_packet"]["financial_decision_authorized"] is False
    finally:
        db.close();engine.dispose()


def test_invalid_declared_fee_kind_fails_closed_not_silently_service(tmp_path):
    engine,db,store,org,actor=_setup(tmp_path)
    try:
        claim,_,_=_claim(db,store,org,actor,invoice=False)
        csv=(
            "line_item_id,service_code,unit,quantity,unit_price,line_total,"
            "invoice_total,claim_reference,provider_code,currency,item_kind\n"
            f"SYN-L1,CONSULT,visit,2,10,20,20,{claim.claim_reference},H1,YER,discount\n"
        ).encode()
        doc,_=_document(db,store,org,"bad_kind.csv",csv)
        db.add(ClaimAttachment(organization_id=org.id,claim_id=claim.id,
            ingestion_document_id=doc.id,document_sha256=doc.sha256,linked_by=actor.id))
        db.commit()
        result=preview_a1_from_g4(db,actor,claim.id,store,run_id="SYN-invalid-kind")
        assert "invalid_invoice_row" in result["missing_evidence"]
        assert result["a1"]["finding_status"]=="INSUFFICIENT_EVIDENCE"
        assert result["financial_decision"]=="NOT_AUTHORIZED"
    finally:
        db.close();engine.dispose()


def test_legacy_service_only_invoice_does_not_invent_missing_fee_clause(tmp_path):
    engine,db,store,org,actor=_setup(tmp_path)
    try:
        claim,_,_=_claim(db,store,org,actor)
        preview=preview_a1_from_g4(db,actor,claim.id,store,run_id="SYN-service-only-fee-gate")
        assert "approved_contract_fee_clause" not in preview["missing_evidence"]
        assert preview["financial_decision"]=="NOT_AUTHORIZED"
    finally:
        db.close();engine.dispose()
