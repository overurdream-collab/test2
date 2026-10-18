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
                assert db.scalar(select(InputClause).where(InputClause.organization_id==org.id,
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
                rows=db.scalars(select(InputClause).where(InputClause.organization_id==org.id,
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
            results["add"]="BLOCKED"
            results["edit"]="BLOCKED"
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
