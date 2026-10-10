from datetime import date
from mcias.models_reference import ContractVersion
from mcias.reference import reference_fingerprint

def test_contract_review_fingerprint_changes_with_effective_dates():
    contract=ContractVersion(id="fixture",organization_id="org",provider_code="P",version=1,
        effective_from=date(2027,1,1),effective_until=date(2028,1,1),precedence=0)
    first=reference_fingerprint(contract)
    contract.effective_until=date(2029,1,1)
    assert reference_fingerprint(contract)!=first
