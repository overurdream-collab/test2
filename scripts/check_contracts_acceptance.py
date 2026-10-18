"""DG-001 contracts-only browser acceptance. No mocks, no demo, fail closed."""
import json, os, time, traceback
from pathlib import Path
from uuid import uuid4
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from playwright.sync_api import sync_playwright, expect
from mcias.models import Organization, User, Role, Permission, RolePermission, UserRole, MFAFactor
from mcias.security import hash_password
from mcias.mfa import generate_totp
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

OUT=Path(".e2e-output/contracts-acceptance")
OUT.mkdir(parents=True,exist_ok=True)
results={"scope":"contracts-only","synthetic":True,"import":"BLOCKED","add":"BLOCKED","edit":"BLOCKED","rbac":"BLOCKED","evidence":[]}
password="synthetic_contract_only_pass"
dburl=os.environ["MCIAS_E2E_DATABASE_URL"]
assert dburl.split("/")[-1].endswith("_e2e"), "Only test PostgreSQL allowed"
assert os.environ["MCIAS_ENVIRONMENT"]=="development"
engine=create_engine(dburl)
tag=uuid4().hex[:10]
secrets={label:os.urandom(20) for label in ('writer','reader')}
with Session(engine) as db:
    org=Organization(name="SYN CONTRACTS "+tag)
    db.add(org); db.flush()
    role=Role(code="contract_writer_"+tag)
    readonly=Role(code="contract_reader_"+tag)
    db.add_all([role,readonly]); db.flush()
    for code in ["profile.read","reference.read","reference.write","ingestion.read","ingestion.upload","medical_fields.text.read"]:
        perm=db.scalar(select(Permission).where(Permission.code==code))
        if perm is None:
            perm=Permission(code=code); db.add(perm); db.flush()
        db.add(RolePermission(role_id=role.id,permission_id=perm.id))
        if code in ("profile.read","reference.read"):
            db.add(RolePermission(role_id=readonly.id,permission_id=perm.id))
    admin=db.scalar(select(Role).where(Role.code=="super_admin"))
    if admin is None:
        admin=Role(code="super_admin"); db.add(admin); db.flush()
    users={}
    for label,assigned in [("writer",role),("reader",readonly)]:
        user=User(organization_id=org.id,username="syn-"+label+"-"+tag,password_hash=hash_password(password))
        db.add(user); db.flush()
        db.add(UserRole(user_id=user.id,role_id=assigned.id))
        db.add(UserRole(user_id=user.id,role_id=admin.id))
        users[label]=user.username
        # Both synthetic accounts hold super_admin; real auth requires MFA for each.
        if label in secrets:
            nonce=os.urandom(12)
            encrypted=AESGCM(bytes.fromhex(os.environ["MCIAS_MFA_ENCRYPTION_KEY"])).encrypt(nonce,secrets[label],user.id.encode())
            db.add(MFAFactor(user_id=user.id,encrypted_secret=nonce+encrypted,enabled=True))
    organization_id = org.id
    db.commit()

def record(page,name):
    page.screenshot(path=str(OUT/(name+".png")),full_page=True)
    results["evidence"].append(name+".png")

def login(page,label):
    page.goto("http://127.0.0.1:8000/login")
    page.get_by_label("اسم المستخدم",exact=True).fill(users[label])
    page.get_by_label("كلمة المرور",exact=True).fill(password)
    page.get_by_label("رمز التحقق (إلزامي للإدارة)",exact=True).fill(generate_totp(secrets[label],int(time.time())//30))
    with page.expect_response(lambda response: response.url.endswith("/api/v1/auth/login")) as auth:
        page.get_by_role("button",name="تسجيل الدخول بأمان",exact=True).click()
    assert auth.value.status == 200, "Actual login rejected: HTTP " + str(auth.value.status)
    assert auth.value.json().get("access_token"), "Login response has no session token"
    expect(page.get_by_role("heading",name="مرحبًا بك في MCIAS")).not_to_be_visible(timeout=12000)
    # Session bearer token is MEMORY-ONLY: page.goto would reload and erase it.
    page.evaluate('''() => {
        history.pushState({}, "", "/admin/input-register");
        window.dispatchEvent(new PopStateEvent("popstate"));
    }''')
    expect(page.get_by_role("button",name="العقود",exact=True)).to_be_visible(timeout=12000)
    record(page,"00-contracts-authenticated-"+label)
    return auth.value.json()["access_token"]

try:
    with sync_playwright() as pw:
        browser=pw.chromium.launch()
        page=browser.new_page(viewport={"width":1440,"height":950})
        try:
            writer_token=login(page,"writer")
            for name in ("استيراد ملف (رفع المصدر)","إضافة","تعديل"):
                expect(page.get_by_role("button",name=name,exact=True)).to_be_visible()
            record(page,"01-contracts-controls")
            # Unauthorized operator must not be allowed to mutate.
            other=browser.new_page()
            try:
                reader_token=login(other,"reader")
                for name in ("استيراد ملف (رفع المصدر)","إضافة","تعديل"):
                    expect(other.get_by_role("button",name=name,exact=True)).to_be_disabled()
                record(other,"02-reader-denied")
                results["rbac"]="PASS"
            finally: other.close()
            # G2 import: original synthetic PDF, exact extraction + HUMAN preview required.
            from reportlab.pdfgen import canvas
            synthetic=OUT/"synthetic-contract.pdf"
            c=canvas.Canvas(str(synthetic))
            c.drawString(50,750,"SYNTHETIC CONTRACT PROVIDER SYN_H1")
            c.drawString(50,725,"Service SYN_001 Price 125.00 USD effective 2026-11-01")
            c.save()
            page.get_by_role("button",name="استيراد ملف (رفع المصدر)",exact=True).click()
            expect(page.locator("#drawer")).to_be_visible()
            page.locator("#drawer input[type=file]").set_input_files(str(synthetic))
            with page.expect_response(lambda r: "/api/v1/ingestion/uploads?" in r.url and r.request.method == "POST") as upload:
                page.get_by_role("button",name="رفع الملف",exact=True).click()
            assert upload.value.status == 200, "G2 upload HTTP " + str(upload.value.status)
            # Chromium may evict the response body after UI navigation. Assert
            # server status and the semantic inspect control the UI adds only
            # when the response includes a valid source document identifier.
            results["g2_upload"] = {"http_status":upload.value.status}
            inspect = page.get_by_role("button",name="فحص بيان مصدر العقد من G2",exact=True)
            expect(inspect).to_be_enabled(timeout=10000)
            record(page,"03-upload-result")
            with page.expect_response(lambda r: "/api/v1/ingestion/documents/" in r.url and r.url.endswith("/manifest")) as manifest_response:
                inspect.click()
            assert manifest_response.value.status == 200, "G2 manifest HTTP " + str(manifest_response.value.status)
            # Keep the real GET status and rendered browser evidence; do not
            # depend on CDP retaining a response body after rendering.
            results["g2_manifest_http_status"] = manifest_response.value.status
            expect(page.locator("#drawer")).to_contain_text("manifest",timeout=10000)
            record(page,"04-g2-source-manifest")
            # Strict gate: a manifest is NOT an editable review of extracted contract clauses.
            preview=page.locator("#drawer [data-testid='g2-contract-fields-preview']")
            # G2 manifest and contract candidate preview are sequential async requests.
            # A synchronous .count() here races the second request and reports a false absence.
            try:
                expect(preview).to_be_visible(timeout=15000)
            except AssertionError:
                results["import"]="BLOCKED"
                results["first_missing_function"]="Contract preview not rendered after G2 manifest; inspect server response"
                record(page,"04-preview-not-rendered")
                raise
            expect(preview).to_contain_text("SYN_001")
            expect(page.get_by_role("button",name="تأكيد الحقول وإنشاء مسودة",exact=True)).to_be_visible()
            record(page,"04-g2-human-preview")
            from mcias.models_input_clauses import InputClause
            with Session(engine) as db:
                assert db.scalar(select(InputClause).where(InputClause.organization_id==organization_id,
                    InputClause.section=="contracts")) is None, "Source preview created draft without human confirmation"
            preview.get_by_label("القيمة بعد التصحيح",exact=True).fill("126.00")
            record(page,"05-human-correction-before-confirm")
            # An unauthorized reader cannot confirm even by direct HTTP POST.
            denied = page.request.post("http://127.0.0.1:8000/api/v1/input-clauses/contracts/documents/invalid/confirm",
                headers={"Authorization":"Bearer "+reader_token},
                data={"source_record_id":"SYN","service_code":"SYN_001","corrected_value":"126.00",
                      "effective_from":"2026-11-01","human_confirmed":True})
            assert denied.status == 403, "Unauthorized user reached confirmation route"
            preview.locator("input[type=checkbox]").check()
            with page.expect_response(lambda r: "/api/v1/input-clauses/contracts/documents/" in r.url and r.url.endswith("/confirm")) as confirmation:
                page.get_by_role("button",name="تأكيد الحقول وإنشاء مسودة",exact=True).click()
            assert confirmation.value.status == 201, "Confirmed draft HTTP " + str(confirmation.value.status)
            with Session(engine) as db:
                rows=db.scalars(select(InputClause).where(InputClause.organization_id==organization_id,
                    InputClause.section=="contracts")).all()
                assert len(rows)==1, "Expected precisely one confirmed contract draft"
                point=rows[0]
                assert point.structured_value["original_amount"]=="125.00"
                assert point.structured_value["amount"]=="126.00"
                assert point.structured_value["human_confirmed"] is True
                assert point.source_document_id and point.source_locator.get("kind")=="page"
                results["db_evidence"]={"draft_id":point.id,"version":point.version,
                    "original_amount":"125.00","corrected_amount":"126.00","status":"draft",
                    "source_document_id":point.source_document_id}
            record(page,"06-confirmed-contract-draft")
            results["source_review_preview"]="PASS"
            results["import"]="PASS"
            # Manual Add is G3 ContractVersion, not a generic InputClause entry.
            from mcias.models_reference import ContractVersion
            page.locator("#drawer").get_by_role("button",name="إغلاق",exact=True).click()
            page.get_by_role("button",name="إضافة",exact=True).click()
            form=page.locator("#drawer [data-testid='manual-g3-contract-draft']")
            expect(form).to_be_visible()
            record(page,"07-manual-add-empty")
            contract_number="SYN-CONTRACT-"+tag
            form.get_by_label("رقم العقد",exact=True).fill(contract_number)
            form.get_by_label("رمز مقدم الخدمة",exact=True).fill("SYN_HOSP")
            form.get_by_label("تاريخ البداية",exact=True).fill("2026-11-01")
            form.get_by_label("تاريخ النهاية",exact=True).fill("2027-11-01")
            form.get_by_label("معلومات العقد",exact=True).fill("Synthetic medical provider contract — draft only")
            record(page,"08-manual-add-filled")
            with Session(engine) as db:
                assert not db.scalars(select(ContractVersion).where(
                    ContractVersion.organization_id==organization_id,
                    ContractVersion.contract_number==contract_number)).first(), "Premature contract persistence"
            with page.expect_response(lambda r: r.url.endswith("/api/v1/reference/contracts") and r.request.method=="POST") as create_response:
                form.get_by_role("button",name="تنفيذ الطلب",exact=True).click()
            assert create_response.value.status==201, "G3 manual contract HTTP "+str(create_response.value.status)
            expect(form).to_contain_text(contract_number,timeout=10000)
            record(page,"09-manual-add-saved-and-read")
            with Session(engine) as db:
                matches=db.scalars(select(ContractVersion).where(
                    ContractVersion.organization_id==organization_id,
                    ContractVersion.contract_number==contract_number)).all()
                assert len(matches)==1, "G3 PostgreSQL contract write/readback mismatch"
                contract=matches[0]
                assert contract.provider_code=="SYN_HOSP"
                assert contract.effective_from.isoformat()=="2026-11-01"
                assert contract.effective_until.isoformat()=="2027-11-01"
                assert contract.contract_notes=="Synthetic medical provider contract — draft only"
                assert contract.status=="draft" and contract.authorization_id is None
                assert contract.version==1
                results["manual_add_db_evidence"]={"id":contract.id,"contract_number":contract.contract_number,
                    "organization_id":organization_id,"provider_code":contract.provider_code,
                    "effective_from":contract.effective_from.isoformat(),
                    "effective_until":contract.effective_until.isoformat(),
                    "status":contract.status,"version":contract.version,
                    "authorization_id":contract.authorization_id,"notes":contract.contract_notes}
            # Authorized duplicate is rejected; a reader cannot create a contract even via HTTP.
            manual_payload={"contract_number":contract_number,"provider_code":"SYN_HOSP",
                "effective_from":"2026-11-01","effective_until":"2027-11-01",
                "contract_notes":"Synthetic medical provider contract — draft only","precedence":0}
            dup=page.request.post("http://127.0.0.1:8000/api/v1/reference/contracts",
                headers={"Authorization":"Bearer "+writer_token},data=manual_payload)
            assert dup.status==409, "Duplicate manual contract number was accepted"
            denied_add=page.request.post("http://127.0.0.1:8000/api/v1/reference/contracts",
                headers={"Authorization":"Bearer "+reader_token},data={**manual_payload,"contract_number":"SYN-DENIED-"+tag})
            assert denied_add.status==403, "Unauthorized reader created G3 draft"
            invalid=page.request.post("http://127.0.0.1:8000/api/v1/reference/contracts",
                headers={"Authorization":"Bearer "+writer_token},
                data={**manual_payload,"contract_number":"SYN-DATE-"+tag,
                      "effective_from":"2027-11-01","effective_until":"2026-11-01"})
            assert invalid.status==409, "Invalid contract dates were accepted"
            with Session(engine) as db:
                assert db.scalar(select(__import__("sqlalchemy").func.count()).select_from(ContractVersion).where(
                    ContractVersion.organization_id==organization_id,
                    ContractVersion.contract_number==contract_number))==1
            results["manual_add_validation"]={"duplicate_status":dup.status,
                "reader_denial_status":denied_add.status,"invalid_dates_status":invalid.status}
            results["add"]="PASS"
            # Select persisted G3 contract from the actual contracts screen.
            page.locator("#drawer").get_by_role("button",name="إغلاق",exact=True).click()
            page.get_by_role("button",name="العقود",exact=True).click()
            choose=page.get_by_role("button",name=contract_number+" — v1",exact=True)
            expect(choose).to_be_visible(timeout=12000)
            choose.click()
            expect(page.get_by_role("button",name="تعديل",exact=True)).to_be_enabled(timeout=10000)
            record(page,"10-selected-existing-g3-contract")
            page.get_by_role("button",name="تعديل",exact=True).click()
            revision=page.locator("#drawer [data-testid='g3-contract-revision-form']")
            expect(revision).to_be_visible()
            expect(revision.get_by_label("معلومات العقد",exact=True)).to_have_value(
                "Synthetic medical provider contract — draft only")
            record(page,"11-prefilled-contract-revision")
            revision.get_by_label("معلومات العقد",exact=True).fill("SYNTHETIC revised contract notes — version 2")
            record(page,"12-revision-edited-before-save")
            with page.expect_response(lambda r: "/api/v1/reference/contracts/drafts/" in r.url
                    and r.url.endswith("/revise") and r.request.method=="POST") as change:
                revision.get_by_role("button",name="تنفيذ الطلب",exact=True).click()
            assert change.value.status==201, "G3 revise HTTP "+str(change.value.status)
            expect(revision).to_contain_text("SYNTHETIC revised contract notes",timeout=10000)
            record(page,"13-contract-version-history")
            from mcias.models import AuditLog
            from mcias.models_reference import ProviderTariff
            with Session(engine) as db:
                versions=db.scalars(select(ContractVersion).where(
                    ContractVersion.organization_id==organization_id,
                    ContractVersion.contract_number==contract_number).order_by(ContractVersion.version)).all()
                assert len(versions)==2 and [v.version for v in versions]==[1,2]
                assert versions[0].contract_notes=="Synthetic medical provider contract — draft only"
                assert versions[1].contract_notes=="SYNTHETIC revised contract notes — version 2"
                assert versions[0].id!=versions[1].id
                assert all(v.status=="draft" and v.authorization_id is None for v in versions)
                assert all(v.provider_code=="SYN_HOSP" for v in versions)
                assert all(v.created_by for v in versions)
                assert versions[1].created_at>=versions[0].created_at
                assert not db.scalars(select(ProviderTariff).where(ProviderTariff.contract_id.in_(
                    [v.id for v in versions]))).first()
                audit=db.scalars(select(AuditLog).where(
                    AuditLog.resource_type=="contract_version",
                    AuditLog.resource_id==versions[1].id,
                    AuditLog.action=="contract_draft_revised")).all()
                assert len(audit)==1 and audit[0].details["previous_id"]==versions[0].id
                original_id=versions[0].id
                latest_id=versions[1].id
                results["revision_db_evidence"]={"contract_number":contract_number,
                    "original_id":original_id,"new_id":latest_id,"versions":[1,2],
                    "original_notes":versions[0].contract_notes,"new_notes":versions[1].contract_notes,
                    "audit_event_id":audit[0].id,"original_unchanged":True,
                    "financial_approval":False}
            revise_url="http://127.0.0.1:8000/api/v1/reference/contracts/drafts/"+original_id+"/revise"
            revised_payload={"contract_notes":"SYN stale overwrite", "effective_from":"2026-11-01",
                "effective_until":"2027-11-01","precedence":0}
            stale=page.request.post(revise_url,
                headers={"Authorization":"Bearer "+writer_token},data=revised_payload)
            assert stale.status==409, "Stale version was accepted"
            # The denied attempt is committed outside the failed business transaction.
            with Session(engine) as db:
                denied_audits=db.scalars(select(AuditLog).where(
                    AuditLog.action=="contract_revision_denied",
                    AuditLog.resource_id==original_id)).all()
                assert denied_audits and denied_audits[-1].details["outcome"]=="denied"
                assert denied_audits[-1].details["organization_id"]==organization_id
                assert "contract_notes" not in denied_audits[-1].details
                results["durable_rejection_audit"]={"event_id":denied_audits[-1].id,
                    "outcome":"denied","survived_rollback":True}
            denied_revision=page.request.post(
                "http://127.0.0.1:8000/api/v1/reference/contracts/drafts/"+latest_id+"/revise",
                headers={"Authorization":"Bearer "+reader_token},data=revised_payload)
            assert denied_revision.status==403, "Unauthorized reader revised G3 contract"
            bad_dates=page.request.post(
                "http://127.0.0.1:8000/api/v1/reference/contracts/drafts/"+latest_id+"/revise",
                headers={"Authorization":"Bearer "+writer_token},
                data={**revised_payload,"effective_from":"2028-01-01","effective_until":"2027-01-01"})
            assert bad_dates.status==409, "Invalid revision effective dates allowed"
            results["revision_guards"]={"stale_version":stale.status,
                "reader_denied":denied_revision.status,"invalid_dates":bad_dates.status}
            # Real audit activity endpoint: tenant-scoped, metadata-only, no raw details.
            from mcias.models import AuditLog
            with Session(engine) as db:
                foreign=Organization(name="SYN FOREIGN AUDIT "+tag)
                db.add(foreign);db.flush()
                foreign_actor=User(organization_id=foreign.id,username="syn-audit-other-"+tag,
                                   password_hash=hash_password(password))
                db.add(foreign_actor);db.flush()
                foreign_event=AuditLog(actor_id=foreign_actor.id,action="synthetic_foreign_private",
                                      resource_type="contract_version",resource_id=None,
                                      details={"medical_secret":"DO_NOT_EXPOSE"})
                db.add(foreign_event);db.commit()
            activity=page.request.get("http://127.0.0.1:8000/api/v1/workspace/activity?limit=100",
                                      headers={"Authorization":"Bearer "+writer_token})
            assert activity.status==200, "Audit activity list HTTP "+str(activity.status)
            body=activity.json()
            assert body["details_redacted"] is True and body["scope"]=="current_organization"
            assert body["items"] and all("details" not in item for item in body["items"])
            assert any(item["action"]=="contract_draft_revised" for item in body["items"])
            assert any(item["action"]=="contract_revision_denied" for item in body["items"])
            assert not any(item["action"]=="synthetic_foreign_private" for item in body["items"])
            assert "DO_NOT_EXPOSE" not in activity.text()
            with Session(engine) as db:
                success_event=db.scalar(select(AuditLog).where(
                    AuditLog.action=="contract_draft_revised",AuditLog.resource_id==latest_id))
                assert success_event and success_event.details["outcome"]=="success"
                assert success_event.details["organization_id"]==organization_id
                # Database-level immutable audit history: privileged owner cannot
                # bypass the database trigger with raw UPDATE or DELETE.
                from sqlalchemy import text as sql_text
                from sqlalchemy.exc import DBAPIError
                for stmt in ("UPDATE audit_log SET action='forged' WHERE id=:id",
                             "DELETE FROM audit_log WHERE id=:id"):
                    try:
                        db.execute(sql_text(stmt),{"id":success_event.id})
                        db.commit()
                        raise AssertionError("Raw SQL audit mutation was accepted")
                    except DBAPIError:
                        db.rollback()
                assert db.get(AuditLog,success_event.id).action=="contract_draft_revised"
            results["activity_audit"]={"status":"PASS","actor_tenant_isolation":True,
                                       "details_redacted":True,"revision_event_visible":True}
            results["edit"]="PASS"
        finally:
            try: record(page,"99-last-browser-state")
            except Exception: pass
            browser.close()
except Exception as exc:
    results["failure"]=type(exc).__name__+": "+str(exc)[:1000]
    results["traceback"]=traceback.format_exc()[-2500:]
    print(json.dumps(results,ensure_ascii=False,indent=2))
    (OUT/"results.json").write_text(json.dumps(results,ensure_ascii=False,indent=2))
    raise
finally:
    (OUT/"results.json").write_text(json.dumps(results,ensure_ascii=False,indent=2))
    print(json.dumps(results,ensure_ascii=False,indent=2))
    engine.dispose()
