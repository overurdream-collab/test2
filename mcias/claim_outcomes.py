"""Conservative four-file audit triage; a classification is not a payment decision."""
import csv
import io
from collections import Counter

REJECTED = "REJECTED_RULE_CERTAIN"
ACCEPTED = "ACCEPTED_RULES"
MISSING = "MISSING_ATTACHMENTS"
REVIEW = "HUMAN_REVIEW"
KINDS = (REJECTED, ACCEPTED, MISSING, REVIEW)


def classify(findings, verification, calculation):
    """Use only server-side deterministic, evidence-backed failure statuses.

    Missing enrollment from a possibly incomplete beneficiary registry is NOT
    proof of ineligibility. AI predictions never create confirmed rejection.
    """
    agents = findings.get("agents", []) if isinstance(findings, dict) else []
    if not isinstance(agents, list) or len(agents) != 8:
        return REVIEW, "audit_checks_missing"
    if any(not isinstance(f, dict) for f in agents):
        return REVIEW, "malformed_audit_finding"
    # A purported deterministic rejection must also pass independent Palermo
    # reconciliation. Existing Palermo-2 holds non-pass findings, so these
    # remain human-review cases until a dedicated verified-failure path exists.
    for finding in agents:
        if finding.get("status") == "fail_confirmed":
            if (finding.get("evidence_confirmed") is True
                and finding.get("source_reference")
                and isinstance(verification, dict)
                and verification.get("status") == "verified"):
                return REJECTED, str(finding.get("reason") or "confirmed_rule_failure")[:160]
            return REVIEW, "confirmed_failure_requires_independent_verification"
    for finding in agents:
        if finding.get("agent") == "evidence" and finding.get("status") == "hold":
            return MISSING, "required_evidence_missing"
    if any(f.get("status") != "pass" for f in agents):
        return REVIEW, "unresolved_rule_finding"
    if (not isinstance(verification, dict) or verification.get("status") != "verified"
        or not isinstance(calculation, dict) or calculation.get("status") != "calculated"):
        return REVIEW, "independent_verification_pending"
    return ACCEPTED, "all_applicable_rules_passed"


def classify_claims(claims, audit_snapshots):
    """One output row per claim, choosing the latest immutable audit snapshot.

    Caller must supply only one tenant/batch; this guard is defense in depth.
    """
    latest = {}
    for snap in audit_snapshots:
        if not any(c.id == snap.claim_id and c.organization_id == snap.organization_id for c in claims):
            raise ValueError("cross-batch or cross-organization audit snapshot")
        prior = latest.get(snap.claim_id)
        if prior is None or (snap.created_at, snap.id) > (prior.created_at, prior.id):
            latest[snap.claim_id] = snap
    output = []
    for claim in claims:
        snap = latest.get(claim.id)
        category, reason = (classify(snap.findings, snap.verification, snap.calculation)
                            if snap else (REVIEW, "no_authorized_audit_snapshot"))
        output.append({
            "claim_id": claim.id, "claim_reference": claim.claim_reference,
            "provider_code": claim.provider_code, "service_date": claim.service_date.isoformat(),
            "claimed_amount": str(claim.claimed_amount), "currency": claim.currency,
            "outcome": category, "reason": reason,
            "audit_snapshot_id": snap.id if snap else "",
            "policy_fingerprint": snap.policy_fingerprint if snap else "",
            "review_state": "PROPOSED_NOT_FINAL",
        })
    return output


FIELDS = ("claim_id", "claim_reference", "provider_code", "service_date",
          "claimed_amount", "currency", "outcome", "reason",
          "audit_snapshot_id", "policy_fingerprint", "review_state")


def export_csv(rows, outcome):
    if outcome not in KINDS:
        raise ValueError("unsupported outcome")
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=FIELDS, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        if row["outcome"] != outcome:
            continue
        # Prevent untrusted claim text from becoming an Excel formula.
        escaped = {key: ("'" + str(row.get(key, ""))
                         if str(row.get(key, "")).lstrip().startswith(("=", "+", "-", "@"))
                         else str(row.get(key, ""))) for key in FIELDS}
        writer.writerow(escaped)
    return ("\ufeff" + output.getvalue()).encode("utf-8")


def summarize(rows):
    counter = Counter(row["outcome"] for row in rows)
    return {"total": len(rows), "counts": {kind: counter[kind] for kind in KINDS},
            "decision_status": "review_only_not_payout_authorization"}
