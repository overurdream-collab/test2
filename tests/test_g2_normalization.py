from mcias.ingestion.normalization import normalize_fields, decimal_value, iso_date

def test_normalization_preserves_original_and_decimal_precision():
    values={"amount":"1,234.50","date":"10/10/2026"}
    result=normalize_fields(values,numeric_fields=("amount",),date_fields=("date",))
    assert result["original"]==values
    assert result["normalized"]=={"amount":"1234.50","date":"2026-10-10"}
    assert not result["errors"]

def test_invalid_numeric_is_not_silently_zero():
    result=normalize_fields({"amount":"NaN"},numeric_fields=("amount",))
    assert "amount" in result["errors"]
    assert "amount" not in result["normalized"]

def test_ambiguous_date_is_not_guessed():
    assert iso_date("10-10-26") is None
