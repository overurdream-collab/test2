from decimal import Decimal
import pytest
from mcias.claim_normalization import normalize, ClaimValidationError

GOOD={"claim_reference":"C-1","beneficiary_token":"opaque-1","provider_code":"H1",
      "service_code":"CONSULT","service_date":"2026-10-10","claimed_amount":"123.4500","currency":"YER"}

def test_g4_normalization_exact_values():
    result=normalize(GOOD)
    assert result["claimed_amount"]==Decimal("123.4500")
    assert result["service_date"].isoformat()=="2026-10-10"

@pytest.mark.parametrize("key,value",[
    ("claimed_amount","NaN"),("claimed_amount","Infinity"),("claimed_amount","-1"),
    ("claimed_amount","1.00001"),("claimed_amount","1e99"),
    ("currency","yer"),("currency","USDT"),("service_date","10/10/2026"),
    ("beneficiary_token",""),("provider_code","bad provider\t")])
def test_g4_fail_closed_invalid_values(key,value):
    with pytest.raises(ClaimValidationError):
        normalize({**GOOD,key:value})

def test_g4_missing_required_fields():
    with pytest.raises(ClaimValidationError,match="missing required"):
        normalize({"claim_reference":"C"})
