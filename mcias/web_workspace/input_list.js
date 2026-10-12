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
  let schema, offset = 0, generation = 0;
  const search = field("intake-search", L("بحث", "Search"), { required: false, maxLength: 200 });
  const status = field("intake-status", L("الحالة", "Status"), { required: false,
    options: [["", L("الكل", "All")], ["open", L("مفتوح", "Open")], ["closed", L("مغلق", "Closed")]] });

  function recordForm(previous, evidenceDocumentId = null, onSubmit = null) {
    const form = el("form"), inputs = new Map(), grid = el("div", null, "form-grid");
    const title = field("intake-title", L("الاسم / العنوان", "Name / title"), { maxLength: 200, value: previous?.title || "" });
    const from = field("intake-from", L("تاريخ البداية", "Effective from"), { type: "date", value: day() });
    const until = field("intake-to", L("تاريخ النهاية (اختياري)", "Effective to (optional)"), { type: "date", required: false });
    grid.append(title.wrap, from.wrap, until.wrap);
    for (const item of schema.fields) {
      const control = field(`intake-${item.key}`, L(item.ar, item.en), { maxLength: item.max_length || 200, value: previous?.values?.[item.key] || "" });
      if (item.key === "record_code" && previous) control.input.readOnly = true;
      if (item.key === "currency") control.input.pattern = "[A-Z]{3}";
      if (["amount", "percent"].includes(item.key)) control.input.inputMode = "decimal";
      if (item.key === "coding_system") control.input.placeholder = "LOCAL / ICD / CPT / LOINC / SNOMED";
      inputs.set(item.key, control.input); grid.append(control.wrap);
    }
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
        if (onSubmit) await onSubmit(payload);
        else {
          if (previous) payload.expected_version = previous.version;
          await api.request(previous ? `${base}/records/${previous.id}/versions` : `${base}/records`, { method: "POST", body: payload });
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
      if (record.close_reason) body.append(el("p", record.close_reason));
      const actions = el("div", null, "actions"); body.append(actions);
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
      const data = await api.request(`${base}/records?offset=${offset}&limit=25&q=${encodeURIComponent(search.input.value)}${status.input.value ? `&status=${status.input.value}` : ""}`);
      if (version !== generation || !content.isConnected) return;
      const filters = el("form", null, "filters"), apply = el("button", L("تطبيق", "Apply"), "button"); apply.type = "submit";
      filters.append(search.wrap, status.wrap, apply);
      filters.addEventListener("submit", event => { event.preventDefault(); offset = 0; void load(); });
      const actions = el("div", null, "actions");
      if (schema.permissions.create) {
        actions.append(button(L("إضافة جديد", "Add new"), () => openDrawer(L("سجل جديد", "New record"), recordForm(null)), "button primary"));
        actions.append(button(L("استيراد ملف", "Import file"), importDialog));
      }
      const list = el("div", null, "intake-grid");
      for (const record of data.items) {
        const item = el("article", null, "intake-card");
        item.append(el("h3", record.title), badge(L(record.status === "open" ? "مفتوح" : "مغلق", record.status === "open" ? "Open" : "Closed")),
          el("p", `${record.effective_from} → ${record.effective_to || "—"}`, "muted"),
          el("p", `${L("النسخة", "Version")} ${record.version}`),
          button(L("عرض التفاصيل", "View details"), () => void showRecord(record.id)));
        list.append(item);
      }
      const pagination = el("div", null, "actions");
      if (offset) pagination.append(button(L("السابق", "Previous"), () => { offset = Math.max(0, offset - 25); void load(); }));
      if (data.has_more) pagination.append(button(L("التالي", "Next"), () => { offset += 25; void load(); }));
      content.replaceChildren(filters, actions, data.items.length ? list : empty(L("لا سجلات", "No records"),
        L("أضف مدخلاً أو استورد مصدراً مصرحاً به.", "Add intake or import an authorized source."), route.icon), pagination);
    } catch (error) { content.replaceChildren(errorState(error, () => void load())); }
  }
  void load();
}
