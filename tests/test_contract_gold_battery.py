"""Twenty synthetic, source-anchored clauses across all eight MCIAS sections.

These are a frozen validator gold sanity battery, NOT predictions from an AI
model and NOT a Precision/Recall benchmark. Real-model metrics live separately.
No PHI or institutional contract/prices are used.
"""
from hashlib import sha256
import pytest
from mcias.contract_intelligence import make_source_blocks, validate_candidates

# id, verbatim quote, section, logical_key, rule_type, typed value,
# provider_code, service_code, currency
CASES = [["SYN-EN-T1","H1 CONSULT tariff 5000 YER effective 2026-01-01 to 2027-01-01.","tariffs","H1:CONSULT","amount","5000","H1","CONSULT","YER"],["SYN-EN-T2","H2 CONSULT tariff 7000 YER effective 2026-01-01 to 2027-01-01.","tariffs","H2:CONSULT","amount","7000","H2","CONSULT","YER"],["SYN-EN-T3","H3 XRAY tariff 1250 YER effective 2026-01-01 to 2027-01-01.","tariffs","H3:XRAY","amount","1250","H3","XRAY","YER"],["SYN-MIX-T4","المستشفى H4 service MRI price 9300 YER effective 2026-01-01 to 2027-01-01.","tariffs","H4:MRI","amount","9300","H4","MRI","YER"],["SYN-MIX-T5","المستشفى H5 service LAB price 850 YER effective 2026-01-01 to 2027-01-01.","tariffs","H5:LAB","amount","850","H5","LAB","YER"],["SYN-EN-T6","Provider P6 SERVICE PHARM tariff 42.50 USD effective 2026-01-01 to 2027-01-01.","tariffs","P6:PHARM","amount","42.50","P6","PHARM","USD"],["SYN-AR-C1","نسبة تحمل العيادات 20% من 2026-01-01 حتى 2027-01-01.","cost_sharing","copay_percent","percentage","20",None,None,None],["SYN-EN-C2","Patient copay is 10.5% from 2026-01-01 until 2027-01-01.","cost_sharing","copay_percent","percentage","10.5",None,None,None],["SYN-MIX-C3","نسبة copay هي 15% from 2026-01-01 until 2027-01-01.","cost_sharing","copay_percent","percentage","15",None,None,None],["SYN-EN-B1","The covered beneficiary count is 1000 from 2026-01-01 until 2027-01-01.","beneficiaries","beneficiary_count","count","1000",None,None,None],["SYN-AR-B2","عدد المستفيدين 2500 من 2026-01-01 إلى 2027-01-01.","beneficiaries","beneficiary_count","count","2500",None,None,None],["SYN-EN-D1","The contract duration is one year starting 2026-01-01 and ending 2027-01-01.","contracts","duration","duration",None,None,None,None],["SYN-AR-D2","تسري الاتفاقية من 2026-01-01 وحتى 2027-01-01.","contracts","contract.term","text",None,None,None,None],["SYN-EN-E1","Travel abroad is excluded from coverage from 2026-01-01 to 2027-01-01.","exclusions","outside_country","exclusion",None,None,None,None],["SYN-AR-E2","لا تشمل التغطية العلاج خارج الدولة من 2026-01-01 إلى 2027-01-01.","exclusions","outside_country","exclusion",None,None,None,None],["SYN-EN-A1","MRI requires prior approval effective 2026-01-01 until 2027-01-01.","approvals","MRI_prior_approval","approval",None,None,None,None],["SYN-AR-A2","يشترط الحصول على موافقة مسبقة للجراحة من 2026-01-01 حتى 2027-01-01.","approvals","surgery_prior_approval","approval",None,None,None,None],["SYN-EN-P1","H8 is an in-network provider from 2026-01-01 to 2027-01-01.","providers","H8_network","text",None,"H8",None,None],["SYN-AR-CAT1","الفئة الذهبية تشمل الخدمات الداخلية من 2026-01-01 إلى 2027-01-01.","categories","gold_category","text",None,None,None,None],["SYN-EN-CAT2","Silver category covers outpatient services from 2026-01-01 to 2027-01-01.","categories","silver_category","text",None,None,None,None]]

def evaluate(candidate, quote, record_id="SYN-SOURCE"):
    blocks = make_source_blocks([{
        "id": record_id, "locator": {"kind": "page", "index": 1},
        "values": {"text": quote},
    }])
    return validate_candidates([candidate], blocks,
        source_sha256=sha256(quote.encode()).hexdigest(),
        model_id="SYN-NOT-A-REAL-MODEL", model_revision="NO-MODEL-INFERENCE")[0]


@pytest.mark.parametrize("sample", CASES, ids=[x[0] for x in CASES])
def test_gold_clause_types_are_accepted_only_with_verbatim_source(sample):
    identity, quote, section, key, kind, amount, provider, service, currency = sample
    assert identity.startswith("SYN-")
    assert "2026-01-01" in quote and "2027-01-01" in quote
    candidate = {
        "record_id": identity, "quote": quote, "section": section,
        "logical_key": key, "rule_type": kind, "amount": amount,
        "provider_code": provider, "service_code": service, "currency": currency,
        "effective_from": "2026-01-01", "effective_until": "2027-01-01",
    }
    result = evaluate(candidate, quote, identity)
    assert result["validation_errors"] == [], (identity, result["validation_errors"])
    assert result["evidence_status"] == "verified_source_anchor"
    assert result["status"] == "DRAFT_ONLY"


@pytest.mark.parametrize("mutation,issue", [
    ({"record_id": "SYN-FORGED"}, "source_record_missing"),
    ({"section": "financial_transfer"}, "unsupported_section"),
    ({"rule_type": "execute_sql"}, "unsupported_rule_type"),
    ({"amount": "7000"}, "numeric_not_in_source"),
    ({"provider_code": "H2"}, "tariff_identity_incomplete"),
    ({"service_code": "XRAY"}, "tariff_identity_incomplete"),
    ({"currency": "USD"}, "currency_not_in_source"),
    ({"logical_key": "H1:XRAY"}, "tariff_identity_incomplete"),
    ({"effective_from": None}, "missing_effective_from"),
    ({"effective_from": "2027-01-01", "effective_until": "2026-01-01"}, "invalid_effective_range"),
], ids=[
    "wrong_source","unknown_section","code_as_rule","invented_amount",
    "wrong_provider","wrong_service","wrong_currency","wrong_key",
    "missing_start","reversed_period",
])
def test_ten_adversarial_mutations_never_verify_as_trusted(mutation, issue):
    quote = CASES[0][1]
    candidate = {
        "record_id": "SYN-SOURCE", "quote": quote, "section": "tariffs",
        "logical_key": "H1:CONSULT", "rule_type": "amount", "amount": "5000",
        "provider_code": "H1", "service_code": "CONSULT", "currency": "YER",
        "effective_from": "2026-01-01", "effective_until": "2027-01-01",
    }
    candidate.update(mutation)
    result = evaluate(candidate, quote)
    assert issue in result["validation_errors"], (mutation, result["validation_errors"])
    assert result["evidence_status"] == "needs_human_review"
    assert result["status"] == "DRAFT_ONLY"
