#!/usr/bin/env python3
"""Classify original 1170 matches conservatively. Not a substitute for call-chain review.
Input: untouched GitHub Actions artifact matches.csv from run 39330289038.
Output: classified_matches.csv retaining every input row and an immutable key.
"""
import csv,collections,re,sys
from pathlib import Path
source=Path(sys.argv[1] if len(sys.argv)>1 else "matches.csv")
out=Path(sys.argv[2] if len(sys.argv)>2 else "classified_matches.csv")
rows=list(csv.DictReader(source.open(encoding="utf-8")))
result=[]
for number,row in enumerate(rows,1):
    kind,path,s=row["kind"],row["file"],row["source"]
    istest=path.startswith(("tests/","scripts/check_")) or "/test_" in path or path.startswith("conftest")
    if istest:
        category,reason="test_or_fixture","Test/fixture or acceptance-check source; not independent production consumer"
    elif path.startswith("alembic/") or (path.endswith("models.py") and "AuditLog" in s):
        category,reason="documentation_or_reference","Migration or model declaration, not direct business writer"
    elif kind=="AuditLog_constructor":
        category,reason="direct_audit_consumer","Direct AuditLog constructor; inspect enclosing transaction"
    elif kind in ("write_event","record_outcome_independent") and re.search(r"\b(?:return\s+)?(?:write_event|record_outcome_independent)\s*\(",s) and not s.startswith("def "):
        category,reason="indirect_audit_consumer","Explicit shared writer call"
    elif kind=="transaction_boundary":
        related=any(t in path for t in ("auth.py","tenant.py","governance.py","reference_service.py","audit_policy_lifecycle.py","audit_writer.py","audit_service.py","claim_batches.py","ingestion/reprocessing.py","ingestion/orchestrator.py","ingestion/review.py","mfa","denial_events.py","workspace_api.py","intelligence_service_g8.py","reference_api.py","governance_g6.py","audit_policy_api.py"))
        category,reason=("transaction_owner_candidate","Related module, full enclosing path requires inspection") if related else ("non_audit_transaction_candidate","Commit or rollback alone is not proof of Audit association")
    elif kind in ("direct_SQL","multiline_SQL"):
        category,reason="direct_audit_SQL","Raw audit table query or mutation, verify execution context"
    elif re.search(r"\b(?:getattr|importlib|exec_driver_sql|text\s*\()\b",s):
        category,reason="dynamic_unresolved","Dynamic or SQL dispatch not resolvable from one extracted line"
    else:
        category,reason="textual_reference","Import, reference, declaration or text match; not a proven writer from this line"
    followup=category in ("transaction_owner_candidate","dynamic_unresolved","non_audit_transaction_candidate") or ("action=action" in s and category=="direct_audit_consumer") or ('"g6_" + kind' in s) or ('"g8_task_" + kind' in s)
    result.append({**{"match_id":f'{row["ref"]}:{row["file"]}:{row["line"]}:{number}'},**row,"classification":category,"reason":reason,"requires_full_source_review":"YES" if followup else "NO"})
assert len(rows)==1170 and len(result)==1170
assert collections.Counter(x["ref"] for x in rows)=={"main":255,"pr25":323,"pr28":292,"pr29_baseline":300}
with out.open("w",encoding="utf-8",newline="") as f:
    w=csv.DictWriter(f,fieldnames=list(result[0]));w.writeheader();w.writerows(result)
print("Classified all source rows",len(result),dict(collections.Counter(x["classification"] for x in result)))
print("Full-source review candidates",sum(x["requires_full_source_review"]=="YES" for x in result))
