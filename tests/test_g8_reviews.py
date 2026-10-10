"""G8 independent quality feedback: T14 false positives with explicit denominators."""
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from types import SimpleNamespace
import pytest

from mcias.models import Base, Organization, User
from mcias.models_ingestion import IngestionDocument  # noqa: F401
from mcias.models_claims import ClaimEntry  # noqa: F401
from mcias.models_audit import AuditSnapshot  # noqa: F401
from mcias.models_governance_g6 import GovernanceCase  # noqa: F401
from mcias.models_reporting_g7 import ReportSnapshot  # noqa: F401
from mcias.models_g8 import AnalysisRun, AnalysisSignalReview
from mcias.intelligence_g8 import IntelligenceBlocked, digest
from mcias import intelligence_review_g8 as review

@pytest.fixture
def signal_database(monkeypatch):
    engine=create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine,expire_on_commit=False) as db:
        org=Organization(name="G8 synthetic reviewer org")
        foreign=Organization(name="G8 synthetic foreign org")
        author=User(username="g8-feedback-author",password_hash="synthetic")
        reviewer=User(username="g8-feedback-reviewer",password_hash="synthetic")
        stranger=User(username="g8-feedback-stranger",password_hash="synthetic")
        db.add_all([org,foreign,author,reviewer,stranger]);db.flush()
        author.organization_id=reviewer.organization_id=org.id
        stranger.organization_id=foreign.id
        findings=[{"status":"review_only","indicator":"hold_rate",
                  "group":"provider-X","currency":"YER",
                  "sample_count":10,"numerator":"7","denominator":"10"}]
        sources=[{"report_id":"synthetic-source","fingerprint":"a"*64}]
        result={"analysis_type":"signals","output":{"findings":findings},
                "status":"review_only"}
        parameters={"source":"g7_frozen_report_snapshots","min_group_size":5}
        fp=digest({"kind":"signals","sources":sources,
                   "parameters":parameters,"result":result,"task_id":None})
        run=AnalysisRun(organization_id=org.id,kind="signals",
            sources=sources,parameters=parameters,result=result,
            fingerprint=fp,created_by=author.id)
        db.add(run);db.commit()
        monkeypatch.setattr(review,"_authorize",lambda db,actor,permission:actor.organization_id)
        yield db,run,author,reviewer,stranger
    engine.dispose()

def test_t14_false_positive_rates_explicit_denominator(signal_database):
    db,run,author,reviewer,_=signal_database
    start=review.reviews_summary(db,reviewer,run.id)
    assert start["signal_count"]==1 and start["reviewed_signals"]==0
    assert start["false_positive_rate_among_reviewed"] is None
    result=review.add_review(db,reviewer,run.id,0,"false_positive","DATA_QUALITY")
    assert result.version==1
    status=review.reviews_summary(db,reviewer,run.id)
    assert status["reviewed_signals"]==1
    assert status["by_disposition"]["false_positive"]==1
    assert status["false_positive_rate_among_reviewed"]=="100"
    assert status["denominator"]=="reviewed_signals_only"
    assert "fraud_confirmed" not in str(status).lower()

def test_t14_reassessment_appends_revision_without_overwriting_history(signal_database):
    db,run,author,reviewer,_=signal_database
    first=review.add_review(db,reviewer,run.id,0,"false_positive","DATA_QUALITY")
    second=review.add_review(db,reviewer,run.id,0,"needs_followup","NEEDS_SOURCE_REVIEW")
    assert first.id!=second.id and first.version==1 and second.version==2
    latest=review.reviews_summary(db,reviewer,run.id)
    assert latest["by_disposition"]["false_positive"]==0
    assert latest["by_disposition"]["needs_followup"]==1
    assert latest["false_positive_rate_among_reviewed"]=="0"
    assert db.scalars(select(AnalysisSignalReview)).all()==[first,second]

def test_t15_signal_author_and_foreign_tenant_cannot_review(signal_database):
    db,run,author,reviewer,stranger=signal_database
    with pytest.raises(IntelligenceBlocked,match="independent"):
        review.add_review(db,author,run.id,0,"false_positive","DATA_QUALITY")
    with pytest.raises(IntelligenceBlocked,match="not accessible"):
        review.add_review(db,stranger,run.id,0,"false_positive","DATA_QUALITY")
    with pytest.raises(IntelligenceBlocked,match="not accessible"):
        review.reviews_summary(db,stranger,run.id)
    assert db.scalars(select(AnalysisSignalReview)).all()==[]

def test_t15_signal_review_rejects_arbitrary_notes_and_signal_index(signal_database):
    db,run,author,reviewer,_=signal_database
    with pytest.raises(IntelligenceBlocked,match="coded reasons"):
        review.add_review(db,reviewer,run.id,0,"false_positive","patient diagnosis")
    with pytest.raises(IntelligenceBlocked,match="out of range"):
        review.add_review(db,reviewer,run.id,30,"false_positive","DATA_QUALITY")
    with pytest.raises(IntelligenceBlocked,match="coded reasons"):
        review.add_review(db,reviewer,run.id,0,"fraud_confirmed","DATA_QUALITY")

def test_g8_review_immutable_after_persistence(signal_database):
    db,run,author,reviewer,_=signal_database
    entry=review.add_review(db,reviewer,run.id,0,"false_positive","DATA_QUALITY")
    entry.disposition="needs_followup"
    with pytest.raises(ValueError,match="append-only"):
        db.flush()
    db.rollback()

def test_g8_review_source_fingerprint_integrity(signal_database):
    db,run,author,reviewer,_=signal_database
    review.add_review(db,reviewer,run.id,0,"false_positive","DATA_QUALITY")
    run.result["output"]["findings"][0]["sample_count"]=55
    # ORM changes to stored JSON are blocked, but verify on a forged read fails closed.
    with pytest.raises(IntelligenceBlocked,match="integrity"):
        review.reviews_summary(db,reviewer,run.id)
