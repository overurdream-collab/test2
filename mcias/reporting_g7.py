"""G7 deterministic reports: frozen source integrity, financial reconciliation, default-deny disclosure.

This is an engineering snapshot builder, NOT institutional approval of accounting policy.
It must not change any G4, G5 or G6 record.
"""
from decimal import Decimal, InvalidOperation
from datetime import date
from hashlib import sha256
import json
from sqlalchemy import select
from mcias.models import AuditLog
from mcias.models_claims import ClaimBatch, ClaimEntry
from mcias.models_audit import AuditSnapshot
from mcias.models_governance_g6 import GovernanceCase, GovernanceEvent
from mcias.models_reporting_g7 import ReportSnapshot
from mcias.palermo2 import verify as verify_palermo2
from mcias.audit_agents import AGENTS, OFFICIAL_AUDIT_STATES, project_audit_findings
from mcias.audit_contract import (REFERENCE_FAMILIES, CLAIM_AUDIT_ACTION,
    CLAIM_AUDIT_REASONS_V2, claim_reference_projection, clean_claim_audit_details, _uuid)
from mcias.audit_writer import write_event

class ReportBlocked(ValueError):
    pass

def canonical(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")

def fingerprint(dataset, summary):
    return sha256(canonical({"dataset": dataset, "summary": summary})).hexdigest()

def amount(value):
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ReportBlocked("invalid monetary data") from exc
    if not result.is_finite() or result < 0:
        raise ReportBlocked("non-finite or negative monetary data")
    return result

def number(value):
    return format(value, "f")

def _same_org(obj, org):
    if obj.organization_id != org:
        raise ReportBlocked("cross-organization evidence mismatch")

def _evidence_ids(values):
    """Historical free text is never a public evidence identifier."""
    safe = set()
    for value in values if isinstance(values, list) else []:
        try:
            safe.add(_uuid(value))
        except ValueError:
            continue
    return sorted(safe)

def _reference_core(references):
    return [{key: reference[key] for key in ("family", "id", "version", "status", "evidence_ids", "gaps")}
            for reference in references]

def _audit_projection(snapshot, claim, batch):
    """Read the existing G5 contract; never infer audit completion from a name."""
    result = {"audit_state": None, "audit_state_schema_version": 2,
        "source_audit_state_schema_version": None, "audit_reason_code": None,
        "completed_audit": False, "audit_coverage": None, "audit_references": [],
        "audit_rules": [], "source_evidence_verified": False,
        "complete_reference_count": 0}
    if snapshot is None or not isinstance(snapshot.findings, dict) or "audit_state" not in snapshot.findings:
        return result
    try:
        findings = project_audit_findings(snapshot.findings)
    except (TypeError, ValueError) as exc:
        raise ReportBlocked("invalid stored audit outcome") from exc
    state = findings["audit_state"]
    result.update(audit_state=state,
        source_audit_state_schema_version=findings["source_audit_state_schema_version"])
    if findings.get("reason_code") in CLAIM_AUDIT_REASONS_V2[state]:
        result["audit_reason_code"] = findings["reason_code"]
    certificates = findings.get("reference_certificates", [])
    if not isinstance(certificates, list) or any(not isinstance(certificate, dict) for certificate in certificates):
        raise ReportBlocked("invalid stored reference certificates")
    if certificates:
        try:
            safe = clean_claim_audit_details({"audit_snapshot_id": snapshot.id,
                "source_record_id": claim.extracted_record_id, "document_id": claim.source_locator.get("document_id"),
                "source_sha256": batch.source_sha256, "policy_fingerprint": snapshot.policy_fingerprint,
                "audit_state": snapshot.findings["audit_state"],
                "audit_state_schema_version": snapshot.findings.get("audit_state_schema_version", 1),
                "reason_code": snapshot.findings.get("reason_code"),
                "references": claim_reference_projection(certificates)})
            result["audit_references"] = safe["references"]
            by_family = {certificate["family"]: certificate for certificate in certificates}
            for reference in result["audit_references"]:
                for key in ("effective_from", "effective_until", "coverage_from", "coverage_until"):
                    value = by_family[reference["family"]].get(key)
                    reference[key] = date.fromisoformat(value).isoformat() if value is not None else None
        except (ValueError, TypeError) as exc:
            raise ReportBlocked("invalid stored reference certificates") from exc
    source = findings.get("source_evidence")
    locator = claim.source_locator
    result["source_evidence_verified"] = bool(isinstance(source, dict)
        and source.get("source_record_id") == claim.extracted_record_id
        and source.get("document_id") == locator.get("document_id")
        and source.get("document_id") == getattr(batch, "ingestion_document_id", locator.get("document_id"))
        and source.get("document_id")
        and source.get("source_sha256") == batch.source_sha256 == locator.get("source_sha256")
        and source.get("source_scope_approval_id") == locator.get("source_scope_approval_id")
        and source.get("source_scope_approval_id"))
    ready = set()
    for certificate in certificates:
        if certificate.get("organization_id") != claim.organization_id:
            raise ReportBlocked("cross-organization reference mismatch")
        try:
            valid = (certificate.get("approved") is True and certificate.get("complete") is True
                and certificate.get("lookup_status") == "reference_applicable" and not certificate.get("gaps")
                and certificate.get("reference_id") and certificate.get("version") is not None
                and certificate.get("source_evidence")
                and date.fromisoformat(certificate["effective_from"]) <= claim.service_date < date.fromisoformat(certificate["effective_until"])
                and date.fromisoformat(certificate["coverage_from"]) <= claim.service_date < date.fromisoformat(certificate["coverage_until"]))
        except (AttributeError, KeyError, TypeError, ValueError):
            valid = False
        if valid:
            ready.add(certificate.get("family"))
    result["complete_reference_count"] = len(ready & REFERENCE_FAMILIES)
    coverage = findings.get("coverage", {})
    if isinstance(coverage, dict) and all(type(coverage.get(key)) is int for key in ("required", "executed", "blocked")):
        result["audit_coverage"] = {key: coverage[key] for key in ("required", "executed", "blocked")}
    checks = findings.get("agents", [])
    if not isinstance(checks, list) or any(not isinstance(check, dict) for check in checks):
        raise ReportBlocked("invalid stored audit checks")
    for check in checks:
        if check.get("rule_id") in AGENTS and type(check.get("rule_version")) is int and 1 <= check["rule_version"] <= 999999999:
            result["audit_rules"].append({"rule_id": check["rule_id"], "rule_version": check["rule_version"],
                "audit_state": check.get("audit_state"),
                "reference_families": [family for family in check.get("reference_families", []) if family in REFERENCE_FAMILIES],
                "evidence_record_ids": _evidence_ids(check.get("reference"))})
    completed_checks = (len(checks) == len(AGENTS) and {check.get("agent") for check in checks} == set(AGENTS)
        and all(check.get("audit_state") in {"MATCH_VERIFIED", "VIOLATION_PROVEN"}
            and check.get("rule_id") == check.get("agent")
            and type(check.get("rule_version")) is int and 1 <= check["rule_version"] <= 999999999
            and isinstance(check.get("reference"), list)
            and all(isinstance(value, str) for value in check["reference"])
            and len(_evidence_ids(check["reference"])) == len(set(check["reference"])) for check in checks))
    state_proven = (all(check.get("audit_state") == "MATCH_VERIFIED" for check in checks)
        if state == "MATCH_VERIFIED" else any(check.get("audit_state") == "VIOLATION_PROVEN" for check in checks))
    result["completed_audit"] = bool(state in {"MATCH_VERIFIED", "VIOLATION_PROVEN"}
        and result["source_evidence_verified"] and len(certificates) == len(REFERENCE_FAMILIES)
        and ready == REFERENCE_FAMILIES and completed_checks and state_proven
        and result["audit_coverage"] == {"required": len(AGENTS), "executed": len(AGENTS), "blocked": 0})
    return result


def freeze_batch(batch, claims, snapshots, cases, events, audit_events=()):
    """Pure builder; never rounds or invents an institution's accounting policy."""
    org = batch.organization_id
    by_claim, by_snapshot, by_case = {}, {}, {}
    for s in snapshots:
        _same_org(s, org)
        by_claim.setdefault(s.claim_id, []).append(s)
    for c in cases:
        _same_org(c, org)
        by_snapshot.setdefault(c.audit_snapshot_id, []).append(c)
    for e in events:
        _same_org(e, org)
        by_case.setdefault(e.case_id, []).append(e)

    shared_events = {}
    for event in audit_events:
        if event.action == CLAIM_AUDIT_ACTION:
            details = event.details
            if not isinstance(details, dict):
                raise ReportBlocked("invalid shared audit evidence")
            if details.get("organization_id") != org:
                raise ReportBlocked("cross-organization audit event mismatch")
            shared_events.setdefault(details.get("audit_snapshot_id"), []).append(event)
    rows = []
    totals = {}
    observed = set()
    for claim in sorted(claims, key=lambda item: item.id):
        _same_org(claim, org)
        if claim.batch_id != batch.id or claim.id in observed:
            raise ReportBlocked("claim batch integrity failure")
        observed.add(claim.id)
        claimed = amount(claim.claimed_amount)
        if not isinstance(claim.source_values, dict) or not isinstance(claim.source_locator, dict):
            raise ReportBlocked("original source provenance is missing")
        if len(claim.currency) != 3 or not claim.currency.isupper():
            raise ReportBlocked("invalid claim currency")
        possible = by_claim.get(claim.id, [])
        snapshot = max(possible, key=lambda s: (s.created_at, s.id)) if possible else None
        if snapshot:
            _same_org(snapshot, org)
        cands = by_snapshot.get(snapshot.id, []) if snapshot else []
        chosen_case = max(cands, key=lambda c: (c.created_at, c.id)) if cands else None
        if chosen_case and chosen_case.claim_id != claim.id:
            raise ReportBlocked("governance case claim mismatch")
        events_for_case = by_case.get(chosen_case.id, []) if chosen_case else []
        if any(e.snapshot_id != chosen_case.audit_snapshot_id for e in events_for_case):
            raise ReportBlocked("governance evidence snapshot mismatch")
        latest = max(events_for_case, key=lambda e: (e.version, e.id)) if events_for_case else None
        state = "held"
        reason = "awaiting_verified_approval"
        payable = None
        deduction = None
        if snapshot and latest and latest.kind == "approve":
            calc = snapshot.calculation
            findings = snapshot.findings.get("agents", []) if isinstance(snapshot.findings, dict) else []
            independent = verify_palermo2(claim, findings, calc)
            if (isinstance(calc, dict) and calc.get("status") == "calculated"
                and independent["status"] == "verified"
                and snapshot.verification.get("status") == "verified"
                and calc.get("currency") == claim.currency
                and calc.get("source_id") == claim.extracted_record_id):
                calc_claimed = amount(calc.get("claimed"))
                candidate = amount(calc.get("payable"))
                steps = calc.get("deductions")
                if not isinstance(steps, list):
                    raise ReportBlocked("missing deduction evidence")
                deductions = sum((amount(x["deduction"]) for x in steps), Decimal(0))
                actual = calc.get("fingerprint")
                recalculated = sha256(canonical({k: v for k, v in calc.items()
                                                if k != "fingerprint"})).hexdigest()
                if (calc_claimed == claimed and candidate + deductions == claimed
                    and actual == recalculated):
                    state, reason, payable, deduction = "approved", None, number(candidate), number(deductions)
                else:
                    reason = "financial_reconciliation_hold"
            else:
                reason = "unverified_calculation_hold"
        if latest and latest.kind == "object":
            state, reason = "held", "open_objection"
        item = {
            "claim_id": claim.id, "claim_reference": claim.claim_reference,
            "beneficiary_token": claim.beneficiary_token,
            "currency": claim.currency, "claimed": number(claimed),
            "state": state, "hold_reason": reason,
            "payable": payable, "deduction": deduction,
            "audit_snapshot_id": snapshot.id if snapshot else None,
            "governance_case_id": chosen_case.id if chosen_case else None,
            "governance_event_id": latest.id if latest else None,
            "governance_event_version": latest.version if latest else None,
            "source_record_id": claim.extracted_record_id,
            "source_locator": claim.source_locator,
            "source_values": claim.source_values,
            "source_document_id": claim.source_locator.get("document_id"),
            "source_sha256": batch.source_sha256,
            "source_position": {key: claim.source_locator[key] for key in
                ("kind", "index", "row", "column", "page", "bbox") if key in claim.source_locator},
            **_audit_projection(snapshot, claim, batch),
        }
        correlated = shared_events.get(snapshot.id, []) if snapshot else []
        if len(correlated) > 1:
            raise ReportBlocked("duplicate shared audit outcome event")
        if any(event.resource_type != "claim_entry" or event.details.get("outcome") != "success"
               or event.resource_id != claim.id or event.details.get("source_record_id") != claim.extracted_record_id
               or event.details.get("document_id") != claim.source_locator.get("document_id")
               or event.details.get("source_sha256") != batch.source_sha256 for event in correlated):
            raise ReportBlocked("shared audit claim/source mismatch")
        for event in correlated:
            try:
                _uuid(event.id)
                safe = clean_claim_audit_details(event.details)
            except ValueError as exc:
                raise ReportBlocked("invalid shared audit evidence") from exc
            if (safe["audit_state"] != snapshot.findings.get("audit_state")
                or safe.get("audit_state_schema_version", 1) != snapshot.findings.get("audit_state_schema_version", 1)
                or safe.get("reason_code") != snapshot.findings.get("reason_code")
                or safe["policy_fingerprint"] != snapshot.policy_fingerprint
                or safe["references"] != _reference_core(item["audit_references"])):
                raise ReportBlocked("shared audit outcome/reference mismatch")
        item["audit_event_ids"] = sorted(event.id for event in correlated)
        item["completed_audit"] = item["completed_audit"] and len(correlated) == 1
        rows.append(item)
        tot = totals.setdefault(claim.currency, {
            "claimed": Decimal(0), "approved_claimed": Decimal(0),
            "held_claimed": Decimal(0), "payable": Decimal(0),
            "deductions": Decimal(0), "approved_count": 0, "held_count": 0,
        })
        tot["claimed"] += claimed
        if state == "approved":
            tot["approved_claimed"] += claimed
            tot["payable"] += amount(payable)
            tot["deductions"] += amount(deduction)
            tot["approved_count"] += 1
        else:
            tot["held_claimed"] += claimed
            tot["held_count"] += 1

    if batch.imported_count != len(rows) or batch.record_count != len(rows) or batch.status != "imported":
        raise ReportBlocked("batch not fully imported; report cannot be reconciled")
    completed = sum(row["completed_audit"] for row in rows)
    summary = {"total_claims": len(rows), "by_currency": {}, "audit": {
        "audit_state_schema_version": 2,
        "outcome_counts": {state: sum(row["audit_state"] == state for row in rows) for state in sorted(OFFICIAL_AUDIT_STATES)},
        "completed_audit_count": completed, "incomplete_audit_count": len(rows) - completed,
        "unclassified_count": sum(row["audit_state"] is None for row in rows),
        "complete_reference_count": sum(row["complete_reference_count"] for row in rows),
        "required_reference_count": len(rows) * len(REFERENCE_FAMILIES),
        "source_evidence_verified_count": sum(row["source_evidence_verified"] for row in rows)}}
    for currency, values in sorted(totals.items()):
        if values["approved_claimed"] + values["held_claimed"] != values["claimed"]:
            raise ReportBlocked("T20 claim aggregation failed")
        if values["payable"] + values["deductions"] != values["approved_claimed"]:
            raise ReportBlocked("T20 payable reconciliation failed")
        summary["by_currency"][currency] = {
            k: v if isinstance(v, int) else number(v) for k, v in values.items()
        }
    dataset = {"schema": 2, "organization_id": org, "batch_id": batch.id,
               "source_sha256": batch.source_sha256, "rows": rows}
    return dataset, summary

def verify_snapshot(report):
    if report.fingerprint != fingerprint(report.dataset, report.summary):
        raise ReportBlocked("frozen report integrity failure")
    return True

def create_snapshot(db, actor, batch_id):
    if not actor.active or not actor.organization_id:
        raise ReportBlocked("active organization required")
    # Lock the batch to serialize versions. PostgreSQL is authoritative.
    batch = db.scalar(select(ClaimBatch).where(
        ClaimBatch.id == batch_id, ClaimBatch.organization_id == actor.organization_id
    ).with_for_update())
    if batch is None:
        raise ReportBlocked("batch not accessible")
    claims = db.scalars(select(ClaimEntry).where(
        ClaimEntry.batch_id == batch_id, ClaimEntry.organization_id == actor.organization_id
    ).order_by(ClaimEntry.id)).all()
    if len(claims) > 10000:
        raise ReportBlocked("report exceeds the provisional 10000-claim engineering limit")
    snapshots = db.scalars(select(AuditSnapshot).join(
        ClaimEntry, AuditSnapshot.claim_id == ClaimEntry.id
    ).where(ClaimEntry.batch_id == batch_id,
            AuditSnapshot.organization_id == actor.organization_id)).all()
    cases = db.scalars(select(GovernanceCase).join(
        ClaimEntry, GovernanceCase.claim_id == ClaimEntry.id
    ).where(ClaimEntry.batch_id == batch_id,
            GovernanceCase.organization_id == actor.organization_id)).all()
    events = db.scalars(select(GovernanceEvent).join(
        GovernanceCase, GovernanceEvent.case_id == GovernanceCase.id
    ).join(ClaimEntry, GovernanceCase.claim_id == ClaimEntry.id).where(
        ClaimEntry.batch_id == batch_id,
        GovernanceEvent.organization_id == actor.organization_id)).all()
    audit_events = db.scalars(select(AuditLog).where(AuditLog.action == CLAIM_AUDIT_ACTION,
        AuditLog.resource_type == "claim_entry", AuditLog.resource_id.in_([claim.id for claim in claims]))).all()
    dataset, summary = freeze_batch(batch, claims, snapshots, cases, events, audit_events)
    digest = fingerprint(dataset, summary)
    previous = db.scalar(select(ReportSnapshot).where(
        ReportSnapshot.organization_id == actor.organization_id,
        ReportSnapshot.batch_id == batch_id
    ).order_by(ReportSnapshot.version.desc()).limit(1))
    if previous:
        verify_snapshot(previous)
        if previous.fingerprint == digest:
            return previous
    report = ReportSnapshot(organization_id=actor.organization_id, batch_id=batch_id,
        version=previous.version + 1 if previous else 1, dataset=dataset, summary=summary,
        fingerprint=digest, created_by=actor.id)
    db.add(report)
    db.flush()
    write_event(db, actor=actor, organization_id=actor.organization_id, action="g7_report_frozen",
        resource_type="report_snapshot", resource_id=report.id, outcome="success",
        details={"version": report.version})
    db.commit()
    return report

def beneficiary_statement(report, token):
    verify_snapshot(report)
    if not token:
        raise ReportBlocked("beneficiary token is required")
    rows = report.dataset["rows"]
    return {"report_id": report.id, "report_version": report.version,
            "beneficiary_token": token, "items": [
                {"claim_reference": row["claim_reference"], "currency": row["currency"],
                 "claimed": row["claimed"], "payable": row["payable"],
                 "state": row["state"], "hold_reason": row["hold_reason"]}
                for row in rows if row["beneficiary_token"] == token
            ]}
