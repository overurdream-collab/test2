"""Synthetic scoring equivalence: exact tariff identity and Decimal monetary equality."""
from scripts.contract_benchmark_scoring import count_matches


def test_equivalent_decimal_spellings_are_the_same_tariff():
    assert count_matches({("tariffs", "H2:CONSULT", "7000")},
                         {("tariffs", "H2:CONSULT", "7000.00")}) == (1, 0, 0)
    assert count_matches({("tariffs", "H2:CONSULT", "7000.00")},
                         {("tariffs", "H2:CONSULT", "7000")}) == (1, 0, 0)


def test_different_amount_is_never_matched():
    assert count_matches({("tariffs", "H2:CONSULT", "7000")},
                         {("tariffs", "H2:CONSULT", "7001")}) == (0, 1, 1)


def test_different_provider_or_service_is_never_matched():
    for wrong in ("H3:CONSULT", "H2:XRAY"):
        assert count_matches({("tariffs", "H2:CONSULT", "7000")},
                             {("tariffs", wrong, "7000.00")}) == (0, 1, 1)


def test_original_c28_4_case_scoring_recomputed():
    gold = [
        {("tariffs", "H1:CONSULT", "5000")},
        {("cost_sharing", "copay_percent", "20")},
        {("tariffs", "H2:CONSULT", "7000")},
        set(),
    ]
    predicted = [
        {("tariffs", "H1:CONSULT", "5000")},
        {("cost_sharing", "copay_percent", "20")},
        {("tariffs", "H2:CONSULT", "7000.00")},
        set(),
    ]
    scores = [count_matches(g, p) for g, p in zip(gold, predicted)]
    assert scores == [(1, 0, 0), (1, 0, 0), (1, 0, 0), (0, 0, 0)]
    assert tuple(sum(row[i] for row in scores) for i in range(3)) == (3, 0, 0)
