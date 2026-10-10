"""G9 bounded synthetic analytics performance probe.

No patient data, database access or actual on-prem SLA certification is implied.
"""
import argparse
import json
import statistics
import time
from datetime import date
from decimal import Decimal

from mcias.intelligence_g8 import aggregate, simulate, signals, SOURCE, digest

def fake_rows(count: int):
    if type(count) is not int or not 10 <= count <= 10000:
        raise ValueError("synthetic volume must be 10..10000 claims")
    rows=[]
    for i in range(count):
        held=i%7==0
        claimed=Decimal("100.50")
        rows.append({
            "claim_id": "synthetic-" + str(i),
            "provider": "synthetic_provider_" + str(i % 25),
            "service": "synthetic_service_" + str(i % 8),
            "month": f"2026-{1+(i%12):02d}",
            "currency": "YER" if i%2 else "USD",
            "state": "held" if held else "approved",
            "claimed": claimed,
            "payable": Decimal(0) if held else Decimal("90.45"),
            "deductions": Decimal(0) if held else Decimal("10.05"),
        })
    return rows

def profile(count=1000, repeats=3):
    if type(repeats) is not int or not 1 <= repeats <= 10:
        raise ValueError("repeat count outside bounds")
    rows=fake_rows(count)
    elapsed=[]
    checks=[]
    for _ in range(repeats):
        start=time.perf_counter()
        summary=aggregate(rows,"provider",5)
        sim=simulate(rows,"10")
        scan=signals(rows,{
            "source":SOURCE,
            "indicator":"hold_rate","dimension":"provider",
            "threshold_percent":"70","min_group_size":5,
        })
        elapsed.append(round((time.perf_counter()-start)*1000,3))
        # Ensure results are deterministic regardless of wall-clock samples.
        checks.append(digest({"summary":summary,"scenario":sim,"signals":scan}))
    if len(set(checks))!=1:
        raise ValueError("G9 performance probe produced non-deterministic results")
    return {"schema":"mcias-g9-synthetic-benchmark-v1",
            "dataset":"synthetic_only_no_patient_data",
            "claim_count":count, "repetitions":repeats,
            "median_elapsed_ms":statistics.median(elapsed),
            "worst_elapsed_ms":max(elapsed),
            "result_digest":checks[0],
            "threshold_status":"NO_INSTITUTION_APPROVED_SLA",
            "production_performance_accepted":False}

def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument("--claims",type=int,default=1000)
    parser.add_argument("--repeats",type=int,default=3)
    args=parser.parse_args(argv)
    print(json.dumps(profile(args.claims,args.repeats),sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
