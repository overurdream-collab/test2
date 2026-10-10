"""G7 preparatory snapshot reporting; no production export endpoints."""
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from io import BytesIO
import json
from openpyxl import Workbook

class ReportBlocked(ValueError):
    pass

def freeze_report(rows, *, organization_id, version, allowed_sensitive_fields=()):
    if not organization_id or version<1:
        raise ReportBlocked("tenant and positive version required")
    frozen=[]
    for row in rows:
        if row.get("organization_id")!=organization_id:
            raise ReportBlocked("T20 cross-tenant export denied")
        if row.get("sensitive_fields") and not set(row["sensitive_fields"]).issubset(set(allowed_sensitive_fields)):
            raise ReportBlocked("T20 unauthorized sensitive field export")
        if row.get("verification_status")!="verified":
            raise ReportBlocked("held or unverified snapshot cannot be approved report line")
        try:
            claimed=Decimal(str(row["claimed"]))
            payable=Decimal(str(row["payable"]))
            deduction=Decimal(str(row["deduction"]))
        except (InvalidOperation, KeyError, TypeError) as exc:
            raise ReportBlocked("invalid report amounts") from exc
        if not all(x.is_finite() and x>=0 for x in (claimed,payable,deduction)):
            raise ReportBlocked("invalid report amount")
        if claimed!=payable+deduction:
            raise ReportBlocked("independent report reconciliation failed")
        frozen.append({"snapshot_id":str(row["snapshot_id"]),
                       "source_values":json.loads(json.dumps(row["source_values"],ensure_ascii=False)),
                       "claimed":str(claimed),"deduction":str(deduction),
                       "payable":str(payable),"currency":str(row["currency"])})
    payload={"organization_id":organization_id,"version":version,"rows":frozen,
             "total_claimed":str(sum((Decimal(x["claimed"]) for x in frozen),Decimal(0))),
             "total_deduction":str(sum((Decimal(x["deduction"]) for x in frozen),Decimal(0))),
             "total_payable":str(sum((Decimal(x["payable"]) for x in frozen),Decimal(0)))}
    payload["sha256"]=sha256(json.dumps(payload,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    return payload

def excel_bytes(frozen):
    book=Workbook()
    sheet=book.active
    sheet.title="Frozen claims"
    sheet.append(["Snapshot","Source columns JSON","Claimed","Deduction","Payable","Currency"])
    for item in frozen["rows"]:
        # Formula injection protection applies to untrusted source fields.
        source=json.dumps(item["source_values"],ensure_ascii=False,sort_keys=True)
        if source.startswith(("=","+","-","@")):
            source="'"+source
        sheet.append([item["snapshot_id"],source,item["claimed"],item["deduction"],
                      item["payable"],item["currency"]])
    out=BytesIO()
    book.save(out)
    return out.getvalue()
