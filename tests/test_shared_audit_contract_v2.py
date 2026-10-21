"""Versioned event-contract tests; native G3 acceptance is tested separately."""
from copy import deepcopy
from hashlib import sha256
import json
import os
from urllib.parse import urlsplit
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import Session

from mcias.audit_contract import clean_claim_audit_details, claim_reference_projection
from mcias.models import AuditLog, Base
from mcias.models_audit import AuditSnapshot
from test_shared_audit_inputs_pg16 import _seed, _write


REASONS = {"MATCH_VERIFIED": "CHECKS_COMPLETED", "VIOLATION_PROVEN": "PROVEN_RULE_BREACH",
           "UNRESOLVED": "REFERENCE_INCOMPLETE", "AUDIT_UNAVAILABLE": "SOURCE_UNAVAILABLE"}


@pytest.fixture(params=["sqlite", "pg16"])
def case(request):
    url = "sqlite://" if request.param == "sqlite" else os.getenv("MCIAS_INPUTS_AUDIT_DATABASE_URL")
    if not url:
        pytest.skip("dedicated synthetic PostgreSQL16 fixture required")
    engine = create_engine(url)
    schema = None
    isolated = engine
    if request.param == "pg16":
        parsed = urlsplit(url.replace("postgresql+psycopg://", "postgresql://", 1))
        assert os.getenv("MCIAS_INPUTS_AUDIT_ALLOW") == "YES"
        assert parsed.hostname in {"localhost", "127.0.0.1"}
        assert parsed.path == "/mcias_inputs_audit"
        with engine.begin() as connection:
            assert connection.dialect.server_version_info[0] == 16
            schema = "audit_v2_" + uuid4().hex
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        isolated = engine.execution_options(schema_translate_map={None: schema})
    Base.metadata.create_all(isolated)
    try:
        yield isolated, _seed(isolated)
    finally:
        if schema:
            with engine.begin() as connection:
                connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        engine.dispose()


def _v2(case, state, *, complete=True):
    engine, (org, actor, claim, old) = case
    with Session(engine) as db:
        previous = db.get(AuditSnapshot, old["audit_snapshot_id"])
        certificates = deepcopy(previous.findings["reference_certificates"])
        for certificate in certificates:
            certificate.update(approved=complete, complete=complete)
            if complete:
                certificate.update(lookup_status="reference_applicable", gaps=[])
            certificate["source_evidence"][0]["document_id"] = old["document_id"]
            certificate["source_evidence"][0]["source_record_id"] = old["source_record_id"]
        findings = {"audit_state_schema_version": 2, "audit_state": state,
            "reason_code": REASONS[state], "reference_certificates": certificates,
            "coverage": {"required": 8, "executed": 8 if complete else 0,
                         "blocked": 0 if complete else 8},
            "agents": [{"rule_id": "tariff", "rule_version": 1, "audit_state": state}]}
        fingerprint = sha256((state + str(complete)).encode()).hexdigest()
        snapshot = AuditSnapshot(organization_id=org, claim_id=claim,
            policy_id="SYN-review-v2", policy_fingerprint=fingerprint,
            calculation={"status": "review_only", "payable": None, "deductions": []},
            findings=findings, verification={"status": "held"}, created_by=actor)
        db.add(snapshot); db.flush()
        details = {**old, "audit_snapshot_id": snapshot.id, "policy_fingerprint": fingerprint,
            "audit_state_schema_version": 2, "audit_state": state,
            "reason_code": REASONS[state], "references": claim_reference_projection(certificates)}
        db.commit()
    return details


@pytest.mark.parametrize("state", list(REASONS))
def test_v2_state_commit_reopen_dedup_and_no_phi(case, state):
    engine, (org, actor, claim, _) = case
    details = _v2(case, state)
    with Session(engine) as db:
        event_id = _write(db, org, actor, claim, {**details,
            "patient_name": "SYN-private-value", "diagnosis": "SYN-private-value"}).id
        db.commit()
    with Session(engine) as db:
        event = db.get(AuditLog, event_id)
        assert event.details["audit_state"] == state
        assert event.details["audit_state_schema_version"] == 2
        assert event.details["reason_code"] == REASONS[state]
        assert "SYN-private-value" not in json.dumps(event.details)
        assert all(details["document_id"] in reference["evidence_ids"] for reference in event.details["references"])
        assert _write(db, org, actor, claim, details).id == event_id
        db.commit()
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(AuditLog)) == 1


def test_legacy_event_contract_is_not_rewritten(case):
    engine, (org, actor, claim, details) = case
    with Session(engine) as db:
        event_id = _write(db, org, actor, claim, details).id
        db.commit()
    with Session(engine) as db:
        persisted = db.get(AuditLog, event_id).details
        assert persisted["audit_state"] == "UNRESOLVED_OR_MISSING_REFERENCE"
        assert "audit_state_schema_version" not in persisted


def test_new_names_require_explicit_v2_and_known_reason(case):
    details = _v2(case, "UNRESOLVED")
    for invalid in ({**details, "audit_state_schema_version": 1},
                    {**details, "audit_state_schema_version": True},
                    {**details, "audit_state_schema_version": 3},
                    {**details, "reason_code": "patient narrative"}):
        with pytest.raises(ValueError):
            clean_claim_audit_details(invalid)


@pytest.mark.parametrize("state", ["MATCH_VERIFIED", "VIOLATION_PROVEN"])
def test_incomplete_reference_cannot_be_logged_as_completed(case, state):
    engine, (org, actor, claim, _) = case
    details = _v2(case, state, complete=False)
    with Session(engine) as db:
        with pytest.raises(ValueError, match="complete reference coverage"):
            _write(db, org, actor, claim, details)
        db.rollback()
        assert db.scalar(select(func.count()).select_from(AuditLog)) == 0


def test_reference_version_substitution_is_rejected(case):
    engine, (org, actor, claim, _) = case
    details = _v2(case, "UNRESOLVED")
    changed = deepcopy(details)
    changed["references"][0]["version"] += 1
    with Session(engine) as db:
        with pytest.raises(ValueError, match="reference correlation mismatch"):
            _write(db, org, actor, claim, changed)
        db.rollback()
        assert db.scalar(select(func.count()).select_from(AuditLog)) == 0
