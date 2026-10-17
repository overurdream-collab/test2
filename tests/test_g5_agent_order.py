"""Synthetic SQL regression of inspect_claim; no production approval or payment."""
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from mcias.audit_agents import AGENTS, inspect_claim
from mcias.models import Base, Organization, SourceFile, User
from mcias.models_claims import ClaimAttachment, ClaimBatch, ClaimEntry
from mcias.models_ingestion import ExtractedSourceRecord, IngestionDocument, IngestionJob
from mcias.models_reference import (
    BeneficiaryCategory, BeneficiaryEnrollment, ContractVersion, ProviderTariff,
)

EXPECTED_ORDER = (
    "eligibility", "contract", "tariff", "exclusion", "caps", "cost_sharing",
    "duplicates", "evidence",
)


@pytest.fixture
def agent_database():
    engine = create_engine("sqlite+pysqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def enforce_foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    try:
        with Session(engine) as db:
            org = Organization(name="Synthetic agent-order regression")
            db.add(org)
            db.flush()
            actor = User(organization_id=org.id, username="synthetic-agent-order", password_hash="test-only")
            source = SourceFile(sha256="a" * 64, original_filename="synthetic.csv", storage_key="synthetic-agent-order")
            db.add_all([actor, source])
            db.flush()
            document = IngestionDocument(organization_id=org.id, source_id=source.id,
                sha256=source.sha256, filename="synthetic.csv", status="extracted")
            db.add(document)
            db.flush()
            job = IngestionJob(organization_id=org.id, document_id=document.id,
                status="extracted", manifest={"complete": True})
            db.add(job)
            db.flush()
            records = [ExtractedSourceRecord(job_id=job.id, locator={"kind": "row", "row": i + 2},
                values={"claim_reference": "SYN-claim"}, confidence=100) for i in range(2)]
            db.add_all(records)
            db.flush()
            batch = ClaimBatch(organization_id=org.id, ingestion_document_id=document.id,
                created_by=actor.id, source_sha256=source.sha256, record_count=2, imported_count=1)
            db.add(batch)
            db.flush()
            claim = ClaimEntry(organization_id=org.id, batch_id=batch.id, extracted_record_id=records[0].id,
                source_locator=records[0].locator, source_values=records[0].values,
                claim_reference="SYN-claim", beneficiary_token="synthetic-token", provider_code="SYN-provider",
                service_code="SYN-service", service_date=date(2026, 6, 1),
                claimed_amount=Decimal("100"), currency="YER")
            db.add(claim)
            db.flush()
            yield db, actor, document, records[1], claim
    finally:
        engine.dispose()


@pytest.mark.parametrize("references,tariff_currency,duplicate,approved", [
    (True, "YER", False, True),
    (False, "YER", False, True),
    (True, "USD", False, True),
    (True, "YER", True, True),
    (True, "YER", False, False),
])
def test_inspect_claim_returns_eight_ordered_findings(
        agent_database, references, tariff_currency, duplicate, approved):
    db, actor, document, second_record, claim = agent_database
    contract = tariff = enrollment = attachment = None
    if references:
        category = BeneficiaryCategory(organization_id=claim.organization_id,
            code="SYN-category", description="Synthetic regression category")
        contract = ContractVersion(organization_id=claim.organization_id, provider_code=claim.provider_code,
            version=1, status="approved", effective_from=date(2026, 1, 1), effective_until=date(2027, 1, 1))
        db.add_all([category, contract])
        db.flush()
        enrollment = BeneficiaryEnrollment(organization_id=claim.organization_id,
            beneficiary_token=claim.beneficiary_token, category_id=category.id,
            effective_from=date(2026, 1, 1), effective_until=date(2027, 1, 1))
        tariff = ProviderTariff(contract_id=contract.id, service_code=claim.service_code,
            amount=Decimal("100"), currency=tariff_currency)
        attachment = ClaimAttachment(organization_id=claim.organization_id, claim_id=claim.id,
            ingestion_document_id=document.id, document_sha256=document.sha256, linked_by=actor.id)
        db.add_all([enrollment, tariff, attachment])
    if duplicate:
        db.add(ClaimEntry(organization_id=claim.organization_id, batch_id=claim.batch_id,
            extracted_record_id=second_record.id, source_locator=second_record.locator,
            source_values=second_record.values, claim_reference=claim.claim_reference,
            beneficiary_token=claim.beneficiary_token, provider_code=claim.provider_code,
            service_code=claim.service_code, service_date=claim.service_date,
            claimed_amount=claim.claimed_amount, currency=claim.currency))
    db.flush()

    # Invoke actual checks and SQL queries, rather than constructing findings.
    result = inspect_claim(db, claim, SimpleNamespace(approved=approved, policy_id="synthetic-policy"))
    assert tuple(f["agent"] for f in result["findings"]) == EXPECTED_ORDER
    assert AGENTS == EXPECTED_ORDER
    expected = {name: "pass" for name in EXPECTED_ORDER}
    if not references:
        expected.update({name: "hold" for name in ("eligibility", "contract", "tariff", "evidence")})
    elif tariff_currency != claim.currency:
        expected["tariff"] = "hold"
    if duplicate:
        expected["duplicates"] = "review"
    if not approved:
        expected.update({name: "hold" for name in ("exclusion", "caps", "cost_sharing")})
    assert {f["agent"]: f["status"] for f in result["findings"]} == expected
    assert result["review_required"] == any(status != "pass" for status in expected.values())
    assert result["eligible"] == references
    assert result["evidence_complete"] == references
    assert result["contract"] is contract
    assert result["enrollment"] is enrollment
    assert result["tariff"] is (tariff if references and tariff_currency == claim.currency else None)
    findings = {f["agent"]: f for f in result["findings"]}
    assert findings["contract"]["reference"] == (contract.id if contract else None)
    assert findings["eligibility"]["reference"] == (enrollment.id if enrollment else None)
    assert findings["evidence"]["reference"] == ([attachment.id] if attachment else [])



def test_approved_uncompiled_reference_point_blocks_even_8_clean_checks(agent_database):
    """Real G5 SQL check must respect new temporal-reference hold, not fake pass."""
    from mcias.models_reference_points import ReferencePoint
    db, actor, document, second_record, claim = agent_database
    category = BeneficiaryCategory(organization_id=claim.organization_id,
        code="SYN-CAT", description="Synthetic eligible category")
    contract = ContractVersion(organization_id=claim.organization_id,
        provider_code=claim.provider_code, version=1, status="approved",
        effective_from=date(2026, 1, 1), effective_until=date(2027, 1, 1))
    db.add_all([category, contract])
    db.flush()
    db.add_all([
        BeneficiaryEnrollment(organization_id=claim.organization_id,
            beneficiary_token=claim.beneficiary_token, category_id=category.id,
            effective_from=date(2026, 1, 1), effective_until=date(2027, 1, 1)),
        ProviderTariff(contract_id=contract.id, service_code=claim.service_code,
            amount=Decimal("100"), currency="YER"),
        ClaimAttachment(organization_id=claim.organization_id, claim_id=claim.id,
            ingestion_document_id=document.id, document_sha256=document.sha256,
            linked_by=actor.id),
        ReferencePoint(organization_id=claim.organization_id, section="approvals",
            logical_key="SYN-prior-approval", version=1, title="Prior approval",
            clause_text="Synthetic approval required on this service",
            rule_type="approval", provider_code=claim.provider_code,
            service_code=claim.service_code, effective_from=date(2026, 1, 1),
            effective_until=date(2027, 1, 1), status="approved",
            created_by=actor.id, approved_by=actor.id),
    ])
    db.flush()
    policy = SimpleNamespace(approved=True, policy_id="SYN-approved",
        tariff=Decimal("100"), copay_percent=Decimal("20"), exclusion=Decimal("0"))
    checks = inspect_claim(db, claim, policy)
    assert all(f["status"] == "pass" for f in checks["findings"])
    assert checks["reference_reconciliation"]["status"] == "hold"
    assert "uncompiled_approvals_point" in checks["reference_reconciliation"]["unresolved"]
    assert checks["review_required"] is True
