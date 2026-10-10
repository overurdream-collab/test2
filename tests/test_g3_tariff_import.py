import pytest
from mcias.tariff_import import preview_csv, TariffImportError

def test_tariff_csv_preview_has_row_provenance():
    result=preview_csv(b"service_code,amount,currency\nA,123.4500,YER\nB,broken,YER\n")
    assert result["accepted"]==[{"row":2,"service_code":"A","amount":"123.4500","currency":"YER"}]
    assert result["errors"]==[{"row":3,"reason":"invalid amount precision or currency"}]
    assert not result["complete"]
    assert result["rows_seen"]==2

def test_tariff_csv_duplicate_and_precision_rejected():
    result=preview_csv(b"service_code,amount,currency\nA,1,YER\nA,2,YER\nB,1.12345,YER\n")
    assert len(result["errors"])==2

def test_tariff_csv_malformed_headers_rejected():
    with pytest.raises(TariffImportError):
        preview_csv(b"amount,service_code,currency\n1,A,YER\n")

def test_tariff_csv_nan_infinity_rejected():
    result=preview_csv(b"service_code,amount,currency\nA,NaN,YER\nB,Infinity,YER\n")
    assert not result["accepted"]
    assert len(result["errors"])==2
