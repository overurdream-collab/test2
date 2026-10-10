"""G8 evidence-first local analytics. No fraud verdicts or financial write-backs.

Every metric comes from a frozen, SHA-verified G7 report and an immutable G4
claim entry; monetary values remain Decimal and currencies never mix.
"""
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json

from mcias.reporting_g7 import verify_snapshot, ReportBlocked

class IntelligenceBlocked(ValueError):
    pass

DIMENSIONS = frozenset({"provider", "service", "month"})
INDICATORS = frozenset({"hold_rate", "provider_claimed_share"})
SOURCE = "g7_frozen_report_snapshots"
ENGINE_VERSION = "g8-deterministic-1"

def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")

def digest(value):
    return sha256(canonical(value)).hexdigest()

def dec(value):
    try:
        amount = Decimal(str(value))
    except (ValueError, TypeError, InvalidOperation) as exc:
        raise IntelligenceBlocked("invalid numeric evidence") from exc
    if not amount.is_finite() or amount < 0:
        raise IntelligenceBlocked("invalid numeric evidence")
    return amount

def as_string(value):
    return format(value, "f")

def pct(numerator, denominator):
    if not denominator:
        return None
    return as_string(numerator * Decimal(100) / denominator)

def validate_config(config):
    if type(config) is not dict or set(config) != {
        "source", "indicator", "dimension", "threshold_percent", "min_group_size"
    }:
        raise IntelligenceBlocked("unsupported indicator schema or source configuration")
    if config["source"] != SOURCE:
        raise IntelligenceBlocked("data source not approved")
    if config["indicator"] not in INDICATORS or config["dimension"] not in DIMENSIONS:
        raise IntelligenceBlocked("unsupported indicator or dimension")
    if config["indicator"] == "provider_claimed_share" and config["dimension"] != "provider":
        raise IntelligenceBlocked("provider share requires provider grouping")
    threshold = dec(config["threshold_percent"])
    if threshold > 100:
        raise IntelligenceBlocked("percent threshold out of range")
    count = config["min_group_size"]
    if type(count) is not int or not 5 <= count <= 1000:
        raise IntelligenceBlocked("group privacy minimum must be an integer from 5 to 1000")
    return {
        "source": SOURCE,
        "indicator": config["indicator"],
        "dimension": config["dimension"],
        "threshold_percent": as_string(threshold),
        "min_group_size": count,
    }

def assemble(reports, claims):
    """Return stripped rows, source hashes; reject mismatched snapshot/claim joins.

    No beneficiary identifiers, claim references, diagnosis or source_values
    cross this boundary. This is a snapshot-bound in-memory cohort, not a
    live aggregation of multiple report versions.
    """
    if not 1 <= len(reports) <= 12:
        raise IntelligenceBlocked("select between one and twelve frozen reports")
    organization = reports[0].organization_id
    seen_batches, seen_claims = set(), set()
    results, sources = [], []
    for report in reports:
        if report.organization_id != organization or report.batch_id in seen_batches:
            raise IntelligenceBlocked("cross-tenant or duplicate-batch snapshots")
        seen_batches.add(report.batch_id)
        try:
            verify_snapshot(report)
        except ReportBlocked as exc:
            raise IntelligenceBlocked("G7 report fingerprint invalid") from exc
        sources.append({"report_id": report.id, "version": report.version,
                        "fingerprint": report.fingerprint,
                        "source_sha256": report.dataset["source_sha256"]})
        expected = report.summary["by_currency"]
        actual = defaultdict(lambda: {"claimed": Decimal(0), "payable": Decimal(0),
                                      "deductions": Decimal(0), "approved_count": 0,
                                      "held_count": 0})
        for row in report.dataset["rows"]:
            if row["claim_id"] in seen_claims:
                raise IntelligenceBlocked("duplicate claim across report sources")
            seen_claims.add(row["claim_id"])
            claim = claims.get(row["claim_id"])
            if (claim is None or claim.organization_id != organization
                or claim.batch_id != report.batch_id
                or claim.extracted_record_id != row["source_record_id"]
                or claim.currency != row["currency"]
                or dec(claim.claimed_amount) != dec(row["claimed"])):
                raise IntelligenceBlocked("G4/G7 financial or provenance mismatch")
            state = row["state"]
            if state not in {"approved", "held"}:
                raise IntelligenceBlocked("unsupported frozen claim status")
            claimed = dec(row["claimed"])
            if state == "approved":
                payable = dec(row["payable"])
                deductions = dec(row["deduction"])
                if claimed != payable + deductions:
                    raise IntelligenceBlocked("G7 approved reconciliation mismatch")
            else:
                if row["payable"] is not None or row["deduction"] is not None:
                    raise IntelligenceBlocked("held item cannot contain approved payable")
                payable = deductions = Decimal(0)
            if not getattr(claim, "provider_code", None) or not getattr(claim, "service_code", None):
                raise IntelligenceBlocked("missing G4 service/provider dimension")
            period = claim.service_date.strftime("%Y-%m")
            item = {"claim_id": claim.id, "currency": claim.currency,
                    "provider": claim.provider_code, "service": claim.service_code,
                    "month": period, "state": state, "claimed": claimed,
                    "payable": payable, "deductions": deductions}
            results.append(item)
            amounts = actual[claim.currency]
            amounts["claimed"] += claimed
            if state == "approved":
                amounts["approved_count"] += 1
                amounts["payable"] += payable
                amounts["deductions"] += deductions
            else:
                amounts["held_count"] += 1
        # Independent aggregate reconciliation; report fingerprints alone are insufficient.
        for currency, values in expected.items():
            values_actual = actual.pop(currency, None)
            if values_actual is None:
                raise IntelligenceBlocked("missing currency data for report")
            if (values_actual["claimed"] != dec(values["claimed"])
                or values_actual["payable"] != dec(values["payable"])
                or values_actual["deductions"] != dec(values["deductions"])
                or values_actual["approved_count"] != values["approved_count"]
                or values_actual["held_count"] != values["held_count"]):
                raise IntelligenceBlocked("G7 frozen totals do not reconcile")
        if actual or len(report.dataset["rows"]) != report.summary["total_claims"]:
            raise IntelligenceBlocked("unmatched report currency or claim count")
    if len(results) > 10000:
        raise IntelligenceBlocked("cohort exceeds unapproved engineering data limit")
    return sorted(results, key=lambda row: row["claim_id"]), sources

def aggregate(rows, dimension="provider", min_group_size=5):
    if dimension not in DIMENSIONS or type(min_group_size) is not int or not 5 <= min_group_size <= 1000:
        raise IntelligenceBlocked("unsupported dimension or privacy floor")
    buckets = defaultdict(list)
    for row in rows:
        buckets[(row["currency"], row[dimension])].append(row)
    merged = defaultdict(list)
    suppressed_groups = 0
    for (currency, key), values in buckets.items():
        if len(values) < min_group_size:
            merged[(currency, "__suppressed__")].extend(values)
            suppressed_groups += 1
        else:
            merged[(currency, key)].extend(values)
    groups = []
    for (currency, key), values in sorted(merged.items()):
        claimed = sum((v["claimed"] for v in values), Decimal(0))
        payable = sum((v["payable"] for v in values), Decimal(0))
        deductions = sum((v["deductions"] for v in values), Decimal(0))
        held = sum(v["state"] == "held" for v in values)
        groups.append({"currency": currency, "dimension": dimension,
                       "group": key, "suppressed": key == "__suppressed__",
                       "count": len(values), "approved_count": len(values)-held,
                       "held_count": held, "claimed": as_string(claimed),
                       "payable": as_string(payable), "deductions": as_string(deductions),
                       "hold_rate_percent": pct(Decimal(held), Decimal(len(values)))})
    return {"engine": ENGINE_VERSION, "dimension": dimension,
            "denominator_count": len(rows), "suppressed_groups": suppressed_groups,
            "groups": groups, "interpretation": "descriptive_only_no_clinical_or_fraud_verdict"}

def signals(rows, config):
    cfg = validate_config(config)
    dimension = cfg["dimension"]
    threshold = dec(cfg["threshold_percent"])
    minimum = cfg["min_group_size"]
    grouped = aggregate(rows, dimension, minimum)
    totals = defaultdict(lambda: {"count": 0, "claimed": Decimal(0), "held": 0})
    for row in rows:
        currency = row["currency"]
        totals[currency]["count"] += 1
        totals[currency]["claimed"] += row["claimed"]
        totals[currency]["held"] += (row["state"] == "held")
    findings = []
    for item in grouped["groups"]:
        if item["suppressed"] or item["count"] < minimum:
            continue
        currency = item["currency"]
        cohort = totals[currency]
        if cohort["count"] < 2*minimum:
            continue  # Small baselines cannot justify signals
        if cfg["indicator"] == "hold_rate":
            numerator = Decimal(item["held_count"])
            denominator = Decimal(item["count"])
            base_num = Decimal(cohort["held"])
            base_den = Decimal(cohort["count"])
        else:
            numerator = dec(item["claimed"])
            denominator = cohort["claimed"]
            base_num = Decimal(item["count"])
            base_den = Decimal(cohort["count"])
        if not denominator:
            continue
        observed = numerator * Decimal(100) / denominator
        if observed <= threshold:
            continue
        findings.append({
            "status": "review_only", "indicator": cfg["indicator"],
            "currency": currency, "dimension": dimension, "group": item["group"],
            "observed_percent": as_string(observed),
            "threshold_percent": cfg["threshold_percent"],
            "sample_count": item["count"], "cohort_count": cohort["count"],
            "numerator": as_string(numerator), "denominator": as_string(denominator),
            "baseline_percent": pct(base_num, base_den),
            "evidence_quality": "synthetic_or_unapproved_until_review",
            "interpretation": "review_signal_not_fraud_or_clinical_judgment",
        })
    return {"engine": ENGINE_VERSION, "status": "review_only",
            "indicator": cfg["indicator"], "config_fingerprint": digest(cfg),
            "sources_count": len(rows),
            "findings": findings[:100], "suppressed_groups": grouped["suppressed_groups"],
            "false_positive_review_required": True,
            "no_automatic_deductions": True}

def simulate(rows, reduction_percent):
    """Pure what-if on *approved* payables. Does not modify policies or DB."""
    percent = dec(reduction_percent)
    if percent > 100:
        raise IntelligenceBlocked("scenario percent exceeds 100")
    by_currency = defaultdict(lambda: {"payable": Decimal(0), "approved_count": 0})
    for row in rows:
        if row["state"] == "approved":
            by_currency[row["currency"]]["payable"] += row["payable"]
            by_currency[row["currency"]]["approved_count"] += 1
    output = []
    for currency, vals in sorted(by_currency.items()):
        original = vals["payable"]
        hypothetical = original * (Decimal(100) - percent) / Decimal(100)
        output.append({"currency": currency, "approved_count": vals["approved_count"],
                       "baseline_payable": as_string(original),
                       "hypothetical_payable": as_string(hypothetical),
                       "hypothetical_difference": as_string(original - hypothetical)})
    return {"engine": ENGINE_VERSION, "mode": "review_only_hypothetical",
            "assumption": {"approved_payable_reduction_percent": as_string(percent)},
            "by_currency": output, "policy_change_authorized": False,
            "financial_writeback": False}
