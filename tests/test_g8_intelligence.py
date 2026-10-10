"""G8 T14/T15/T19 synthetic golden data and false-positive controls."""
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
import pytest

from mcias.reporting_g7 import fingerprint
from mcias.intelligence_g8 import (
    IntelligenceBlocked, SOURCE, validate_config,
    assemble, aggregate, signals, simulate, digest,
)

def cohort(total=20, held_a=8, held_b=2):
    claims, data = {}, []
    for n in range(total):
        provider = "A" if n < total // 2 else "B"
        idx = n if provider == "A" else n-total//2
        held = idx < (held_a if provider == "A" else held_b)
        money = "100"
        payable = None if held else "80"
        deduction = None if held else "20"
        cid = f"synthetic-{n}"
        claims[cid] = SimpleNamespace(
            id=cid, organization_id="organization-1", batch_id="batch-1",
            extracted_record_id="raw-"+cid, currency="YER",
            claimed_amount=Decimal(money), provider_code=provider,
            service_code="LAB" if provider=="A" else "PHARMACY",
            service_date=date(2026, 1, 1+n%28),
            beneficiary_token="private-beneficiary-"+cid)
        data.append({"claim_id":cid,"source_record_id":"raw-"+cid,
                     "state":"held" if held else "approved",
                     "currency":"YER","claimed":money,
                     "payable":payable,"deduction":deduction,
                     "source_values":{"diagnosis":"private-diagnosis"},
                     "source_locator":{"row":n+2},
                     "beneficiary_token":"private-beneficiary-"+cid})
    claimed=Decimal(total)*100
    held_count=held_a+held_b
    approved=total-held_count
    summary={"total_claims":total,"by_currency":{"YER":{
        "claimed":format(claimed,"f"),
        "payable":format(Decimal(approved)*80,"f"),
        "deductions":format(Decimal(approved)*20,"f"),
        "approved_claimed":format(Decimal(approved)*100,"f"),
        "held_claimed":format(Decimal(held_count)*100,"f"),
        "approved_count":approved,"held_count":held_count}}}
    dataset={"schema":1,"organization_id":"organization-1",
             "batch_id":"batch-1","source_sha256":"a"*64,"rows":data}
    report=SimpleNamespace(id="report-1",organization_id="organization-1",
                           batch_id="batch-1",version=1,
                           dataset=dataset,summary=summary,
                           fingerprint=fingerprint(dataset,summary))
    return report, claims

def normalized():
    report, claims=cohort()
    return assemble([report],claims)

def configuration(metric="hold_rate",dimension="provider",threshold="60"):
    return {"source":SOURCE,"indicator":metric,"dimension":dimension,
            "threshold_percent":threshold,"min_group_size":5}

def test_t14_review_only_statistical_signal_with_denominators():
    rows,sources=normalized()
    result=signals(rows,configuration())
    assert result["status"]=="review_only"
    assert result["no_automatic_deductions"] is True
    assert result["false_positive_review_required"]
    assert len(result["findings"])==1
    finding=result["findings"][0]
    assert finding["group"]=="A" and finding["sample_count"]==10
    assert finding["cohort_count"]==20 and finding["numerator"]=="8"
    assert finding["denominator"]=="10" and finding["observed_percent"]=="80"
    assert finding["baseline_percent"]=="50"
    assert finding["interpretation"]=="review_signal_not_fraud_or_clinical_judgment"
    assert len(sources)==1 and sources[0]["fingerprint"]==cohort()[0].fingerprint
    assert "private-diagnosis" not in str(result)
    assert "private-beneficiary-" not in str(result)

def test_t14_threshold_and_negative_controls_stop_false_positives():
    rows,_=normalized()
    assert signals(rows,configuration(threshold="80"))["findings"]==[]
    assert signals(rows,configuration(threshold="100"))["findings"]==[]
    assert signals(rows,configuration(threshold="0"))["findings"]
    assert signals(rows,configuration("provider_claimed_share",threshold="50"))["findings"]==[]
    found=signals(rows,configuration("provider_claimed_share",threshold="40"))
    assert len(found["findings"])==2

def test_t14_small_group_and_small_cohort_do_not_emit_alerts():
    rows,_=normalized()
    sliced=[r for r in rows if r["provider"]=="A"][:5]
    assert signals(sliced,configuration(threshold="0"))["findings"]==[]
    sparse=rows[:]
    for n,row in enumerate(sparse[:9]):
        row["provider"]="RARE"+str(n)
    overview=aggregate(sparse,"provider",5)
    assert overview["suppressed_groups"]>=1
    assert any(item["group"]=="__suppressed__" and item["suppressed"]
               for item in overview["groups"])
    assert all(item["group"] not in {"RARE"+str(i) for i in range(9)}
               for item in overview["groups"])
    assert all("RARE" not in str(f) for f in signals(sparse,configuration(threshold="0"))["findings"])

def test_t14_descriptive_month_service_aggregation_and_reconciliation():
    rows,_=normalized()
    by_service=aggregate(rows,"service",5)
    assert sum(Decimal(i["claimed"]) for i in by_service["groups"])==Decimal(2000)
    assert sum(Decimal(i["payable"]) for i in by_service["groups"])==Decimal(800)
    by_month=aggregate(rows,"month",5)
    assert by_month["groups"][0]["group"]=="2026-01"
    assert by_month["denominator_count"]==20

def test_what_if_is_nonbinding_and_not_a_financial_mutation():
    rows,_=normalized()
    initial=[dict(x) for x in rows]
    outcome=simulate(rows,"25")
    assert outcome["mode"]=="review_only_hypothetical"
    assert outcome["financial_writeback"] is False
    assert outcome["policy_change_authorized"] is False
    assert outcome["by_currency"][0]["baseline_payable"]=="800"
    assert outcome["by_currency"][0]["hypothetical_payable"]=="600"
    assert outcome["by_currency"][0]["hypothetical_difference"]=="200"
    assert rows==initial
    with pytest.raises(IntelligenceBlocked):
        simulate(rows,"101")
    with pytest.raises(IntelligenceBlocked):
        simulate(rows,"NaN")

def test_t15_unapproved_source_fields_expressions_or_small_group_are_denied():
    for update in [
        {"source":"arbitrary_sql"}, {"indicator":"execute_sql"},
        {"dimension":"diagnosis"}, {"min_group_size":1},
        {"threshold_percent":"101"}, {"threshold_percent":"NaN"},
    ]:
        cfg={**configuration(),**update}
        with pytest.raises(IntelligenceBlocked):
            validate_config(cfg)
    with pytest.raises(IntelligenceBlocked):
        validate_config({**configuration(),"sql":"SELECT * FROM patients"})

def test_g8_cross_tenant_duplicate_batch_and_forged_source_denied():
    report,claims=cohort()
    changed={**claims}
    first=next(iter(claims))
    changed[first]=SimpleNamespace(**{**vars(claims[first]),"organization_id":"other"})
    with pytest.raises(IntelligenceBlocked,match="provenance"):
        assemble([report],changed)
    with pytest.raises(IntelligenceBlocked,match="duplicate-batch"):
        assemble([report,report],claims)
    report.dataset["rows"][0]["claimed"]="999"
    with pytest.raises(IntelligenceBlocked,match="fingerprint"):
        assemble([report],claims)

def test_g8_frozen_aggregate_tampering_and_bad_original_amounts_denied():
    report,claims=cohort()
    report.summary["by_currency"]["YER"]["payable"]="999"
    report.fingerprint=fingerprint(report.dataset,report.summary)
    with pytest.raises(IntelligenceBlocked,match="reconcile"):
        assemble([report],claims)
    report,claims=cohort()
    cid=next(iter(claims))
    claims[cid].claimed_amount=Decimal("999")
    with pytest.raises(IntelligenceBlocked,match="provenance"):
        assemble([report],claims)

def test_t15_k_anonymity_applies_to_summary_and_simulation_even_one_claim():
    rows,_=normalized()
    rare=rows[:1]
    summary=aggregate(rare,"provider",5)
    assert len(summary["groups"])==1
    group=summary["groups"][0]
    assert group["suppressed"] and group["count"]==1
    assert group["claimed"] is None and group["payable"] is None
    assert group["hold_rate_percent"] is None
    hypothetical=simulate(rare,"25")
    assert hypothetical["by_currency"]==[]  # this single synthetic claim is held
    approved=[row for row in rows if row["state"]=="approved"][:1]
    result=simulate(approved,"25")
    assert result["by_currency"][0]["privacy_suppressed"] is True
    assert result["by_currency"][0]["baseline_payable"] is None
    assert result["by_currency"][0]["hypothetical_payable"] is None

def test_t15_malformed_configuration_types_fail_closed():
    for dimension in ({}, [], 1):
        with pytest.raises(IntelligenceBlocked):
            validate_config({**configuration(),"dimension":dimension})
    for metric in ({}, [], 1):
        with pytest.raises(IntelligenceBlocked):
            validate_config({**configuration(),"indicator":metric})
