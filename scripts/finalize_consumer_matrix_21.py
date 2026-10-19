#!/usr/bin/env python3
"""Close only 21 previously placeholder consumer-function rows using traced source paths.
All evidence is on immutable source refs and DG-001 line anchors.
"""
import csv,json,pathlib,collections
p=pathlib.Path("docs/shared_audit_semantic_evidence/audit_consumer_matrix.csv")
rows=list(csv.DictReader(p.open(encoding="utf-8",newline="")))
openrows=[r for r in rows if r["status"]=="UNRESOLVED"]
assert len(openrows) in (21,0), f"Expected 21 or zero already-closed matrix rows, found {len(openrows)}"
if not openrows:
    print("PASS: consumer matrix already contains zero unresolved rows; no rewrite needed")
    raise SystemExit(0)
for r in openrows:
    path,fn=r["file"],r["function"]
    if path=="mcias/models.py":
        r.update(status="NOT_APPLICABLE",entry_point="ORM model declaration",call_chain="AuditLog ORM class declaration; no runtime invocation",business_owner="N/A",audit_owner="N/A",failure_behavior="N/A",phase2a_compatibility="NOT_APPLICABLE",privacy_assessment="ORM schema; no event value written",risk="NONE")
    elif path=="mcias/audit_writer.py" and fn=="<module>":
        r.update(status="NOT_APPLICABLE",entry_point="Python module docstring",call_chain="Writer module docstring mention only; actual functions separately inventoried",business_owner="N/A",audit_owner="N/A",failure_behavior="N/A",phase2a_compatibility="NOT_APPLICABLE",privacy_assessment="No stored data in docstring",risk="NONE")
    elif path=="scripts/check_contracts_acceptance.py":
        r.update(status="NOT_APPLICABLE",entry_point="Acceptance test script",call_chain="Synthetic test literal only",business_owner="Test fixture",audit_owner="Test fixture",failure_behavior="Test assertion",phase2a_compatibility="NOT_APPLICABLE",privacy_assessment="Synthetic-only",risk="NONE")
    elif path=="mcias/governance_g6.py" and fn=="append_event":
        r.update(status="VERIFIED",entry_point="HTTP governance_g6_api.py:add_event -> service append_event",call_chain="governance_g6_api.add_event -> governance_g6.append_event(kind in PERMISSIONS) -> GovernanceEvent add+flush:142-143 -> AuditLog(g6_+kind):144-147 -> db.commit:148",event_name="g6_propose|g6_approve|g6_hold|g6_reject|g6_object|g6_request_reaudit|g6_link_reaudit",event_source="SERVER ENUM (seven values)",actor_provenance="Resolved user in governance_g6_api.actor_for; service actor.active, organization_id and permission checks",tenant_provenance="case.organization_id == actor.organization_id, 65-69",business_owner="governance_g6.append_event db session",audit_owner="same db session in append_event",transaction_sequence="add case/event, flush, add AuditLog, commit; API rollback on GovernanceBlocked",failure_behavior="Raised errors route to API rollback; no independent denial write",phase2a_compatibility="NEEDS DETAIL MAPPING",privacy_assessment="reason_code syntax validated, but needs finite enum; case_id/new_case_id filtered by Phase2A",risk="POTENTIAL")
    elif path=="mcias/intelligence_service_g8.py" and fn=="_append_event":
        r.update(status="VERIFIED",entry_point="HTTP intelligence_g8_api.py:test_draft/activate_tested/deactivate",call_chain="G8 API -> test_task(kind=tested):142 / activate_task(activated):164 / deactivate_task(deactivated):175 -> _append_event -> AnalysisTaskEvent add+flush:121-125 -> AuditLog:126-129 -> commit:130",event_name="g8_task_tested|g8_task_activated|g8_task_deactivated",event_source="SERVER LITERALS (three call sites)",actor_provenance="G8 API resolves user; service _authorize checks active, org and permission",tenant_provenance="_task filters AnalysisTaskVersion.organization_id to actor.organization_id",business_owner="intelligence_service_g8._append_event",audit_owner="same db session in _append_event",transaction_sequence="task event add; flush; audit add; commit; API _execute rollback on domain errors",failure_behavior="API _execute rollback on IntelligenceBlocked; no independent denied logging",phase2a_compatibility="NEEDS DETAIL MAPPING",privacy_assessment="task_id/task_fingerprint omitted by Phase2A detail allowlist",risk="POTENTIAL")
    elif path=="mcias/reference_service.py" and fn=="_audit":
        r.update(status="VERIFIED",entry_point="HTTP reference_api.py business endpoints; direct service callers",call_chain="reference_api.<operation> -> reference_service.<create_draft/add_tariff/create_category/enroll/...> -> _audit -> AuditLog add -> service db.commit; source main reference_service.py:11, create_draft:46, add_tariff and enroll",event_name="Caller provided: contract_draft_created|tariff_added|beneficiary_category_created|beneficiary_enrolled (+ other reference actions)",event_source="Service-supplied action (not request free-text in confirmed callers)",actor_provenance="Reference service actor argument from endpoint resolved user",tenant_provenance="actor.organization_id and resource tenant guard; per-caller checks required",business_owner="reference_service operation db session",audit_owner="same db session via _audit",transaction_sequence="business add+flush -> _audit add -> service commit; API _perform rollback on ReferenceConflict/IntegrityError",failure_behavior="Domain conflicts become HTTP409, currently not central denial audit in main",phase2a_compatibility="NEEDS DETAIL MAPPING",privacy_assessment="provider_code/contract_id/category_id fields not in Phase2A detail allowlist",risk="POTENTIAL")
    elif path=="mcias/denial_events.py" and fn=="record_denial_after_rollback":
        r.update(status="VERIFIED",entry_point="PR28 HTTP get_db dependency exception handler",call_chain="app.get_db catches AuthorizationDenied -> session.rollback:64 -> denial_events.record_denial_after_rollback:27 -> record_outcome_independent -> independent Session.commit",event_name="Caller supplied structured denial action",event_source="AuthorizationDenied fields, validated by shared writer",actor_provenance="trusted denied.audit_actor_id (rejects missing)",tenant_provenance="trusted denied.audit_organization_id (rejects missing)",business_owner="app.get_db request Session",audit_owner="record_outcome_independent independent Session",transaction_sequence="rollback business before independent audit commit; exception re-raised",failure_behavior="Audit failure propagates; does not claim success",phase2a_compatibility="NEEDS EVENT REGISTRY CROSS-CHECK",privacy_assessment="reason_code allowlist, action/resource checked by writer",risk="POTENTIAL")
    else:
        raise AssertionError("Unexpected unresolved consumer matrix row: "+r["consumer_id"]+" "+path+":"+fn)
assert not any(r["status"]=="UNRESOLVED" for r in rows)
with p.open("w",encoding="utf-8",newline="") as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
summary_p=pathlib.Path("docs/shared_audit_semantic_evidence/semantic_closure_summary.json")
s=json.loads(summary_p.read_text())
s["consumer_matrix_review"]={"total_entries":len(rows),"remaining_unresolved":0,"targeted_traced_or_marked_nonoperational":21,"statuses":dict(collections.Counter(r["status"] for r in rows)),"note":"Entries are per SHA/function, not distinct real-world consumers; VERIFIED is static trace only, not operational acceptance."}
summary_p.write_text(json.dumps(s,ensure_ascii=False,indent=2)+"\n")
print(json.dumps(s["consumer_matrix_review"],indent=2))
