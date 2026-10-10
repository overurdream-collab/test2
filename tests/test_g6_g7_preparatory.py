"""Synthetic G6/G7 preparatory regression tests; not gate acceptance."""
from io import BytesIO
import pytest
from openpyxl import load_workbook
from mcias.g6_decision_planning import DecisionProposal,GovernanceBlocked,plan_decision,objection_impact
from mcias.g7_snapshot_reporting import freeze_report,excel_bytes,ReportBlocked

def proposal():
    return DecisionProposal("org1","maker",("s1","s2","s3"),("s2",),
                            ("review","head"),("source-1",))

def test_t11_separation_of_duties():
    with pytest.raises(GovernanceBlocked,match="cannot approve"):
        plan_decision(proposal(),actor_id="maker",stage="head",
                      verified_snapshot_ids=("s1","s3"))

def test_t12_partial_approval_excludes_held():
    result=plan_decision(proposal(),actor_id="reviewer",stage="review",
                         verified_snapshot_ids=("s1","s2","s3"))
    assert result["approved_ids"]==("s1","s3")
    assert result["held_ids"]==("s2",)
    assert result["version"]==1

def test_t10_objection_reaudits_only_affected_items():
    result=objection_impact(original_snapshot_ids=("s1","s2","s3"),
                            objection_evidence_id="new-doc",affected_snapshot_ids=("s2",))
    assert result["reaudit_required_ids"]==("s2",)
    assert result["unchanged_ids"]==("s1","s3")
    with pytest.raises(GovernanceBlocked):
        objection_impact(original_snapshot_ids=("s1",),objection_evidence_id="",
                         affected_snapshot_ids=("s1",))

def row(**changes):
    value=dict(organization_id="org1",snapshot_id="s1",source_values={"original_col":"=SUM(1,2)"},
               claimed="100.00",deduction="20.00",payable="80.00",
               currency="YER",verification_status="verified")
    value.update(changes)
    return value

def test_t13_frozen_report_is_stable_after_source_changes():
    original=row()
    first=freeze_report([original],organization_id="org1",version=1)
    original["payable"]="10.00"
    assert first["rows"][0]["payable"]=="80.00"
    assert first["sha256"]==freeze_report([row()],organization_id="org1",version=1)["sha256"]

def test_t18_original_source_columns_preserved_in_excel():
    report=freeze_report([row()],organization_id="org1",version=1)
    sheet=load_workbook(BytesIO(excel_bytes(report)),read_only=True).active
    assert '"original_col": "=SUM(1,2)"' in sheet["B2"].value

def test_t20_sensitive_and_cross_tenant_exports_denied():
    with pytest.raises(ReportBlocked,match="cross-tenant"):
        freeze_report([row(organization_id="org2")],organization_id="org1",version=1)
    with pytest.raises(ReportBlocked,match="sensitive"):
        freeze_report([row(sensitive_fields=["diagnosis"])],organization_id="org1",version=1)
    with pytest.raises(ReportBlocked,match="reconciliation"):
        freeze_report([row(payable="81")],organization_id="org1",version=1)
