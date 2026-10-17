"""Actual common-input subset comparison: A1 rules vs existing G5 Decimal engine.

Strict synthetic-only, 6 independently hand-labeled cases with explicit G5
claim-level approved test ceiling and matching itemized A1 references.
Cannot represent an institution-approved live G5 policy; see report caveats.
"""
import argparse
from copy import deepcopy
from decimal import Decimal
import json
from pathlib import Path
import resource
from time import perf_counter
from statistics import mean

from mcias.agents.invoice_integrity import analyze
from mcias.audit_engine import AuditPolicy, evaluate
from tests.a1.synthetic_cases import base, ref


def cases():
    for name in ("clean", "inflated_price", "legitimate_discount",
                 "unauthorized_fee", "authorized_fee", "inflated_quantity"):
        b = deepcopy(base())
        line = b["invoice"]["items"][0]
        line["quantity"] = "1"
        line["unit_price"] = line["line_total"] = "10"
        ceiling = Decimal("10")
        expected = False
        if name == "inflated_price":
            expected = True
            line["unit_price"] = line["line_total"] = "15"
        elif name == "legitimate_discount":
            line["unit_price"] = line["line_total"] = "8"
        elif name in ("unauthorized_fee", "authorized_fee"):
            b["invoice"]["items"].append({
                "id": "F1", "code": "ADMIN", "unit": "fee", "kind": "fee",
                "quantity": "1", "unit_price": "5", "line_total": "5",
                "source": ref("synthetic-fee-source")})
            if name == "unauthorized_fee":
                expected = True
            else:
                ceiling = Decimal("15")
                b["contracts"][0]["allowed_fees"] = [{
                    "code": "ADMIN", "unit": "fee", "currency": "YER", "unit_price": "5"}]
        elif name == "inflated_quantity":
            expected = True
            ceiling = Decimal("20")  # independently authored synthetic per-claim G5 ceiling
            line["quantity"] = "2"
            line["line_total"] = "20"
        if name != "inflated_quantity":
            line["quantity"] = "1"
        b["documents"][0]["items"][0]["quantity"] = "1"
        total = sum((Decimal(x["line_total"]) for x in b["invoice"]["items"]), Decimal("0"))
        b["invoice"]["stated_total"] = b["claim"]["amount"] = str(total)
        b["run_id"] = "synthetic-comparator-" + name
        yield name, b, expected, ceiling


def metrics(rows, key):
    tp = sum(x["gold_review"] and x[key] for x in rows)
    fp = sum(not x["gold_review"] and x[key] for x in rows)
    fn = sum(x["gold_review"] and not x[key] for x in rows)
    tn = sum(not x["gold_review"] and not x[key] for x in rows)
    return {"TP":tp,"FP":fp,"FN":fn,"TN":tn,
            "precision":tp/(tp+fp) if tp+fp else None,
            "recall":tp/(tp+fn) if tp+fn else None}


def evaluate_common_subset():
    rows, a1_times, g5_times = [], [], []
    for name, bundle, expected, approved_test_ceiling in cases():
        start = perf_counter()
        a1 = analyze(bundle)
        a1_times.append((perf_counter()-start)*1000)
        policy = AuditPolicy(policy_id="synthetic-g5-comparator-v1", currency="YER",
            rounding="HALF_UP", precision=4,
            order=("exclusion","tariff","cap","copay"),
            copay_percent=Decimal("0"), cap=None, exclusion=Decimal("0"),
            tariff=approved_test_ceiling, approved=True)
        start = perf_counter()
        g5 = evaluate(Decimal(bundle["claim"]["amount"]), "YER", policy,
            eligible=True, evidence_complete=True,
            source_id="synthetic-source", contract_id="synthetic-contract",
            beneficiary_enrollment_id="synthetic-enrollment")
        g5_times.append((perf_counter()-start)*1000)
        result = {
            "case":name, "gold_review":expected,
            "a1_review":a1["finding_status"]=="REVIEW",
            "a1_types":[x["finding_type"] for x in a1["findings"]
                        if x["finding_status"] == "REVIEW"],
            "g5_tariff_deduction":next(step["deduction"] for step in
                                      g5["deductions"] if step["rule"]=="tariff"),
            "g5_review_proxy":any(Decimal(x["deduction"])>0 for x in g5["deductions"]),
            "synthetic_policy_tariff_ceiling":str(approved_test_ceiling),
        }
        assert (result["a1_review"] == expected), f"A1 comparator case mismatch {name}"
        rows.append(result)
    return {"evaluation": "SYNTHETIC_SIX_CASE_COMMON_SUBSET_G5_ENGINE_ONLY",
            "warning": "G5 policy is synthetic and pre-authorized for this experiment only. "
            "This tests mcias.audit_engine.evaluate, NOT G5 end-to-end authorization, "
            "not clinical accuracy. G5 provides aggregate deductions not fraud findings. "
            "G5 flag is a proxy (nonzero deduction); broader invoices are incomparable.",
            "gold_source": "scripts/compare_a1_g5_baseline.py::cases (human authored)",
            "a1":metrics(rows,"a1_review"), "g5_proxy":metrics(rows,"g5_review_proxy"),
            "mean_a1_milliseconds":mean(a1_times), "mean_g5_milliseconds":mean(g5_times),
            "peak_process_rss_kib":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            "rows":rows}


if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--output",default="a1-g5-comparison.json")
    args=ap.parse_args()
    report=evaluate_common_subset()
    Path(args.output).write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k!="rows"},ensure_ascii=False))
