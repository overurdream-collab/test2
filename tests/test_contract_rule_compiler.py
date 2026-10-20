"""Synthetic typed diagnostic test suite; absolutely no executable rules."""
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
import pytest
from mcias.contract_rule_compiler import compile_diagnostic, compare_diagnostic, CompilationBlocked

def point(**kw):
    d=dict(id="SYN-point",organization_id="org",status="approved",source_sha256="a"*64,
           section="tariffs",rule_type="amount",logical_key="H1:CONSULT",
           provider_code="H1",service_code="CONSULT",currency="YER",
           amount=Decimal(5000),version=1,effective_from=date(2026,1,1),
           effective_until=date(2028,1,1))
    d.update(kw)
    return SimpleNamespace(**d)

def verify(ast,**kwargs):
    d=dict(organization_id="org",provider_code="H1",service_code="CONSULT",
           service_date=date(2026,6,1),currency="YER",
           g3_tariff=Decimal(5000),g5_tariff=Decimal(5000))
    d.update(kwargs)
    return compare_diagnostic(ast,**d)

def test_approved_tariff_compiles_only_to_inert_diagnostic():
    ast=compile_diagnostic(point())
    assert ast["execution_authorized"] is False
    assert verify(ast)["status"]=="CONSISTENT"

def test_provider_tariff_conflict_and_missing_policy():
    ast=compile_diagnostic(point())
    assert verify(ast,g3_tariff=Decimal(7000))["status"]=="CONFLICT"
    assert verify(ast,g5_tariff=None)["status"]=="INDETERMINATE"

def test_half_open_service_dates_preserve_historical_prices():
    ast=compile_diagnostic(point(),end_override=date(2026,7,1))
    assert verify(ast,service_date=date(2026,6,30))["status"]=="CONSISTENT"
    assert verify(ast,service_date=date(2026,7,1))["status"]=="NOT_APPLICABLE"

def test_tenant_provider_currency_never_cross_apply():
    ast=compile_diagnostic(point())
    assert verify(ast,organization_id="org-other")["status"]=="INDETERMINATE"
    assert verify(ast,provider_code="H2")["status"]=="NOT_APPLICABLE"
    assert verify(ast,currency="USD")["status"]=="INDETERMINATE"

def test_draft_missing_sha_and_ambiguous_exclusion_blocked():
    for p in (point(status="draft"),point(source_sha256=None),point(section="exclusions"),
              point(effective_from=None)):
        with pytest.raises(CompilationBlocked):
            compile_diagnostic(p)

def test_percentage_only_compares_to_supplied_policy_without_activation():
    ast=compile_diagnostic(point(section="cost_sharing",rule_type="percentage",
        logical_key="copay_percent",provider_code=None,service_code=None,
        currency=None,amount=Decimal(20)))
    assert verify(ast,g5_copay=None)["status"]=="INDETERMINATE"
    assert verify(ast,g5_copay=Decimal(20))["status"]=="CONSISTENT"
    assert verify(ast,g5_copay=Decimal(30))["status"]=="CONFLICT"

def test_forged_ast_fingerprint_and_execution_flag_rejected():
    ast=compile_diagnostic(point())
    ast["expected"]="1"
    assert verify(ast)["status"]=="INDETERMINATE"
    ast=compile_diagnostic(point())
    ast["execution_authorized"]=True
    assert verify(ast)["status"]=="INDETERMINATE"

def test_malicious_non_finite_values_blocked():
    for n in (float("inf"),Decimal("NaN"),Decimal(-1)):
        with pytest.raises(CompilationBlocked):
            compile_diagnostic(point(amount=n))
