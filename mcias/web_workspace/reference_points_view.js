/* Governed point-per-input-section editor; DOM-only, same-origin, and no auto-activation. */
import { L, el, button, badge, panel, field, details, openDrawer,
         errorState, loading, toast, confirm } from "./ui.js";

const SECTIONS = [
  ["contracts", "بنود العقود", "Contract clauses"],
  ["providers", "مقدمو الخدمة", "Providers"],
  ["beneficiaries", "المستفيدون", "Beneficiaries"],
  ["cost_sharing", "نسب التحمل", "Cost sharing"],
  ["categories", "الفئات", "Categories"],
  ["exclusions", "الاستثناءات", "Exclusions"],
  ["approvals", "الموافقات", "Prior approvals"],
  ["tariffs", "أسعار مقدمي الخدمة", "Provider tariffs"],
];
const RULE_TYPES = [
  ["text", "نص تعاقدي", "Contract text"],
  ["amount", "مبلغ", "Amount"],
  ["percentage", "نسبة مئوية", "Percentage"],
  ["count", "عدد", "Count"],
  ["exclusion", "استثناء", "Exclusion"],
  ["approval", "موافقة", "Approval"],
  ["duration", "مدة", "Duration"],
];
const authorized = (ctx, name) => !ctx.demo && ctx.context.permissions.includes(name);
const today = () => new Date().toISOString().slice(0, 10);

function stateLabel(item) {
  if (item.status === "draft") return L("مسودة — غير مفعلة", "Draft — inactive");
  if (item.effective_until <= today()) return L("مغلق", "Closed");
  if (item.effective_from > today()) return L("مجدول", "Scheduled");
  return L("مفعّل", "Active");
}

function labeledField(name, label, opts, parent, inputs) {
  const f = field(name, label, opts || {});
  inputs[name] = f.input;
  parent.append(f.wrap);
}

function editor(ctx, section, load, parentPoint = null) {
  if (!authorized(ctx, "reference.write") ||
      !ctx.context.permissions.includes("workspace.super_admin")) return;
  const modifying = Boolean(parentPoint);
  const box = el("section", null, "reference-edit");
  box.append(el("p", modifying ?
    L("تعديل بإصدار جديد؛ القديم لا يُحذف ولا يتغير",
      "Amend by new version; original remains immutable") :
    L("أي بند جديد يُنشأ كمسودة ولا يفعّل تلقائيًا",
      "New input points are drafts, never automatically effective."), "muted"));
  const f = el("form"), grid = el("div", null, "form-grid"), inp = {};
  labeledField("logical_key", L("رمز البند الثابت", "Stable clause key"),
    {value: parentPoint?.logical_key || "", maxLength: 120, pattern: "[A-Za-z0-9_.:-]{1,120}"}, grid, inp);
  labeledField("title", L("عنوان البند", "Clause title"),
    {value: parentPoint?.title || "", maxLength: 200}, grid, inp);
  labeledField("clause_text", L("نص الشرط من الاتفاقية", "Clause as written"),
    {type: "textarea", value: parentPoint?.clause_text || "", maxLength: 2000}, grid, inp);
  labeledField("rule_type", L("نوع الشرط", "Rule type"),
    {options: RULE_TYPES.map(([value, ar, en]) => [value, L(ar, en)]),
     value: parentPoint?.rule_type || "text"}, grid, inp);
  labeledField("provider_code", L("رمز مقدم الخدمة إن انطبق", "Provider code if relevant"),
    {required: section === "tariffs", maxLength: 80, value: parentPoint?.provider_code || ""}, grid, inp);
  labeledField("service_code", L("رمز الخدمة إن انطبق", "Service code if relevant"),
    {required: section === "tariffs", maxLength: 100, value: parentPoint?.service_code || ""}, grid, inp);
  labeledField("amount", L("القيمة الرقمية إن انطبقت", "Numeric value if relevant"),
    {required: section === "tariffs", pattern: "[0-9]+(\\.[0-9]{1,4})?",
     value: parentPoint?.amount || "", maxLength: 32}, grid, inp);
  labeledField("currency", L("العملة عند وجود مبلغ", "Currency for amount"),
    {required: section === "tariffs", pattern: "[A-Z]{3}", maxLength: 3,
     value: parentPoint?.currency || ""}, grid, inp);
  labeledField("effective_from", L("تاريخ بدء السريان", "Effective start"),
    {type: "date", value: modifying ? "" : today()}, grid, inp);
  labeledField("effective_until", L("نهاية السريان (غير شاملة)", "Effective end (exclusive)"),
    {type: "date", value: parentPoint?.effective_until || "9999-12-31"}, grid, inp);
  labeledField("source_document_id", L("معرّف ملف المصدر (اختياري)", "Source document ID (optional)"),
    {required: false, value: "", maxLength: 80}, grid, inp);
  if (modifying) {
    inp.logical_key.readOnly = true;
    inp.provider_code.readOnly = true;
    inp.service_code.readOnly = true;
  }
  if (section === "tariffs" && !modifying) {
    const assignKey = () => {
      const provider = inp.provider_code.value.trim();
      const service = inp.service_code.value.trim();
      if (provider && service) inp.logical_key.value = provider + ":" + service;
    };
    inp.provider_code.addEventListener("change", assignKey);
    inp.service_code.addEventListener("change", assignKey);
  }
  const submit = el("button", L("حفظ المسودة", "Save draft"), "button primary"),
    outcome = el("div");
  submit.type = "submit";
  outcome.setAttribute("aria-live", "polite");
  f.append(grid, submit, outcome);
  f.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    if (!f.reportValidity() || submit.disabled) return;
    const value = Object.fromEntries(Object.entries(inp).map(([key, v]) => [key, v.value.trim()]));
    if (value.effective_from >= value.effective_until) {
      outcome.replaceChildren(errorState(new Error(L("نطاق التاريخ غير صحيح", "Invalid effective period"))));
      return;
    }
    if (section === "tariffs") value.logical_key = value.provider_code + ":" + value.service_code;
    const request = {
      section, logical_key: value.logical_key, title: value.title,
      clause_text: value.clause_text, rule_type: value.rule_type,
      provider_code: value.provider_code || null,
      service_code: value.service_code || null,
      amount: value.amount === "" ? null : value.amount,
      currency: value.currency || null,
      effective_from: value.effective_from,
      effective_until: value.effective_until,
      source_document_id: value.source_document_id || null,
      supersedes_id: parentPoint?.id || null,
    };
    submit.disabled = true;
    outcome.replaceChildren(loading());
    try {
      const result = await ctx.api.request("/api/v1/reference-points", {
        method: "POST", body: request,
      });
      outcome.replaceChildren(details(result));
      toast(L("حُفظت مسودة البند — تنتظر اعتمادًا مستقلاً",
              "Clause draft saved — independent approval required"));
      load();
    } catch (err) {
      outcome.replaceChildren(errorState(err));
    } finally { submit.disabled = false; }
  });
  box.append(f);
  openDrawer(modifying ? L("تعديل البند بإصدار جديد", "New clause version") :
    L("إضافة بند", "Add clause"), box);
}

function approveDialog(ctx, item, reload) {
  if (!authorized(ctx, "reference.approve")) return;
  const n = el("section"), form = el("form"), inp = {}, grid = el("div", null, "form-grid");
  n.append(el("p", L("تفعيل مشروط بموافقة مكتوبة منفصلة. لن ينفذ في بيئة الإنتاج دون تحقق توقيع المؤسسة.",
                   "Activation requires independent written authority and production-bound signature checks.")));
  labeledField("authorization_id", L("معرّف التفويض المكتوب", "Written authorization ID"),
    {maxLength: 120}, grid, inp);
  labeledField("reason", L("مبرر الاعتماد (20 حرفًا على الأقل)", "Approval rationale (20+ chars)"),
    {type: "textarea", maxLength: 500}, grid, inp);
  const submit = el("button", L("طلب التفعيل المعتمد", "Submit governed approval"), "button primary"),
    out = el("div");
  submit.type = "submit";
  form.append(grid, submit, out);
  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    if (!form.reportValidity() || inp.reason.value.trim().length < 20 ||
        !(await confirm(L("هل تملك تفويضًا مستقلاً معتمدًا؟", "Do you have independent written authorization?")))) return;
    submit.disabled = true;
    try {
      const result = await ctx.api.request("/api/v1/reference-points/" + encodeURIComponent(item.id) + "/approve",
        {method:"POST", body:{authorization_id:inp.authorization_id.value.trim(),
                              reason:inp.reason.value.trim()}});
      out.replaceChildren(details(result));
      reload();
    } catch(e) { out.replaceChildren(errorState(e)); }
    finally { submit.disabled = false; }
  });
  n.append(form);
  openDrawer(L("مراجعة اعتماد البند", "Clause approval"), n);
}

function sourceUpload(ctx) {
  if (!authorized(ctx, "ingestion.upload")) return;
  const n = el("div"), form = el("form"),
    input = field("new-reference-source", L("اختر مستند الاتفاقية", "Choose contract source"),
                  {type:"file"}), out = el("div");
  input.input.accept = ".pdf,.csv,.xlsx,.png,.jpg,.jpeg";
  n.append(el("p",
    L("يرفع المستند إلى سجل المصادر الحالي؛ استخرج البنود وراجعها قبل حفظها واعتمادها.",
      "Registers the original source; clauses must be extracted, checked and approved separately.")));
  const submit = el("button", L("تسجيل الملف", "Register document"), "button primary");
  submit.type = "submit";
  form.append(input.wrap, submit, out);
  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const file = input.input.files[0];
    if (!file || file.size === 0 || file.size > 20 * 1024 * 1024) {
      out.replaceChildren(errorState(new Error(L("الملف غير صالح أو كبير", "Invalid or oversized file"))));
      return;
    }
    submit.disabled = true;
    try {
      const result = await ctx.api.request("/api/v1/ingestion/uploads?filename=" +
          encodeURIComponent(file.name), {method:"POST", body:file, raw:true});
      out.replaceChildren(details(result));
      toast(L("سُجّل الملف؛ راجع بنوده قبل اعتمادها", "Source registered; review clauses before activation"));
    } catch(err) { out.replaceChildren(errorState(err)); }
    finally {submit.disabled = false;}
  });
  n.append(form);
  openDrawer(L("إضافة ملف جديد", "Add new source file"), n);
}

export function referencePointsView(ctx) {
  const card = panel(L("سجل بنود المدخلات", "Input clause register"),
    L("افتح أي قسم لعرض نقاطه، وإصداراتها، وتواريخها. لا حذف أو تعديل مباشر للبند المعتمد.",
      "Select an input section for its versioned clauses and validity dates. No deletion of approved history."),
    "policy");
  card.classList.add("reference-point-registry");
  const tabs = el("div", null, "reference-point-tabs"),
    toolbar = el("div", null, "reference-point-toolbar"),
    target = el("div", null, "reference-point-list");
  let section = "contracts";
  const controls = () => {
    toolbar.replaceChildren();
    const upload = button(L("إضافة ملف جديد", "Add source file"),
                          () => sourceUpload(ctx), "button");
    upload.disabled = !authorized(ctx, "ingestion.upload");
    const add = button(L("إضافة بند", "Add clause"),
                       () => editor(ctx, section, refresh), "button primary");
    add.disabled = !authorized(ctx, "reference.write") ||
      !ctx.context.permissions.includes("workspace.super_admin");
    toolbar.append(upload, add);
  };
  async function refresh() {
    target.replaceChildren(loading());
    if (ctx.demo) {
      target.replaceChildren(el("p",
        L("العرض الاصطناعي لا يتضمن بنودًا معتمدة. اعرض هذه الشاشة بعد تسجيل دخول مصرح.",
          "Synthetic mode contains no approved clauses; sign in to view authorized records."),
        "muted"));
      return;
    }
    try {
      const data = await ctx.api.request("/api/v1/reference-points?section=" + encodeURIComponent(section));
      target.replaceChildren();
      if (!data.items.length) target.append(el("p",
        L("لا توجد بنود مسجلة لهذا القسم.", "No clauses recorded in this section."), "muted"));
      const head = el("div", null, "reference-point-heading");
      ["البند", "السريان", "الحالة", "الإجراء"].forEach((x, i) =>
        head.append(el("span", L(x, ["Clause", "Validity", "State", "Action"][i]))));
      target.append(head);
      for (const item of data.items) {
        const r = el("article", null, "reference-point-row");
        const name = el("div"), dateSpan = el("div"), state = el("div"), actions = el("div", null, "reference-row-actions");
        name.append(el("strong", item.title), el("small", item.clause_text),
                    el("small", L("إصدار ", "Version ") + item.version + " · " + item.logical_key));
        dateSpan.append(el("small", item.effective_from + " → " + item.effective_until));
        state.append(badge(stateLabel(item)));
        const inspect = button(L("التفاصيل", "Details"), () =>
            openDrawer(L("مصدر وتاريخ البند", "Clause source and history"), details(item)), "button");
        actions.append(inspect);
        if (item.status === "approved" && item.effective_until > today()) {
          const edit = button(L("تعديل بند", "New version"), () => editor(ctx, section, refresh, item), "button");
          edit.disabled = !authorized(ctx, "reference.write") ||
            !ctx.context.permissions.includes("workspace.super_admin");
          actions.append(edit);
        }
        if (item.status === "draft") {
          const approve = button(L("اعتماد", "Approve"), () => approveDialog(ctx, item, refresh), "button");
          approve.disabled = !authorized(ctx, "reference.approve");
          actions.append(approve);
        }
        r.append(name, dateSpan, state, actions);
        target.append(r);
      }
      if (data.has_more) target.append(el("p",
        L("توجد بنود إضافية؛ يعرض أول 100 بند.", "Additional clauses exist; showing first 100."),
        "muted"));
    } catch(err) {target.replaceChildren(errorState(err, () => void refresh()));}
  }
  for (const [code, ar, en] of SECTIONS) {
    const tab = button(L(ar, en), () => {
      section = code;
      for (const item of tabs.children)
        item.setAttribute("aria-pressed", String(item === tab));
      controls();
      void refresh();
    }, "reference-point-tab");
    tab.setAttribute("aria-pressed", String(code === section));
    tabs.append(tab);
  }
  card.append(tabs, toolbar, target);
  ctx.root.append(card);
  controls();
  void refresh();
}
