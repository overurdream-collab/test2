#!/usr/bin/env python3
"""Standalone negative probe of real pinned A1 trusted-source gate on synthetic PDF."""
import os, tempfile
from pathlib import Path
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from mcias.models import Base, Organization, User
from mcias.storage import EncryptedStore
from mcias.ingestion.orchestrator import ingest
from mcias.agents.a1_trusted_input import SourceVerification, A1SourceBlocked, _verify_csv_source

def main(pdf_path):
    for verified_original, verified_rows in [(False,False),(True,False),(False,True)]:
        try:
            SourceVerification.model_validate({
                "document_id":"synthetic","sha256":"a"*64,
                "original_sha256_verified":verified_original,
                "extracted_rows_equal_original":verified_rows})
        except ValidationError:
            pass
        else:
            raise AssertionError("false OCR qualification entered trusted A1 model")
    os.environ["MCIAS_ENVIRONMENT"]="development"
    os.environ["MCIAS_LOCAL_OCR"]="disabled"
    os.environ["MCIAS_MALWARE_SCAN"]="disabled"
    engine=create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with tempfile.TemporaryDirectory() as root, Session(engine) as db:
        store=EncryptedStore(root,os.urandom(32))
        org=Organization(name="synthetic A1 source")
        actor=User(username="isolated_contract_probe",password_hash="test-only")
        db.add_all([org,actor]);db.flush();actor.organization_id=org.id;db.commit()
        pdf=Path(pdf_path).read_bytes()
        result=ingest(db,store,org.id,actor.id,"synthetic.pdf",pdf)
        assert result["status"]=="review_required",result
        try:
            _verify_csv_source(db,store,org.id,result["document_id"],result["sha256"])
        except A1SourceBlocked as exc:
            assert "unavailable_untrusted_tenant_source" in str(exc),str(exc)
        else:raise AssertionError("A1 trusted adapter accepted scanned PDF")
    engine.dispose()
    print("PINNED_A1_TRUSTED_PDF_REJECTION_PASSED")

if __name__=="__main__":
    import sys
    main(sys.argv[1])
