"""Decimal-equivalent comparisons for SYN contract benchmark metrics only.

Does not transform model output, evidence verification or finance amounts.
"""
from decimal import Decimal, InvalidOperation


def _score_key(item):
    section, logical_key, amount = item
    # Exact section and identity matching; only the numeric representation is normalized.
    if not isinstance(amount, str):
        raise ValueError("scored amount must be a validated numeric string")
    try:
        value = Decimal(amount)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("scored amount must be decimal") from exc
    if not value.is_finite():
        raise ValueError("scored amount must be finite")
    return section, logical_key, value


def count_matches(gold, predicted):
    """Return TP, FP, FN after lossless Decimal comparison of validated triples."""
    gold_values = {_score_key(x) for x in gold}
    predicted_values = {_score_key(x) for x in predicted}
    return (len(gold_values & predicted_values),
            len(predicted_values - gold_values),
            len(gold_values - predicted_values))
