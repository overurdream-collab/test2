/* Minimal pilot screens on the existing G2/G3/G4/G5/G6/G7 APIs.
 * Reuses the three-action layout of PR #25 without importing its incompatible
 * clause schema/migration into the PR #34 reference-dataset model.
 * All approvals and financial logic remain server-side.
 */
import { L, el, button, badge, panel, field, safeId, details, openDrawer,
         confirm, table, loading, errorState } from "./ui.js";

const FAMILIES = [
  ["beneficiary", "المستفيدون والأهلية", "Beneficiary eligibility"],
  ["contract", "العقود والتغطية", "Contracts & coverage"],
  ["tariff", "الأسعار والتعرفة", "Provider tariffs"],
  ["policy", "السياسات والموافقات", "Policies & approvals"],
  ["caps", "السقوف والحدود", "Limits & ceilings"],
  ["history", "سجل المطالبات السابق", "Historical claims"],
];
const SHEET_KINDS = [
  ["", "— اختر نوع الورقة —", "— Select worksheet type —"],
  ["CLAIMS", "مطالبات", "Claims"],
  ["PAYMENT", "مدفوعات (لا تستورد)", "Payment (excluded)"],
  ["FAMILY_SUMMARY", "ملخص عائلي (لا يستورد)", "Family summary (excluded)"],
  ["OTHER", "أخرى (لا تستورد)", "Other (excluded)"],
];
const uid = () => "pilot-" + Math.random().toString(36).slice(2, 9);
const permitted = (ctx, permission) => !ctx.demo && ctx.context.permissions.includes(permission);
const isSuper = (ctx) => !ctx.demo && ctx.context.roles.includes("super_admin");
const notice = (target, value) => target.replaceChildren(details(value));
const problem = (target, err) => {
  if (err.name !== "AbortError") target.replaceChildren(errorState(err));
};
const labelled = (name, ar, en, opts = {}) => field(name + "-" + uid(), L(ar, en), opts);

export function renderReferencePilot(ctx) {
  const pane = panel(L("المرجعيات الست — INPUTS FIRST", "Six verified reference families"),
    L("استيراد ملف مصدر، إضافة إصدار موثق، وتعديل بإنشاء إصدار جديد. لا يكفي رفع الملف لاعتماد محتواه؛ جميع الضوابط على الخادم.",
      "Upload original source, register a source-backed version, or revise as a new version. Upload alone never approves a reference."), "policy");
  const tabs = el("div", null, "input-tabs");
  const actions = el("div", null, "input-actions");
  const records = el("div");
  const selection = el("div");
  pane.append(tabs, actions, selection, records);
  ctx.root.append(pane);
  let family = "beneficiary", chosen = null;
  const latestDocuments = new Map();
  let refresh = () => {};
  for (const [key, ar, en] of FAMILIES) {
    const tab = button(L(ar, en), () => draw(key), "button input-tab");
    tab.dataset.family = key;
    tabs.append(tab);
  }
  function draw(key) {
    family = key;
    chosen = null;
    selection.replaceChildren();
    actions.replaceChildren();
    for (const tab of tabs.children)
      tab.setAttribute("aria-pressed", String(tab.dataset.family === key));
    const upload = button(L("استيراد ملف", "Import source file"),
      () => showUpload(key), "button");
    const add = button(L("إضافة", "Add version"),
      () => showVersion(key, null), "button");
    const edit = button(L("تعديل — إصدار جديد", "Edit — new version"),
      () => { if (chosen) showVersion(key, chosen); }, "button");
    const approve = button(L("اعتماد مصدر مكتمل", "Approve complete source"),
      () => { if (chosen) void doApprove(key, chosen); }, "button");
    upload.disabled = !permitted(ctx, "ingestion.upload");
    add.disabled = !(permitted(ctx, "reference.write") || isSuper(ctx));
    edit.disabled = true;
    approve.disabled = true;
    actions.append(upload, add, edit, approve);
    async function load(offset = 0) {
      records.replaceChildren(loading());
      try {
        const data = await ctx.api.request("/api/v1/reference/datasets?family=" + key +
          "&limit=50&offset=" + offset);
        if (family !== key) return;
        records.replaceChildren();
        table(records, data.items, {
          columns: ["dataset_key", "version", "status", "effective_from",
                    "effective_until", "expected_record_count"],
          offset,
          hasMore: data.has_more,
          onPage: load,
          open: row => {
            chosen = row;
            edit.disabled = !(permitted(ctx, "reference.write") || isSuper(ctx));
            approve.disabled = !isSuper(ctx) || row.status !== "draft";
            selection.replaceChildren(details(row));
          },
        });
        if (!data.items.length) records.append(el("p",
          L("لا توجد إصدارات مسجلة في هذا القسم.", "No registered versions for this family.")));
      } catch (err) {
        if (family === key) problem(records, err);
      }
    }
    refresh = load;
    void load();
  }
  function showUpload(key) {
    const body = el("div", null, "form-panel");
    body.append(el("p", L(
      "ملف مرجعي أصلي بصيغة CSV أو XLSX، يحوي أعمدة record_key وpayload. صفوف المصدر يجب أن تطابق عقد G3 القائم؛ رفع PDF لا يفعّل اعتمادًا آليًا.",
      "Original CSV/XLSX must contain record_key and payload columns with the existing G3 schema. A PDF upload does not authorize a reference.")));
    const source = labelled("source", "ملف المصدر", "Source file", {type:"file"});
    source.input.accept = ".csv,.xlsx";
    const output = el("div"); output.setAttribute("aria-live","polite");
    const send = button(L("رفع المصدر", "Upload original"), async () => {
      const file = source.input.files?.[0];
      if (!file || file.size < 1 || file.size > 20 * 1024 * 1024) {
        problem(output, new Error(L("اختر ملفًا صالحًا لا يتجاوز 20 MiB", "Choose a file up to 20 MiB"))); return;
      }
      send.disabled = true; output.replaceChildren(loading());
      try {
        const uploaded = await ctx.api.request("/api/v1/ingestion/uploads?filename=" +
          encodeURIComponent(file.name), {method:"POST",body:file,raw:true});
        if (uploaded.status !== "extracted" && uploaded.status !== "duplicate")
          throw Error(L("المصدر لم يجتز الاستخراج؛ راجع الحجر أولًا", "Source not extracted; review quarantine first"));
        latestDocuments.set(key, uploaded.document_id);
        notice(output, uploaded);
        output.append(el("p", L("استخدم «إضافة» لربط إصدار بهذا المصدر بعد مراجعته.",
          "Use Add to register a reviewed version backed by this source.")));
      } catch (err) { problem(output, err); }
      finally { send.disabled = !permitted(ctx, "ingestion.upload"); }
    }, "button primary");
    send.disabled = !permitted(ctx, "ingestion.upload");
    body.append(source.wrap, send, output);
    openDrawer(L("استيراد ملف المرجع", "Import reference source"), body);
  }
  function showVersion(key, previous) {
    const body = el("div");
    const heading = previous
      ? L("التعديل لا يستبدل الدليل السابق؛ يلزم مصدر جديد وفترة غير متعارضة للاعتماد.",
          "Revision is a NEW source-backed version. Old evidence remains intact; approved date ranges must not overlap.")
      : L("الإضافة تسجل مسودة فقط؛ المراجعة والاعتماد خطوتان منفصلتان.",
          "Add creates a draft only; verification and approval are separate steps.");
    body.append(el("p", heading, "chart-note"));
    const form = el("form", null, "form-grid");
    const specs = [
      ["document_id", "معرّف المستند", "Source document ID", {value: previous ? "" : latestDocuments.get(key) || "",maxLength:36}],
      ["dataset_key", "مفتاح المرجع", "Reference dataset key", {value:previous?.dataset_key || "", maxLength:100}],
      ["version", "رقم الإصدار", "Version", {type:"number",min:1,max:999999,value:previous ? previous.version+1:1}],
      ["effective_from","بداية سريان المرجع","Effective from",{type:"date"}],
      ["effective_until","نهاية سريان المرجع","Effective until",{type:"date"}],
      ["coverage_from","بداية اكتمال المصدر","Source coverage from",{type:"date"}],
      ["coverage_until","نهاية اكتمال المصدر","Source coverage until",{type:"date"}],
      ["expected_record_count","عدد صفوف المصدر المتوقع","Expected source rows",{type:"number",min:1,max:100000,value:1}],
    ];
    const inputs = {};
    for (const [name, ar, en, options] of specs) {
      inputs[name] = labelled(name,ar,en,options).input;
      form.append(inputs[name].parentElement);
    }
    const scopes = [
      ["", "— اختر النطاق صراحة —", "— Explicitly choose scope —"],
      ["provider_code", "مزود محدد", "One provider"],
      ["service_code", "خدمة محددة", "One service"],
      ["beneficiary_token", "مستفيد محدد", "One beneficiary"],
      ["all_providers", "جميع المزودين (يتطلب دليلاً)", "All providers (evidence required)"],
      ["all_services", "جميع الخدمات (يتطلب دليلاً)", "All services (evidence required)"],
      ["all_beneficiaries", "جميع المستفيدين (يتطلب دليلاً)", "All beneficiaries (evidence required)"],
    ];
    const scope = labelled("scope","نطاق التغطية الموثّق","Evidence-backed coverage scope",{
      options:scopes.map(([v,ar,en])=>[v,L(ar,en)])});
    scope.input.value = "";
    const scopeValue = labelled("scope-value", "رمز النطاق المحدد", "Specific scope code",
      {required:false,maxLength:128,pattern:"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}"});
    scope.input.addEventListener("change", () => {
      const specific = !scope.input.value.startsWith("all_");
      scopeValue.input.required = specific;
      scopeValue.wrap.hidden = !specific;
      if (!specific) scopeValue.input.value = "";
    });
    scopeValue.wrap.hidden = true;
    const outcome = el("div"); outcome.setAttribute("aria-live","polite");
    const save = el("button",L("حفظ مسودة إصدار", "Save draft version"),"button primary");
    save.type = "submit";
    save.disabled = !(permitted(ctx,"reference.write") || isSuper(ctx));
    form.append(scope.wrap,scopeValue.wrap,save,outcome);
    form.addEventListener("submit", async event => {
      event.preventDefault();
      if (save.disabled || !form.reportValidity()) return;
      const scopeName = scope.input.value;
      if (!scopeName) {
        problem(outcome,new Error(L("اختر نطاق المرجع", "Choose reference scope")));return;
      }
      if (inputs.effective_from.value >= inputs.effective_until.value ||
          inputs.coverage_from.value >= inputs.coverage_until.value) {
        problem(outcome,new Error(L("تواريخ السريان والتغطية غير صحيحة", "Invalid coverage or effective dates")));return;
      }
      const boundedScope = scopeName.startsWith("all_")
        ? {[scopeName]:true} : {[scopeName]:scopeValue.input.value.trim()};
      const payload = Object.fromEntries(specs.map(([name])=>[name,inputs[name].value]));
      payload.family = key;
      payload.version = Number(payload.version);
      payload.expected_record_count = Number(payload.expected_record_count);
      payload.scope = boundedScope;
      if (!(await confirm(L("حفظ مسودة مصدر موثّق", "Register source-backed draft")))) return;
      save.disabled = true;outcome.replaceChildren(loading());
      try {
        const data = await ctx.api.request("/api/v1/reference/datasets", {method:"POST",body:payload});
        notice(outcome,data);
        if (family === key) void refresh();
      } catch (err) { problem(outcome,err); }
      finally { save.disabled = !(permitted(ctx,"reference.write") || isSuper(ctx)); }
    });
    body.append(form);
    openDrawer(L(previous?"إصدار بديل — دون تعديل الأصل":"إضافة مسودة مرجع",
      previous?"New version — original preserved":"New reference draft"),body);
  }
  async function doApprove(key, item) {
    if (!isSuper(ctx) || item.status !== "draft") return;
    if (!(await confirm(L("أؤكد اكتمال نطاق المصدر بعد مراجعته", "Confirm verified source completeness")))) return;
    selection.replaceChildren(loading());
    try {
      const data = await ctx.api.request("/api/v1/reference/datasets/" + safeId(item.id) +
        "/approve", {method:"POST",body:{reason_code:"source_scope_complete"}});
      notice(selection,data);
      if (family === key) void refresh();
    } catch (err) {problem(selection,err);}
  }
  draw("beneficiary");
}

export function renderClaimPilot(ctx) {
  const pane = panel(L("استيراد Excel وتدقيق مطالبة — خطوة بخطوة", "Guided Excel claim audit"),
    L("اختر الملف، صنّف جميع أوراقه، راجع المطالبات ثم استوردها وشغّل التدقيق الاستشاري. لا اعتماد مالي تلقائي.",
      "Upload, classify every worksheet, preview, import, and run advisory review. No automatic financial decision."), "claims");
  const slot = el("div",null,"pilot-steps");
  pane.append(slot);ctx.root.append(pane);
  const source = labelled("claims-file","ملف مطالبات Excel أو CSV","Claims Excel / CSV",{type:"file"});
  source.input.accept=".xlsx,.csv";
  const upload = el("button",L("1. رفع الملف", "1. Upload file"),"button primary");
  upload.type="button";
  upload.disabled=!permitted(ctx,"ingestion.upload");
  const status = el("div");status.setAttribute("aria-live","polite");
  const scope = el("div"),batchArea=el("div"),auditArea=el("div");
  slot.append(source.wrap,upload,status,scope,batchArea,auditArea);
  let documentId = null, batchId = null, claimId = null;
  function reset() {
    documentId=null;batchId=null;claimId=null;
    scope.replaceChildren();batchArea.replaceChildren();auditArea.replaceChildren();
  }
  upload.addEventListener("click",async()=>{
    const file=source.input.files?.[0];
    if(!file || !file.size || file.size>20*1024*1024){
      problem(status,new Error(L("اختر ملفًا حتى 20 MiB", "Select file up to 20 MiB")));return;
    }
    reset();upload.disabled=true;status.replaceChildren(loading());
    try{
      const data=await ctx.api.request("/api/v1/ingestion/uploads?filename="+
        encodeURIComponent(file.name),{method:"POST",body:file,raw:true});
      if(data.status!=="extracted"&&data.status!=="duplicate")
        throw Error(L("الملف غير جاهز للاستيراد؛ راجع سجل الحجر", "Source not ready; review quarantine"));
      documentId=data.document_id;notice(status,data);
      if(file.name.toLowerCase().endsWith(".xlsx"))await sheetChoices(documentId);
      else stageButton(documentId);
    }catch(err){problem(status,err);}
    finally{upload.disabled=!permitted(ctx,"ingestion.upload");}
  });
  async function sheetChoices(docId){
    scope.replaceChildren(loading());
    try{
      const data=await ctx.api.request("/api/v1/claims/documents/"+safeId(docId)+
        "/worksheet-inventory");
      if(documentId!==docId)return;
      scope.replaceChildren(el("h3",L("2. تصنيف أوراق الملف", "2. Classify original worksheets")));
      const selects=[];
      for(const sheet of data.sheets){
        const options=SHEET_KINDS.filter(([type])=>type!=="CLAIMS" ||
          (sheet.claims_columns_present && !sheet.reserved_non_claims));
        const cell=labelled("sheet-"+sheet.index,sheet.name+" (#"+sheet.index+
          " · "+sheet.data_rows+" "+L("صف","rows")+")",
          sheet.name+" (#"+sheet.index+")",{options:options.map(([v,ar,en])=>[v,L(ar,en)])});
        cell.input.value="";
        selects.push([sheet.index,cell.input]);
        scope.append(cell.wrap);
      }
      const confirmSheets=button(L("اعتماد تصنيف جميع الأوراق", "Approve all worksheet types"),
        async()=>{
          if(selects.some(([,input])=>!input.value)){
            problem(result,new Error(L("صنّف كل ورقة أولًا", "Classify every sheet")));return;
          }
          if(!selects.some(([,input])=>input.value==="CLAIMS")){
            problem(result,new Error(L("لم تحدد ورقة مطالبات", "No claims worksheet selected")));return;
          }
          if(!(await confirm(L("اعتماد نطاق المصدر", "Approve worksheet scope"))))return;
          confirmSheets.disabled=true;result.replaceChildren(loading());
          try{
            const map=Object.fromEntries(selects.map(([id,input])=>[id,input.value]));
            const approved=await ctx.api.request("/api/v1/claims/documents/"+safeId(docId)+
              "/source-scope",{method:"POST",body:{sheet_types:map}});
            notice(result,approved);
            stageButton(docId);
          }catch(err){problem(result,err);}
          finally{confirmSheets.disabled=!permitted(ctx,"claims.import");}
        },"button primary");
      confirmSheets.disabled=!permitted(ctx,"claims.import");
      const result=el("div");
      scope.append(confirmSheets,result);
    }catch(err){problem(scope,err);}
  }
  function stageButton(docId){
    const start=button(L("3. إنشاء دفعة للمعاينة", "3. Stage & preview batch"),async()=>{
      start.disabled=true;batchArea.replaceChildren(loading());
      try{
        const data=await ctx.api.request("/api/v1/claims/batches/from-document/"+
          safeId(docId),{method:"POST"});
        batchId=data.id;
        await previewBatch(data.id);
      }catch(err){problem(batchArea,err);}
      finally{start.disabled=!permitted(ctx,"claims.import");}
    },"button primary");
    start.disabled=!permitted(ctx,"claims.import");
    scope.append(start);
  }
  async function previewBatch(id){
    const data=await ctx.api.request("/api/v1/claims/batches/"+safeId(id)+
      "/preview?limit=100");
    batchArea.replaceChildren(el("h3",L("4. معاينة مصدر المطالبات", "4. Preview claims")));
    batchArea.append(details({
      record_count:data.record_count,excluded_count:data.excluded_count,
      source_scope_approval_id:data.source_scope_approval_id,
      previewed_rows:data.rows?.length
    }));
    const rows=el("div");
    table(rows,data.rows||[],{columns:["claim_reference","valid","reason","record_id"]});
    batchArea.append(rows);
    const apply=button(L("5. تأكيد استيراد الدفعة", "5. Import reviewed batch"),async()=>{
      if(!(await confirm(L("استيراد دفعة موثقة", "Import source-verified batch"))))return;
      apply.disabled=true;auditArea.replaceChildren(loading());
      try{
        const outcome=await ctx.api.request("/api/v1/claims/batches/"+safeId(id)+
          "/resume?chunk_size=100",{method:"POST"});
        notice(auditArea,outcome);
        await showClaims(id,outcome.status);
      }catch(err){problem(auditArea,err);}
      finally{apply.disabled=!permitted(ctx,"claims.import");}
    },"button primary");
    apply.disabled=!permitted(ctx,"claims.import");
    batchArea.append(apply);
  }
  async function showClaims(id,state){
    const data=await ctx.api.request("/api/v1/claims/batches/"+safeId(id)+
      "/entries?limit=100");
    const holder=el("div");
    auditArea.append(el("h3",L("6. المطالبات المستوردة", "6. Imported claims")),holder);
    const picked=el("div");auditArea.append(picked);
    table(holder,data.entries||[],{
      columns:["claim_reference","claimed_amount","currency","service_date"],
      open:record=>{
        claimId=record.id;
        picked.replaceChildren(details(record));
        const run=button(L("تشغيل فحص G5 الاستشاري", "Run G5 advisory audit"),
          async()=>{
            if(!(await confirm(L("تشغيل تدقيق مؤرخ", "Run dated advisory audit"))))return;
            run.disabled=true;result.replaceChildren(loading());
            try{
              const outcome=await ctx.api.request("/api/v1/audits/claims/"+
                safeId(claimId)+"/review",{method:"POST"});
              notice(result,outcome);
              const snapshotId=outcome.id||outcome.snapshot_id;
              if(snapshotId){
                const createCase=button(L("فتح مراجعة G6", "Open G6 review case"),async()=>{
                  createCase.disabled=true;
                  try{
                    const created=await ctx.api.request("/api/v1/governance/cases/from-audit/"+
                      safeId(snapshotId),{method:"POST"});
                    notice(result,created);
                    const review=button(L("عرض المراجعات", "Open human review"),()=>ctx.navigate("/institution/reviews"));
                    result.append(review);
                  }catch(err){problem(result,err);}
                  finally{createCase.disabled=!permitted(ctx,"claims.read");}
                });
                createCase.disabled=!permitted(ctx,"claims.read");
                result.append(createCase);
              }
            }catch(err){problem(result,err);}
            finally{run.disabled=!isSuper(ctx);}
          },"button primary");
        run.disabled=!isSuper(ctx) || state!=="imported";
        const reports=button(L("عرض التقارير G7", "Open G7 reports"),()=>ctx.navigate("/institution/reports"));
        const result=el("div");
        picked.append(run,reports,result);
      }
    });
    if(state!=="imported")
      auditArea.append(el("p",L("الدفعة ليست مكتملة؛ راجع الصفوف المرفوضة قبل التدقيق.",
        "Import is not complete; review rejected rows before auditing.")));
  }
}
