"""PostgreSQL enforced append-only contract AI proposal/review/promotion history.

SYN-only; verifies raw SQL bypass cannot rewrite approval provenance.
"""
import os
from datetime import date
from hashlib import sha256
from uuid import uuid4
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from mcias.models import Organization, User, SourceFile
from mcias.models_ingestion import IngestionDocument, IngestionJob
from mcias.models_reference_points import ReferencePoint
from mcias.models_contract_proposals import ContractProposal, ContractProposalReview, ContractProposalPromotion

@pytest.mark.skipif(not os.getenv("MCIAS_TEST_DATABASE_URL"),
                    reason="isolated PostgreSQL CI required")
def test_contract_proposal_review_promotion_raw_sql_immutability():
    command.upgrade(Config("alembic.ini"),"head")
    engine=create_engine(os.environ["MCIAS_TEST_DATABASE_URL"])
    with Session(engine,expire_on_commit=False) as db:
        tag=uuid4().hex
        org=Organization(name="SYN-contract-guard-"+tag)
        db.add(org);db.flush()
        extractor=User(username="SYN-contract-extractor-"+tag,password_hash="synthetic",organization_id=org.id)
        reviewer=User(username="SYN-contract-reviewer-"+tag,password_hash="synthetic",organization_id=org.id)
        db.add_all([extractor,reviewer]);db.flush()
        source_data=b"SYN H1 CONSULT 5000 YER"
        digest=sha256(source_data).hexdigest()
        source=SourceFile(sha256=digest,original_filename="SYN-contract.pdf",storage_key="SYN-object-"+tag)
        db.add(source);db.flush()
        doc=IngestionDocument(organization_id=org.id,source_id=source.id,sha256=digest,
                              filename="SYN-contract.pdf",status="extracted")
        db.add(doc);db.flush()
        job=IngestionJob(organization_id=org.id,document_id=doc.id,status="extracted",manifest={"complete":True})
        db.add(job);db.flush()
        candidate={"source_sha256":digest,"section":"tariffs","logical_key":"H1:CONSULT",
                   "original_clause_text":"SYN H1 CONSULT 5000 YER"}
        prop=ContractProposal(organization_id=org.id,document_id=doc.id,job_id=job.id,
            candidate_hash=sha256(b"SYN-candidate-"+tag.encode()).hexdigest(),
            candidate=candidate,model_id="SYN-test",model_revision="SYN-rev",
            request_sha256=sha256(b"SYN-request").hexdigest(),
            response_sha256=sha256(b"SYN-response").hexdigest(),
            created_by=extractor.id)
        db.add(prop);db.flush()
        review=ContractProposalReview(proposal_id=prop.id,organization_id=org.id,
            reviewer_id=reviewer.id,decision="accepted",reason="SYN independently reviewed quoted evidence")
        db.add(review)
        point=ReferencePoint(organization_id=org.id,section="tariffs",logical_key="H1:CONSULT",version=1,
            title="SYN H1 CONSULT",clause_text="SYN H1 CONSULT 5000 YER",rule_type="amount",
            amount=5000,currency="YER",provider_code="H1",service_code="CONSULT",
            effective_from=date(2026,1,1),effective_until=date(2027,1,1),
            status="draft",created_by=extractor.id,source_document_id=doc.id,
            source_sha256=digest)
        db.add(point);db.flush()
        db.add(ContractProposalPromotion(proposal_id=prop.id,organization_id=org.id,
            reference_point_id=point.id,promoted_by=extractor.id))
        db.commit()
        ids=(prop.id,review.id,point.id)
    with engine.begin() as conn:
        for query,params in [
            ("UPDATE contract_proposals SET candidate_hash=:h WHERE id=:id",
             {"h":"b"*64,"id":ids[0]}),
            ("DELETE FROM contract_proposals WHERE id=:id",{"id":ids[0]}),
            ("UPDATE contract_proposal_reviews SET decision='rejected' WHERE id=:id",
             {"id":ids[1]}),
            ("DELETE FROM contract_proposal_reviews WHERE id=:id",{"id":ids[1]}),
            ("UPDATE contract_proposal_promotions SET promoted_by=:actor WHERE proposal_id=:id",
             {"id":ids[0],"actor":extractor.id}),
            ("DELETE FROM contract_proposal_promotions WHERE proposal_id=:id",{"id":ids[0]}),
        ]:
            with pytest.raises(DBAPIError):
                with conn.begin_nested():
                    conn.execute(text(query),params)
    with Session(engine) as db:
        assert db.get(ContractProposal,ids[0]).candidate_hash!=("b"*64)
        assert db.get(ContractProposalPromotion,ids[0]).reference_point_id==ids[2]
        assert db.get(ContractProposalReview,ids[1]).decision=="accepted"
        assert db.get(ReferencePoint,ids[2]).status=="draft"
    engine.dispose()
