import { L, el, button, field, panel, badge, empty, loading, errorState, openDrawer, confirm, toast, details, preferences } from "./ui.js";

const day = () => new Date().toISOString().slice(0, 10);
export function inputList(ctx) {
  const { root, api, route, demo } = ctx, feature = route.feature;
  if (demo) {
    root.append(empty(L("سجل المدخلات", "Reference intake"),
      L("العرض الاصطناعي لا ينشئ سجلات. سجّل الدخول لعرض المدخلات المصرح بها.", "The synthetic preview creates no records. Sign in to view authorized intake."), route.icon));
    return;
  }
  const base = `/api/v1/registry/${encodeURIComponent(feature)}`;
  const card = panel(L("السجلات والمصادر", "Records and sources"),
    L("حفظ المدخل لا يفعّل سياسة مالية. تبقى النسخ والمصادر محفوظة للمراجعة المؤسسية.",
      "Saving intake does not activate financial policy. Versions and sources remain available for institutional review."), route.icon);
  const content = el("div"); card.append(content); root.append(card);
  let schema, offset = 0, generation = 0, selected = null;
  const clauseSection = ['inputs.contracts','inputs.regulations','inputs.exceptions','inputs.caps','inputs.coverage','inputs.approvals'].includes(feature);
  const provider = field('price-provider',L('مقدم الخدمة','Provider'),{required:false,options:[['',L('اختر مقدم الخدمة','Select provider')]]});
  let providerOptionsLoaded=false;
  provider.input.addEventListener('change',()=>{offset=0;selected=null;void load();});
  const search = field("intake-search", L("بحث", "Search"), { required: false, maxLength: 200 });
  const status = field("intake-status", L("الحالة", "Status"), { required: false,
    options: [["", L("الكل", "All")], ["open", L("مفتوح", "Open")], ["closed", L("مغلق", "Closed")]] });

  function recordForm(previous, evidenceDocumentId = null, onSubmit = null, parent = null) {
    const form = el("form"), inputs = new Map(), grid = el("div", null, "form-grid");
    const title = field("intake-title", L("الاسم / العنوان", "Name / title"), { maxLength: 200, value: previous?.title || "" });
    const from = field("intake-from", L("تاريخ بداية السريان", "Effective from"), { type: "date", value: previous?.effective_from || parent?.effective_from || day() });
    const until = field("intake-to", L("تاريخ نهاية السريان (اختياري)", "Effective until (optional)"), { type: "date", required: false, value:previous?.effective_to || '' });
    grid.append(title.wrap, from.wrap, until.wrap);
    for (const item of schema.fields) {
      const initial=previous?.values?.[item.key] || (item.key==='record_code'?'':parent?.values?.[item.key]) || (item.key==='provider_code'?provider.input.value:'');
      const control = field(`intake-${item.key}`, L(item.ar, item.en), { maxLength: item.max_length || 200, value: initial });
      if (item.key === "record_code" && previous) control.input.readOnly = true;
      if (item.key === "currency") control.input.pattern = "[A-Z]{3}";
      if (["amount", "percent"].includes(item.key)) control.input.inputMode = "decimal";
      if (item.key === "coding_system") control.input.placeholder = "LOCAL / ICD / CPT / LOINC / SNOMED";
      inputs.set(item.key, control.input); grid.append(control.wrap);
    }
    const relationControls=new Map(),termControls=new Map(),relations=schema.relationships||{};
    const hasMetadata=Object.keys(relations).length||(schema.term_fields||[]).length;
    let linked=null;
    if(hasMetadata){
      const box=el('fieldset'),legend=el('legend',L('روابط وقواعد الفحص','Validation links and terms'));
      const label=el('label'),toggle=el('input');toggle.type='checkbox';toggle.name='intake-linked';
      toggle.checked=Boolean(Object.keys(previous?.links||parent?.links||{}).length||Object.keys(previous?.terms||parent?.terms||{}).length);
      toggle.disabled=Boolean(Object.keys(previous?.links||{}).length||Object.keys(previous?.terms||{}).length);
      label.append(toggle,el('span',L('ربط هذا السجل للفحص بحسب الفئة والخدمة والعقد','Link this record for category, service and contract validation')));
      box.append(legend,label,el('p',L('السجل غير المرتبط يبقى محفوظًا ويحتاج استكمالًا قبل الفحص. النسبة هي تحمل المستفيد، وليست نسبة تغطية الجهة.','Unlinked records remain preserved and require completion before validation. The percentage is beneficiary copay, not institution coverage.')));
      const names={provider:['مقدم الخدمة المرتبط','Linked provider'],contract:['العقد المرتبط','Linked contract'],category:['الفئة المرتبطة','Linked category'],service:['الخدمة المرتبطة','Linked service']};
      for(const [role,options] of Object.entries(relations)){
        const control=field('intake-link-'+role,L(...names[role]),{options:[['',L('اختر المرجع','Select reference')],...options.map(r=>[r.id,r.title])]});
        control.input.value=previous?.links?.[role]||parent?.links?.[role]||'';
        control.input.addEventListener('change',()=>{const target=options.find(r=>r.id===control.input.value);if(!target)return;
          for(const [key,input] of inputs)if(key!=='record_code'&&target.values[key])input.value=target.values[key];});
        relationControls.set(role,control.input);box.append(control.wrap);
      }
      for(const item of schema.term_fields||[]){
        const control=field('intake-term-'+item.key,L(item.ar,item.en),item.options.length?{options:[['',L('اختر القيمة','Select value')],...item.options.map(([value,ar,en])=>[value,L(ar,en)])]}:{maxLength:3,pattern:'[A-Z]{3}'});
        const value=previous?.terms?.[item.key]??parent?.terms?.[item.key];control.input.value=value===undefined?'':String(value);
        termControls.set(item.key,control.input);box.append(control.wrap);
      }
      const update=()=>{for(const input of [...relationControls.values(),...termControls.values()]){input.disabled=!toggle.checked;input.required=toggle.checked;}};
      toggle.addEventListener('change',update);update();linked=toggle;grid.append(box);
    }
    const clause = parent ? field('intake-clause',L('رقم البند الهرمي، مثل 1.1','Hierarchical clause number, e.g. 1.1'),{maxLength:60,pattern:'[1-9][0-9]*(\\.[1-9][0-9]*)*'}) : null;
    if(clause)grid.append(clause.wrap);
    const bodyLabel=el('label',L('التفاصيل / نص البند','Details / clause text')),body=el('textarea');
    body.id='intake-body';body.maxLength=20000;body.rows=5;body.value=previous?.body||'';bodyLabel.htmlFor=body.id;grid.append(bodyLabel,body);
    const reason=previous?.status==='open'?field('intake-edit-reason',L('سبب التعديل','Reason for change'),{maxLength:2000}):null;
    if(reason)grid.append(reason.wrap);
    const feedback = el("div"); feedback.setAttribute("aria-live", "polite");
    const save = el("button", L("حفظ السجل", "Save record"), "button primary"); save.type = "submit";
    form.append(grid, save, feedback);
    form.addEventListener("submit", async event => {
      event.preventDefault(); if (save.disabled || !form.reportValidity()) return;
      save.disabled = true;
      try {
        const payload = { title: title.input.value.trim(), effective_from: from.input.value,
          effective_to: until.input.value || null, values: Object.fromEntries([...inputs].map(([key, input]) => [key, input.value.trim()])) };
        if (evidenceDocumentId) payload.evidence_document_id = evidenceDocumentId;
        payload.body=body.value;
        if(linked?.checked){
          payload.links=Object.fromEntries([...relationControls].map(([key,input])=>[key,input.value]));
          payload.terms=Object.fromEntries([...termControls].map(([key,input])=>[key,key==='precision'?Number(input.value):key==='require_beneficiary_name'?input.value==='true':input.value]));
        }
        if(parent){payload.parent_id=parent.id;payload.clause_number=clause.input.value.trim();}
        if(previous?.parent_id){payload.parent_id=previous.parent_id;payload.clause_number=previous.clause_number;}
        if (onSubmit) await onSubmit(payload);
        else {
          if (previous) payload.expected_version = previous.version;
          if(reason)payload.reason=reason.input.value.trim();
          await api.request(previous ? `${base}/records/${previous.id}/${previous.status==='open'?'replace':'versions'}` : `${base}/records`, { method: "POST", body: payload });
          document.getElementById("drawer").close(); await load();
          toast(L("تم حفظ السجل للمراجعة", "Record saved for review"));
        }
      } catch (error) { feedback.replaceChildren(errorState(error)); }
      finally { save.disabled = false; }
    });
    return form;
  }

  async function showRecord(id) {
    const body = el("div"); body.append(loading()); openDrawer(L("تفاصيل السجل", "Record details"), body);
    try {
      const [record, history] = await Promise.all([api.request(`${base}/records/${id}`), api.request(`${base}/records/${id}/history`)]);
      body.replaceChildren(el("h3", record.title), badge(L(record.status === "open" ? "مفتوح" : "مغلق", record.status === "open" ? "Open" : "Closed")),
        el("p", L("بانتظار المراجعة المؤسسية", "Pending institutional review"), "muted"),
        details({ id: record.id, version: record.version, effective_from: record.effective_from,
          effective_to: record.effective_to, source_sha256: record.source_sha256, ...record.values }));
      if(Object.keys(record.links||{}).length||Object.keys(record.terms||{}).length)
        body.append(el('h3',L('العلاقات والقواعد','Relationships and terms')),details({...record.links,...record.terms}));
      if (record.close_reason) body.append(el("p", record.close_reason));
      const actions = el("div", null, "actions"); body.append(actions);
      if(record.status==='open' && schema.permissions.update)
        actions.append(button(L('تعديل','Edit'),()=>openDrawer(L('تعديل مع حفظ النسخة السابقة','Edit and preserve previous version'),recordForm(record))));
      if (record.status === "open" && schema.permissions.close) {
        const close = button(L("إغلاق السجل", "Close record"), () => {
          const form = el("form"), reason = field("intake-close-reason", L("سبب الإغلاق", "Closing reason"), { maxLength: 2000 });
          const save = el("button", L("تأكيد الإغلاق", "Confirm closure"), "button primary"); save.type = "submit";
          const result = el("div"); result.setAttribute("aria-live", "polite"); form.append(reason.wrap, save, result);
          form.addEventListener("submit", async event => {
            event.preventDefault(); if (save.disabled || !form.reportValidity()) return; save.disabled = true;
            try {
              await api.request(`${base}/records/${id}/close`, { method: "POST", body: { expected_version: record.version, reason: reason.input.value.trim() } });
              document.getElementById("drawer").close(); await load(); toast(L("تم إغلاق السجل", "Record closed"));
            } catch (error) { result.replaceChildren(errorState(error)); }
            finally { save.disabled = false; }
          }); openDrawer(L("إغلاق السجل", "Close record"), form);
        });
        if (record.effective_from > day()) { close.disabled = true; close.title = L("لا يُغلق سجل قبل بدء سريانه", "Cannot close before its effective date"); }
        actions.append(close);
      }
      if (record.status === "closed" && schema.permissions.create)
        actions.append(button(L("إضافة نسخة جديدة", "Add new version"), () => openDrawer(L("نسخة جديدة", "New version"), recordForm(record))));
      body.append(el("h3", L("تاريخ النسخ", "Version history")));
      for (const version of history.items) body.append(el("p", `${version.version} · ${version.status} · ${version.effective_from} → ${version.effective_to || "—"}`));
      if (record.evidence) {
        body.append(el("h3", L("المرفقات والمصدر", "Attachments and source")), el("code", record.evidence.sha256));
        body.append(button(L("تنزيل المصدر المرتبط", "Download linked source"), async () => {
          try {
            const blob = await api.request(`${base}/records/${id}/evidence/${record.evidence.document_id}`, { download: true });
            const extension = ["csv","xlsx","pdf"].includes(record.evidence.format) ? record.evidence.format : "bin";
            const url = URL.createObjectURL(blob), anchor = document.createElement("a"); anchor.href = url; anchor.download = `source-${record.evidence.document_id}.${extension}`;
            anchor.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
          } catch (error) { toast(error.message); }
        }));
      }
    } catch (error) { body.replaceChildren(errorState(error, () => void showRecord(id))); }
  }

  function importDialog() {
    const body = el("div"), form = el("form"), file = field("intake-file", L("ملف المصدر", "Source file"), { type: "file" });
    file.input.accept = ".xlsx,.csv,.pdf";
    const upload = el("button", L("رفع ومعاينة", "Upload and preview"), "button primary"); upload.type = "submit";
    const preview = el("div"); preview.setAttribute("aria-live", "polite");
    form.append(file.wrap, upload); body.append(form, preview);
    const template = ["title", "effective_from", "effective_to", ...schema.fields.map(item => item.key)].join(",");
    body.append(el("p", L("أعمدة CSV / Excel المطلوبة:", "Required CSV / Excel columns:")), el("code", template));
    form.addEventListener("submit", async event => {
      event.preventDefault(); if (upload.disabled || !form.reportValidity()) return;
      const selected = file.input.files[0]; if (!selected) return;
      if (selected.size > 20 * 1024 * 1024) { preview.replaceChildren(el("p", L("الحد الأقصى 20 MiB", "Maximum 20 MiB"))); return; }
      upload.disabled = true; preview.replaceChildren(loading());
      try {
        const source = await api.request(`${base}/imports?filename=${encodeURIComponent(selected.name)}`, { method: "POST", raw: true, body: await selected.arrayBuffer() });
        if (source.status === "review_required") {
          preview.replaceChildren(empty(L("المصدر محجور للمراجعة", "Source quarantined for review"),
            L("حُفظ الأصل. عالج أسباب الاستخراج أو أعد رفع ملف صحيح.", "The original is preserved. Resolve extraction issues or upload a valid source."))); return;
        }
        const result = await api.request(`${base}/imports/${source.document_id}/preview`); preview.replaceChildren(el("code", result.source_sha256));
        if (result.items.some(item => item.manual_required)) {
          preview.append(el("p", L("PDF دليل مصدر؛ أدخل الحقول بعد مراجعة المستند.", "PDF is source evidence; enter structured fields after reviewing it.")));
          for (const item of result.items) preview.append(el("pre", item.text_excerpt));
          preview.append(recordForm(null, source.document_id, async payload => {
            await api.request(`${base}/imports/${source.document_id}/commit`, { method: "POST", body: { manual_record: payload } });
            document.getElementById("drawer").close(); await load(); toast(L("تم حفظ المدخل المرتبط بالمصدر", "Source-linked intake saved"));
          })); return;
        }
        const selectedRows = new Set();
        for (const item of result.items) {
          const row = el("div", null, "import-row");
          if (item.valid) {
            const checkbox = el("input"); checkbox.type = "checkbox"; checkbox.checked = true; checkbox.id = `import-row-${item.id}`;
            const label = el("label", item.record.title); label.htmlFor = checkbox.id;
            selectedRows.add(item.id); checkbox.addEventListener("change", () => checkbox.checked ? selectedRows.add(item.id) : selectedRows.delete(item.id));
            row.append(checkbox, label, details(item.record));
          } else row.append(badge(L("سجل غير صالح", "Invalid record"), "warning"), details(item.locator), el("p", item.error));
          preview.append(row);
        }
        const save = button(L("تأكيد وحفظ المحدد", "Confirm and save selected"), async () => {
          if (!selectedRows.size) { toast(L("اختر سجلاً صالحاً", "Select a valid row")); return; }
          if (!(await confirm(L("حفظ المدخلات المحددة للمراجعة؟", "Save selected intake for review?")))) return;
          save.disabled = true;
          try {
            await api.request(`${base}/imports/${source.document_id}/commit`, { method: "POST", body: { record_ids: [...selectedRows] } });
            document.getElementById("drawer").close(); await load(); toast(L("تم حفظ المدخلات", "Intake saved"));
          } catch (error) { preview.append(errorState(error)); }
          finally { save.disabled = false; }
        }, "button primary");
        preview.append(save);
      } catch (error) { preview.replaceChildren(errorState(error)); }
      finally { upload.disabled = false; }
    });
    openDrawer(L("استيراد ملف", "Import file"), body);
  }

  async function load() {
    const version = ++generation; content.replaceChildren(loading());
    try {
      schema = await api.request(`${base}/schema`);
      if(feature==='providers.prices'&&!providerOptionsLoaded){
        const options=await api.request(`${base}/provider-options`);
        for(const item of options.items){const option=el('option',item.name);option.value=item.code;provider.input.append(option);}providerOptionsLoaded=true;
      }
      const data = await api.request(`${base}/records?offset=${offset}&limit=25&q=${encodeURIComponent(search.input.value)}${status.input.value ? `&status=${status.input.value}` : ""}${feature==='providers.prices'&&provider.input.value?`&provider_code=${encodeURIComponent(provider.input.value)}`:''}`);
      if (version !== generation || !content.isConnected) return;
      const filters = el("form", null, "filters"), apply = el("button", L("تطبيق", "Apply"), "button"); apply.type = "submit";
      if(feature==='providers.prices')filters.append(provider.wrap);
      filters.append(search.wrap, status.wrap, apply);
      filters.addEventListener("submit", event => { event.preventDefault(); offset = 0; void load(); });
      const actions = el("div", null, "actions");
      const nouns={ 'inputs.contracts':['عقد','contract'],'inputs.regulations':['لائحة','regulation'],
        'inputs.exceptions':['استثناء','exception'],'inputs.caps':['سقف','ceiling'],'inputs.coverage':['تغطية','coverage'],'inputs.approvals':['موافقة','approval'] };
      const noun=nouns[feature];
      const add=button(noun?L(`إضافة ${noun[0]} جديد`,`Add new ${noun[1]}`):L('إضافة','Add'),()=>openDrawer(L('سجل جديد','New record'),recordForm(null)),'button primary');
      add.disabled=!schema.permissions.create;actions.append(add);
      const edit=button(clauseSection?L('تعديل بند','Edit clause'):L('تعديل','Edit'),()=>{if(selected)openDrawer(L('تعديل مع حفظ التاريخ','Edit with history preserved'),recordForm(selected));});
      edit.disabled=!selected||!schema.permissions.update;actions.append(edit);
      const addClause=clauseSection?button(L('إضافة بند','Add clause'),()=>{if(selected)openDrawer(L('إضافة بند','Add clause'),recordForm(null,null,null,selected));}):null;
      if(addClause){addClause.disabled=!selected||!schema.permissions.create;actions.append(addClause);}
      const list = el("div", null, "table-scroll"),table=el('table'),thead=el('thead'),header=el('tr');
      for(const label of [L('تحديد','Select'),L('الاسم / البند','Name / clause'),L('القيم المرجعية','Reference values'),L('الحالة','Status'),L('فترة السريان','Validity'),L('الإصدار','Version'),L('المصدر والاكتمال','Source and completeness'),L('الاعتماد','Approval')])header.append(el('th',label));
      thead.append(header);table.append(thead);const tbody=el('tbody');
      for (const record of data.items) {
        const row=el('tr'),choice=el('td'),radio=el('input');radio.type='radio';radio.name='selected-intake';radio.checked=selected?.id===record.id;radio.setAttribute('aria-label',record.title);
        radio.addEventListener('change',()=>{selected=record;edit.disabled=!schema.permissions.update;if(addClause)addClause.disabled=!schema.permissions.create||record.status!=='open';});choice.append(radio);
        const title=el('td');title.append(button(`${record.clause_number?record.clause_number+' · ':''}${record.title}`,()=>void showRecord(record.id),'link-button'));
        const values=el('td');for(const item of schema.fields.filter(i=>i.key!=='record_code'))values.append(el('div',`${L(item.ar,item.en)}: ${record.values[item.key]}`));
        if(record.terms?.network)values.append(el('div',L(record.terms.network==='in_network'?'داخل الشبكة':'خارج الشبكة',record.terms.network==='in_network'?'In network':'Out of network')));
        if(record.terms?.service_type)values.append(el('div',record.terms.service_type));
        row.append(choice,title,values,el('td',L(record.status==='open'?'مفتوح':'مغلق',record.status==='open'?'Open':'Closed')),
          el('td',`${record.effective_from} → ${record.effective_to||'—'}`),el('td',record.version),
          el('td',L(record.evidence?'مستند مرتبط؛ حقول مكتملة':'إدخال يدوي؛ حقول مكتملة',record.evidence?'Linked document; fields complete':'Manual entry; fields complete')),
          el('td',L('بانتظار مراجعة المرجع','Reference review pending')));tbody.append(row);
      }
      table.append(tbody);list.append(table);
      const pagination = el("div", null, "actions");
      if (offset) pagination.append(button(L("السابق", "Previous"), () => { offset = Math.max(0, offset - 25); void load(); }));
      if (data.has_more) pagination.append(button(L("التالي", "Next"), () => { offset += 25; void load(); }));
      const showPrices=feature!=='providers.prices'||Boolean(provider.input.value);
      content.replaceChildren(filters,showPrices?(data.items.length?list:empty(L('لا سجلات','No records'),L('أضف سجلًا جديدًا.','Add a new record.'),route.icon)):
        empty(L('اختر مقدم الخدمة أولًا','Select a provider first'),L('تظهر تسعيرات المقدم المختار فقط.','Only the selected provider’s price list is shown.'),route.icon),pagination,actions);
    } catch (error) { content.replaceChildren(errorState(error, () => void load())); }
  }
  void load();
}
