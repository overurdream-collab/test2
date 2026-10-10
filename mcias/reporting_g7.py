"""G7 deterministic reports: frozen source integrity, financial reconciliation, default-deny disclosure.

This is an engineering snapshot builder, NOT institutional approval of accounting policy.
It must not change any G4, G5 or G6 record.
"""
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
from sqlalchemy import select
from mcias.models import AuditLog
from mcias.models_claims import ClaimBatch, ClaimEntry
from mcias.models_audit import AuditSnapshot
from mcias.models_governance_g6 import GovernanceCase, GovernanceEvent
from mcias.models_reporting_g7 import ReportSnapshot
from mcias.palermo2 import verify as verify_palermo2

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

def freeze_batch(batch, claims, snapshots, cases, events):
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
        }
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
    summary = {"total_claims": len(rows), "by_currency": {}}
    for currency, values in sorted(totals.items()):
        if values["approved_claimed"] + values["held_claimed"] != values["claimed"]:
            raise ReportBlocked("T20 claim aggregation failed")
        if values["payable"] + values["deductions"] != values["approved_claimed"]:
            raise ReportBlocked("T20 payable reconciliation failed")
        summary["by_currency"][currency] = {
            k: v if isinstance(v, int) else number(v) for k, v in values.items()
        }
    dataset = {"schema": 1, "organization_id": org, "batch_id": batch.id,
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
    dataset, summary = freeze_batch(batch, claims, snapshots, cases, events)
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
    db.add(AuditLog(actor_id=actor.id, action="g7_report_frozen",
        resource_type="report_snapshot", resource_id=report.id,
        details={"batch_id": batch_id, "version": report.version, "sha256": digest}))
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
