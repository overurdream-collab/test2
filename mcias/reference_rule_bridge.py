"""Read-only G3/G5 bridge for historically valid, independently approved input points.

This does NOT compile natural-language clauses, create payment instructions,
replace the authoritative G3 provider tariff, or authorize new financial policies.
Any unknown applicable clause fails closed to review rather than fake PASS.
"""
from decimal import Decimal
from sqlalchemy import select, func, or_
from mcias.models_reference_points import ReferencePoint, ReferencePointClosure

MAX_ACTIVE_REFERENCES = 100
CHECKABLE = {"tariffs", "cost_sharing", "exclusions"}


def reconcile(db, claim, policy, g3_tariff):
    """Return a bounded, evidence-linked comparison at the *service date*.

    A missing supplementary reference point is not a missing G3/G5 policy.
    Existing signed G3/G5 references remain authoritative until a separately
    accepted, institution-signed compilation/activation path exists.
    """
    result = {"status": "pass", "reason": "g3_g5_authoritative",
              "service_date": claim.service_date.isoformat(),
              "provider_code": claim.provider_code,
              "service_code": claim.service_code,
              "points": [], "unresolved": []}
    q = (select(ReferencePoint, ReferencePointClosure.effective_until)
         .outerjoin(ReferencePointClosure, ReferencePointClosure.point_id == ReferencePoint.id)
         .where(
             ReferencePoint.organization_id == claim.organization_id,
             ReferencePoint.status == "approved",
             ReferencePoint.effective_from <= claim.service_date,
             func.coalesce(ReferencePointClosure.effective_until, ReferencePoint.effective_until) > claim.service_date,
             or_(ReferencePoint.provider_code.is_(None),
                 ReferencePoint.provider_code == claim.provider_code),
             or_(ReferencePoint.service_code.is_(None),
                 ReferencePoint.service_code == claim.service_code),
         )
         .order_by(ReferencePoint.section, ReferencePoint.logical_key, ReferencePoint.version)
         .limit(MAX_ACTIVE_REFERENCES + 1))
    rows = db.execute(q).all()
    if len(rows) > MAX_ACTIVE_REFERENCES:
        return {**result, "status": "hold",
                "reason": "too_many_applicable_points",
                "unresolved": ["reference_set_requires_bounded_review"]}
    seen = set()
    for p, end in rows:
        unique_scope = (p.section, p.rule_type, p.provider_code, p.service_code)
        # Tariff identity must be exact; global 'tariff' values are unsafe.
        recorded = {"point_id": p.id, "version": p.version,
                    "section": p.section, "logical_key": p.logical_key,
                    "effective_from": p.effective_from.isoformat(),
                    "effective_until": (end or p.effective_until).isoformat(),
                    "source_sha256": p.source_sha256}
        result["points"].append(recorded)
        if p.section in CHECKABLE and unique_scope in seen:
            result["unresolved"].append("ambiguous_" + p.section + "_versions")
            continue
        seen.add(unique_scope)
        if p.section == "tariffs":
            if (p.rule_type != "amount"
                or p.provider_code != claim.provider_code
                or p.service_code != claim.service_code
                or p.logical_key != claim.provider_code + ":" + claim.service_code
                or not g3_tariff or p.currency != claim.currency
                or p.currency != g3_tariff.currency
                or p.amount != g3_tariff.amount
                or p.amount != policy.tariff):
                result["unresolved"].append("tariff_point_mismatch_g3_g5")
        elif p.section == "cost_sharing":
            if (p.rule_type != "percentage" or p.amount != policy.copay_percent
                or p.logical_key not in {"copay_percent",
                        claim.provider_code + ":copay_percent",
                        claim.provider_code + ":" + claim.service_code + ":copay_percent"}):
                result["unresolved"].append("cost_sharing_needs_policy_mapping")
        elif p.section == "exclusions":
            if (p.rule_type != "amount" or p.amount != policy.exclusion
                or p.currency != claim.currency
                or p.logical_key not in {"exclusion_amount",
                        claim.provider_code + ":exclusion_amount",
                        claim.provider_code + ":" + claim.service_code + ":exclusion_amount"}):
                result["unresolved"].append("exclusion_needs_policy_mapping")
        else:
            # e.g. benefit limits, prior approvals, class-based coverage and
            # geographic exclusions require typed policy interpreters.
            result["unresolved"].append("uncompiled_" + p.section + "_point")
    if result["unresolved"]:
        result["status"] = "hold"
        result["reason"] = "approved_input_point_requires_review"
    return result
