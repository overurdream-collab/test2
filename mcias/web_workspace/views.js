import {
  L,
  el,
  icon,
  button,
  link,
  badge,
  panel,
  empty,
  loading,
  errorState,
  field,
  safeId,
  idPattern,
  details,
  display,
  labelFor,
  openDrawer,
  confirm,
  toast,
  table,
  kpi,
  currencyChart,
  groupChart,
  donut,
  preferences,
} from "./ui.js";
import { rbacProvisioning } from "./rbac_provisioning.js";
import { featuresManagement } from "./feature_management.js";
import { inputList } from "./input_list.js";
import { institutionOverview, institutionUsers } from "./institution.js";
import { accessManagement } from "./access_management.js";
import { auditWorkspace, resultReports } from "./audit_workspace.js";
const agentNames = {
  eligibility: ["الأهلية", "Eligibility"],
  tariff: ["التعرفة", "Tariffs"],
  contract: ["العقود", "Contracts"],
  exclusion: ["الاستثناءات", "Exclusions"],
  caps: ["السقوف", "Caps"],
  cost_sharing: ["تقاسم التكلفة", "Cost sharing"],
  duplicates: ["التكرار", "Duplicates"],
  evidence: ["الأدلة", "Evidence"],
};
const dimensions = () => [
  ["provider", L("المزود", "Provider")],
  ["service", L("رمز الخدمة", "Service code")],
  ["month", L("الشهر", "Calendar month")],
];
const indicators = () => [
  ["hold_rate", L("معدل التعليق", "Hold rate")],
  [
    "provider_claimed_share",
    L("حصة المطالبات للمزود", "Provider claimed share"),
  ],
];
const reasons = () => [
  ["NEEDS_SOURCE_REVIEW", L("مراجعة المصدر", "Source review")],
  ["NEEDS_POLICY_REVIEW", L("مراجعة السياسة", "Policy review")],
  ["DATA_QUALITY", L("جودة البيانات", "Data quality")],
  ["CONTEXT_EXPLAINS", L("السياق يفسر الإشارة", "Context explains signal")],
  ["NOT_REPRODUCIBLE", L("غير قابلة للتكرار", "Not reproducible")],
  ["OTHER_REVIEW", L("مراجعة أخرى", "Other review")],
];
export function renderView(ctx) {
  const { root, route } = ctx;
  const kind = route.kind;
  if (kind === 'access-management') { accessManagement(ctx); return; }
  if (kind === 'audit-workspace') { auditWorkspace(ctx); return; }
  if (kind === 'result-reports') { resultReports(ctx); return; }
  if (kind === "institution-users") { institutionUsers(ctx); return; }
  if (['dashboard','admin-overview'].includes(kind) && !ctx.demo) { institutionOverview(ctx); return; }
  if (kind === "rbac-provisioning") { rbacProvisioning(ctx); return; }
  if (kind === "input-list") {
    inputList(ctx);
    return;
  }
  if (kind === "features-management") {
    featuresManagement(ctx);
    return;
  }
  if (kind === "retention") {
    retention(ctx);
    return;
  }
  if (kind === "unavailable") {
    unavailable(ctx);
    return;
  }
  if (kind === "dashboard") {
    dashboard(ctx);
    return;
  }
  if (kind === "admin-overview") {
    adminOverview(ctx);
    return;
  }
  if (["profile", "settings", "help", "mfa", "health"].includes(kind)) {
    general(ctx);
    return;
  }
  if (
    ["analysis", "signals", "simulation", "capabilities", "tasks"].includes(
      kind,
    )
  ) {
    intelligence(ctx);
    return;
  }
  if (["reports"].includes(kind)) {
    reports(ctx);
    return;
  }
  if (
    [
      "claims",
      "batches",
      "documents",
      "ingestion",
      "quarantine",
      "contracts",
      "audits",
      "cases",
      "appeals",
      "users",
    ].includes(kind)
  ) {
    catalog(ctx);
    return;
  }
  if (["claim-detail", "user-detail"].includes(kind)) {
    recordDetail(ctx);
    return;
  }
  lookup(ctx);
}
function allowed(ctx, p) {
  return ctx.context.permissions.includes(p);
}
function actionButton(ctx, label, permission, fn, style = "button") {
  const b = button(label, fn, style);
  if (!allowed(ctx, permission) || ctx.demo) {
    b.disabled = true;
    b.title = ctx.demo
      ? L("العرض الاصطناعي للقراءة فقط", "Synthetic preview is read-only")
      : L("تحتاج صلاحية: ", "Requires permission: ") + permission;
  }
  return b;
}
async function fetchPanel(ctx, target, path, render) {
  target.replaceChildren(loading());
  try {
    const result = await ctx.api.request(path);
    target.replaceChildren();
    render(result);
  } catch (err) {
    if (err.name !== "AbortError")
      target.replaceChildren(
        errorState(err, () => void fetchPanel(ctx, target, path, render)),
      );
  }
}
function operation(
  ctx,
  title,
  description,
  fields,
  permission,
  perform,
  { confirmation = false } = {},
) {
  const card = panel(title, description);
  card.classList.add("form-panel");
  const form = el("form"),
    grid = el("div", null, "form-grid"),
    inputs = {};
  for (const spec of fields) {
    const f = field(spec.name, spec.label, spec);
    inputs[spec.name] = f.input;
    grid.append(f.wrap);
  }
  const controls = el("div", null, "actions"),
    submit = el("button", L("تنفيذ الطلب", "Submit request"), "button primary");
  submit.type = "submit";
  submit.disabled = ctx.demo || !allowed(ctx, permission);
  submit.title = submit.disabled
    ? ctx.demo
      ? L("عرض اصطناعي للقراءة فقط", "Read-only synthetic preview")
      : L("الصلاحية المطلوبة: ", "Required permission: ") + permission
    : "";
  controls.append(submit);
  const result = el("div");
  result.setAttribute("aria-live", "polite");
  form.append(grid, controls, result);
  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    if (!form.reportValidity() || submit.disabled) return;
    if (confirmation && !(await confirm(title))) return;
    submit.disabled = true;
    result.replaceChildren(loading());
    try {
      const values = Object.fromEntries(
        Object.entries(inputs).map(([k, v]) => [k, v.value]),
      );
      const data = await perform(values, inputs);
      result.replaceChildren(
        badge(
          L("تم تسجيل الطلب في الخادم", "Request recorded by server"),
          "success",
        ),
        details(data),
      );
      toast(
        L(
          "اكتمل الطلب؛ راجع النتيجة المسجلة.",
          "Request completed; inspect the recorded result.",
        ),
      );
    } catch (err) {
      if (err.name !== "AbortError") result.replaceChildren(errorState(err));
    } finally {
      submit.disabled = ctx.demo || !allowed(ctx, permission);
    }
  });
  card.append(form);
  return card;
}
const idField = (name, label, value = "") => ({
  name,
  label,
  value,
  pattern: idPattern,
  maxLength: 120,
});
const dateField = (name, label) => ({ name, label, type: "date" });
function unavailable(ctx) {
  const { root, route } = ctx;
  const card = panel(
    L("قدرة غير متاحة في الخادم", "Backend capability unavailable"),
    L(
      "حالة التنفيذ: مخططة، وليست تشغيلية أو معتمدة.",
      "Implementation status: planned, not operational or institutionally approved.",
    ),
    route.icon,
  );
  card.append(
    empty(
      L(
        "هذه المساحة جاهزة للاستكمال",
        "This workspace is ready for implementation",
      ),
      L(route.blocker_ar, route.blocker_en),
      route.icon,
    ),
  );
  const next = el("div", null, "detail-grid");
  for (const [a, b, c, d] of [
    [
      "البيانات والمصادر",
      "Data & sources",
      "يلزم عقد بيانات موثّق وربط الأدلة الأصلية.",
      "A documented data contract and original evidence linkage are required.",
    ],
    [
      "الحسابات والمؤشرات",
      "Calculations & indicators",
      "لا توجد أرقام أو مقارنات قبل توافر البيانات المصرح بها.",
      "No figures or comparisons are shown without authorized data.",
    ],
    [
      "المراجعة والقرارات",
      "Review & decisions",
      "يلزم سجل قرارات وإصدارات وفصل مسؤوليات في الخادم.",
      "Versioned decisions, audit history and separated duties must be enforced by the server.",
    ],
    [
      "التصدير والتقارير",
      "Export & reporting",
      "التصدير محجوب حتى اكتمال API واختبارات الخصوصية.",
      "Export remains unavailable until APIs and privacy checks exist.",
    ],
  ]) {
    const n = el("div", null, "detail");
    n.append(el("h3", L(a, b)), el("p", L(c, d), "muted"));
    next.append(n);
  }
  card.append(next);
  const links = el("div", null, "switch-links");
  links.append(
    link(
      L("القدرات المتاحة", "Available capabilities"),
      ctx.scope === "admin" ? "/admin/dashboard" : "/institution/dashboard",
    ),
    link(L("دليل التغطية والمساعدة", "Coverage & help"), "/shared/help"),
  );
  card.append(links);
  root.append(card);
}
function general(ctx) {
  const { root, route, context } = ctx;
  if (route.kind === "help") {
    const card = panel(
      L("إرشادات العمل والتحقق", "Working & verification guidance"),
      L(
        "كل بوابات G0–G9 ما زالت غير معتمدة مؤسسيًا.",
        "All G0–G9 gates remain institutionally unaccepted.",
      ),
      "reports",
    );
    for (const [a, b] of [
      [
        "اختر لقطة تقرير ثابتة لعرض مؤشرات مالية. كل عملة مستقلة؛ الخصومات ليست وفورات محتملة.",
        "Select a frozen report snapshot for financial metrics. Currencies remain separate; deductions are not potential savings.",
      ],
      [
        "اضغط «عرض الدليل» لفتح البصمة ومرجع المصدر ونتائج المراجعة.",
        "Use View evidence to inspect fingerprints, source references and review results.",
      ],
      [
        "الجلسة محفوظة في ذاكرة الصفحة فقط؛ التحديث أو الخروج يتطلب دخولًا جديدًا.",
        "The session exists only in page memory. Reloading or signing out requires a new login.",
      ],
      [
        "تبديل المؤسسة غير متاح: كل مؤسسة لها تثبيت وقاعدة بيانات محلية منفصلة.",
        "Tenant switching is unavailable: each organization has its own local installation and database.",
      ],
      [
        "الإشارات التحليلية للمراجعة البشرية؛ لا تمثل حكمًا بالاحتيال أو قرارًا طبيًا أو أمر دفع.",
        "Analysis signals require human review and are not fraud verdicts, medical decisions or payment instructions.",
      ],
      [
        "الميزات الموسومة «غير متاحة» لا تملك API تشغيلية. العمليات المتاحة تخضع للصلاحيات والأدلة وفصل المسؤوليات.",
        "Features labeled Unavailable lack an operational API. Available operations remain subject to permissions, evidence and separation of duties.",
      ],
    ]) {
      const n = el("div", null, "finding");
      n.append(el("p", L(a, b)));
      card.append(n);
    }
    root.append(card);
    return;
  }
  if (route.kind === "health") {
    const card = panel(
      L("فحوص الاتصال", "Connectivity checks"),
      L(
        "توافر API وقاعدة البيانات لا يثبت جاهزية الإنتاج أو نجاح النسخ الاحتياطي.",
        "API and database reachability do not establish production readiness or successful backups.",
      ),
      "settings",
    );
    const result = el("div");
    card.append(
      result,
      button(
        L("تحديث الحالة", "Refresh status"),
        () => void check(),
        "button",
        "refresh",
      ),
    );
    async function check() {
      result.replaceChildren(loading());
      const results = await Promise.allSettled(
        ["/health/live", "/health/ready"].map((p) => ctx.api.request(p)),
      );
      result.replaceChildren();
      results.forEach((r, i) => {
        const row = el("div", null, "finding");
        row.append(
          el(
            "h3",
            i === 0
              ? L("خدمة التطبيق", "Application service")
              : L("اتصال قاعدة البيانات", "Database connectivity"),
          ),
          r.status === "fulfilled" ? details(r.value) : errorState(r.reason),
        );
        result.append(row);
      });
    }
    void check();
    root.append(card);
    return;
  }
  if (route.kind === "mfa") {
    const info = panel(
      L("التحقق متعدد العوامل", "Multi-factor authentication"),
      L(
        "التسجيل والتأكيد يستخدمان الخادم. يتطلب الحساب الإداري تهيئة آمنة مسبقة؛ لا توفر الواجهة تجاوزًا للتحقق.",
        "Enrollment and confirmation use the backend. Administrative accounts require secure bootstrap; this interface provides no MFA bypass.",
      ),
      "security",
    );
    root.append(info);
    root.append(
      operation(
        ctx,
        L("بدء تسجيل عامل TOTP", "Start TOTP enrollment"),
        L(
          "أدخل كلمة المرور الحالية. احتفظ بسر التسجيل داخل المؤسسة.",
          "Enter your current password. Keep enrollment secrets on premises.",
        ),
        [
          {
            name: "current_password",
            label: L("كلمة المرور الحالية", "Current password"),
            type: "password",
            maxLength: 1024,
          },
        ],
        "profile.read",
        async (v, inputs) => {
          try {
            return await ctx.api.request("/api/v1/auth/mfa/enroll", {
              method: "POST",
              body: v,
            });
          } finally {
            inputs.current_password.value = "";
          }
        },
      ),
    );
    root.append(
      operation(
        ctx,
        L("تأكيد عامل التحقق", "Confirm MFA factor"),
        L(
          "سيُلغي الخادم الجلسات السابقة بعد التأكيد؛ سجّل الدخول مجددًا.",
          "The server revokes prior sessions after confirmation. Sign in again.",
        ),
        [
          {
            name: "current_password",
            label: L("كلمة المرور الحالية", "Current password"),
            type: "password",
            maxLength: 1024,
          },
          {
            name: "code",
            label: L("رمز TOTP", "TOTP code"),
            pattern: "[0-9]{6}",
            maxLength: 6,
          },
        ],
        "profile.read",
        async (v, inputs) => {
          try {
            const data = await ctx.api.request("/api/v1/auth/mfa/confirm", {
              method: "POST",
              body: v,
            });
            setTimeout(ctx.signOutLocal, 0);
            return data;
          } finally {
            inputs.current_password.value = "";
            inputs.code.value = "";
          }
        },
        { confirmation: true },
      ),
    );
    return;
  }
  const card = panel(
    route.kind === "settings"
      ? L("تفضيلات مساحة العمل", "Workspace preferences")
      : L("هوية الجلسة الحالية", "Current session identity"),
    L(
      "صلاحيات فعلية من الخادم؛ لا يوجد منح افتراضي أو تبديل مؤسسات.",
      "Effective permissions from the backend; no default grants or tenant switching.",
    ),
    "security",
  );
  card.append(
    details({
      id: context.id,
      username: context.username,
      organization: context.organization,
      roles: context.roles,
      permissions: context.permissions,
      expires_at: context.expires_at,
      institutionally_accepted: false,
    }),
  );
  if (route.kind === "settings") {
    const controls = el("div", null, "switch-links");
    controls.append(
      button(L("العربية / English", "English / العربية"), ctx.toggleLanguage),
      button(L("تبديل الثيم", "Switch theme"), ctx.toggleTheme),
    );
    card.append(
      controls,
      el(
        "p",
        L(
          "إدارة الاستحقاقات والإعدادات التشغيلية وتاريخ إعدادات المنصة غير متاحة عبر API.",
          "Entitlement management, operational settings and platform configuration history are unavailable through an API.",
        ),
        "auth-note",
      ),
    );
  }
  root.append(card);
}
function adminOverview(ctx) {
  const hero = el("section", null, "hero");
  const text = el("div");
  text.append(
    badge(
      L(
        "الإدارة المركزية · وصول محكوم",
        "Central administration · governed access",
      ),
    ),
    el(
      "h2",
      L(
        "بيئة آمنة لبيانات موثوقة وقرارات قابلة للتتبع",
        "A secure foundation for trusted data and traceable decisions",
      ),
    ),
    el(
      "p",
      L(
        "العمليات المتاحة ضمن تثبيت المؤسسة الحالي. التغييرات المالية لا تتجاوز الموافقة المستقلة.",
        "Available operations are scoped to this organization installation. Financial changes require independent approval.",
      ),
    ),
  );
  hero.append(text, icon("security"));
  ctx.root.append(hero);
  const kpis = el("div", null, "grid kpis");
  kpis.append(
    kpi(
      L("الصلاحيات الفعلية", "Effective permissions"),
      String(ctx.context.permissions.length),
      "security",
      L("من سياق الجلسة", "From session context"),
      "/admin/permissions",
    ),
    kpi(
      L("المؤسسة الحالية", "Current organization"),
      ctx.context.organization ? L("مؤسسة واحدة", "One organization") : "—",
      "hospitals",
      L("لا يوجد تبديل قواعد بيانات", "Database switching unavailable"),
      "/admin/organizations",
    ),
    kpi(
      L("الاعتماد المؤسسي", "Institutional acceptance"),
      L("معلّق", "Pending"),
      "policy",
      L("G0–G9 غير معتمدة", "G0–G9 unaccepted"),
      "/shared/help",
    ),
    kpi(
      L("المهام المحكومة", "Governed tasks"),
      "—",
      "ai",
      L("تُقرأ حسب الصلاحية", "Loaded subject to permission"),
      "/admin/analysis-tasks",
    ),
  );
  ctx.root.append(kpis);
  const grid = el("div", null, "grid feature-grid");
  for (const path of [
    "/admin/ingestion",
    "/admin/analysis-tasks",
    "/admin/financial-policies",
    "/admin/reference-data",
    "/admin/security",
    "/admin/system-health",
  ]) {
    const r = ctx.routes.find((x) => x.path === path);
    const a = link("", path, "feature-card");
    a.append(
      icon(r.icon),
      el("h3", L(r.ar, r.en)),
      el(
        "p",
        L(
          "قدرات الخادم، الأدلة وضوابط الوصول",
          "Backend capabilities, evidence and access controls",
        ),
      ),
      badge(L("تنفيذ جزئي · غير معتمد", "Partial · unaccepted"), "warning"),
    );
    grid.append(a);
  }
  ctx.root.append(grid);
}
function dashboard(ctx) {
  const source = panel(
      L("نطاق التقرير", "Report scope"),
      L(
        "لقطة ثابتة واحدة؛ لا نجمع إصدارات التقرير ولا نخلط العملات.",
        "One frozen snapshot; report versions and currencies are never combined.",
      ),
      "reports",
    ),
    target = el("div");
  source.append(target);
  ctx.root.append(source);
  const output = el("div");
  output.className = "form-panel";
  ctx.root.append(output);
  void fetchPanel(
    ctx,
    target,
    "/api/v1/report-explorer/snapshots?limit=25",
    (data) => {
      if (!data.items.length) {
        target.append(
          empty(
            L("لا توجد تقارير ثابتة", "No frozen reports"),
            L(
              "أنشئ تقريرًا من دفعة مستوردة بالكامل، ضمن صلاحياتك.",
              "Create a report from a fully imported batch under your permissions.",
            ),
          ),
        );
        return;
      }
      const f = field("snapshot", L("لقطة التقرير", "Report snapshot"), {
        options: data.items.map((x) => [
          x.id,
          L("الإصدار ", "Version ") +
            x.version +
            " · " +
            x.batch_id.slice(0, 8),
        ]),
      });
      const filter = el("div", null, "filters");
      filter.append(
        f.wrap,
        link(
          L("جميع التقارير", "All reports"),
          "/institution/reports",
          "button",
        ),
      );
      target.append(filter);
      const selected = () => {
        const item = data.items.find((x) => x.id === f.input.value);
        draw(item);
      };
      f.input.addEventListener("change", selected);
      selected();
    },
  );
  function draw(report) {
    output.replaceChildren();
    const summary = report.summary,
      totals = summary.by_currency;
    const hero = el("section", null, "hero"),
      text = el("div");
    text.append(
      badge(
        L(
          "ذكاء تنفيذي قائم على الأدلة",
          "Evidence-backed executive intelligence",
        ),
      ),
      el(
        "h2",
        L(
          "رؤية واضحة للإنفاق ومراجعة مالية موثّقة",
          "Clear expenditure visibility and evidenced financial review",
        ),
      ),
      el(
        "p",
        L(
          "المؤشرات مستمدة من لقطة موثقة؛ المستحق المعتمد يتطلب تدقيق G5 وموافقة G6 محفوظة.",
          "Metrics come from a frozen snapshot. Approved payable requires preserved G5 verification and G6 approval.",
        ),
      ),
    );
    hero.append(text, icon("dashboard"));
    output.append(hero);
    const currencies = Object.entries(totals);
    const filters = el("div", null, "filters");
    const cf = field("currency", L("عملة التقرير", "Report currency"), {
      options: currencies.map(([c]) => [c, c]),
    });
    filters.append(
      cf.wrap,
      el(
        "p",
        L(
          "الفترة وآخر مزامنة ناجحة غير متاحتين في بيانات التقرير الحالية؛ لا تُعرض مقارنات زمنية.",
          "Reporting period and last successful synchronization are unavailable in current report metadata. No period comparisons are displayed.",
        ),
        "filter-note",
      ),
    );
    output.append(filters);
    const metrics = el("div", null, "grid kpis");
    output.append(metrics);
    const charts = el("div", null, "grid analytics");
    const financial = panel(
      L("المطالب به مقابل المستحق", "Claimed vs verified payable"),
      L("قيم الخادم بحسب العملة", "Backend values by currency"),
    );
    financial.append(
      currencyChart(
        totals,
        (currency) => void reportEntries(ctx, report.id, 0, "", currency),
      ),
    );
    const legend = el("div", null, "legend");
    for (const [cls, ar, en] of [
      ["claimed", "المطالب به", "Claimed"],
      ["payable", "المستحق", "Verified payable"],
    ]) {
      const span = el("span");
      span.append(el("i", null, cls), document.createTextNode(L(ar, en)));
      legend.append(span);
    }
    financial.append(
      legend,
      el(
        "p",
        L(
          "لا يمثل الفرق وفورات محتملة؛ المطالبات المعلّقة غير محسومة.",
          "The difference is not potential savings; held claims remain unsettled.",
        ),
        "chart-note",
      ),
    );
    const status = panel(
      L("حالة مراجعة المطالبات", "Claims review status"),
      L("من لقطة التقرير المحددة", "From the selected snapshot"),
    );
    charts.append(financial, status);
    output.append(charts);
    function currency() {
      const [c, v] = currencies.find(
        ([currency]) => currency === cf.input.value,
      ) ||
        currencies[0] || ["—", {}];
      metrics.replaceChildren(
        kpi(
          L("إجمالي المطالب به", "Total claimed"),
          display(v.claimed),
          "claims",
          c + "/ G7",
          "/institution/reports",
        ),
        kpi(
          L("المستحق الموثق", "Verified payable"),
          display(v.payable),
          "audit",
          c + "/ G5 + G6",
          "/institution/financial-audit",
        ),
        kpi(
          L("الخصومات المعتمدة", "Approved deductions"),
          display(v.deductions),
          "policy",
          c + "/ G7",
          "/institution/reports",
        ),
        kpi(
          L("مطالبات معلّقة", "Held claims"),
          display(v.held_count),
          "beneficiaries",
          L("ضمن العملة المختارة", "Within selected currency"),
          "/institution/reviews",
        ),
      );
      status.replaceChildren(
        status.firstChild,
        donut(
          (v.approved_count || 0) + (v.held_count || 0),
          v.approved_count || 0,
          v.held_count || 0,
        ),
      );
    }
    cf.input.addEventListener("change", currency);
    currency();
    const exact = panel(
      L("القيم الدقيقة ومصدر البيانات", "Exact values & provenance"),
      L(
        "عرض كامل للعملات دون تقريب أو تحويل",
        "All currencies without rounding or conversion",
      ),
    );
    const exactTable = el("div");
    table(
      exactTable,
      currencies.map(([currency, v]) => ({ currency, ...v })),
      {
        columns: [
          "currency",
          "claimed",
          "payable",
          "deductions",
          "approved_count",
          "held_count",
        ],
        caption: L("إجماليات G7 المسترجعة", "Retrieved G7 totals"),
      },
    );
    exact.append(
      exactTable,
      el(
        "p",
        "G7 / " +
          report.id +
          " / v" +
          report.version +
          " / SHA-256 " +
          report.fingerprint +
          " / Source " +
          report.source_sha256,
        "provenance",
      ),
    );
    const browse = button(
      L("المطالبات والأدلة المرتبطة", "Linked claims & evidence"),
      () => void reportEntries(ctx, report.id),
    );
    exact.append(browse);
    output.append(exact);
  }
}
function reports(ctx) {
  const card = panel(
      L("سجل التقارير الثابتة", "Frozen report register"),
      L(
        "كل إصدار محفوظ ببصمة؛ التنزيل يمر عبر التفويض في الخادم.",
        "Each version has a fingerprint. Downloads pass through backend authorization.",
      ),
      "reports",
    ),
    target = el("div");
  card.append(target);
  ctx.root.append(card);
  function load(offset = 0) {
    void fetchPanel(
      ctx,
      target,
      "/api/v1/report-explorer/snapshots?limit=25&offset=" + offset,
      (data) => {
        table(target, data.items, {
          columns: ["id", "batch_id", "version", "fingerprint"],
          offset,
          hasMore: data.has_more,
          onPage: load,
          open: (r) => {
            const content = el("div");
            content.append(details(r));
            const actions = el("div", null, "switch-links");
            actions.append(
              button(
                L("استعراض المطالبات", "Browse claims"),
                () => void reportEntries(ctx, r.id),
              ),
              actionButton(
                ctx,
                "Excel",
                "reports.export",
                () => void download("excel"),
              ),
              actionButton(
                ctx,
                "PDF",
                "reports.export",
                () => void download("pdf"),
              ),
            );
            content.append(actions);
            openDrawer(L("تفاصيل التقرير", "Report details"), content);
            async function download(format) {
              try {
                await ctx.api.download(
                  "/api/v1/reports/snapshots/" +
                    safeId(r.id) +
                    "/" +
                    format +
                    "?lang=" +
                    preferences.lang,
                  "mcias-" + r.id + "." + (format === "excel" ? "xlsx" : "pdf"),
                );
                toast(
                  L("تم تنزيل التقرير المصرّح", "Authorized report downloaded"),
                );
              } catch (err) {
                toast(err.message);
              }
            }
          },
        });
        if (!data.items.length)
          target.append(
            empty(
              L("لا توجد تقارير", "No reports"),
              L("لا توجد لقطات في هذه الصفحة.", "No snapshots on this page."),
            ),
          );
      },
    );
  }
  load();
  if (allowed(ctx, "reports.create"))
    ctx.root.append(
      operation(
        ctx,
        L("إنشاء لقطة تقرير", "Create report snapshot"),
        L(
          "تُجمّد الدفعة المستوردة بالكامل؛ الحسابات تأتي من الخادم.",
          "Freezes a fully imported batch; calculations come from the backend.",
        ),
        [idField("batch_id", L("معرّف الدفعة", "Batch ID"))],
        "reports.create",
        (v) =>
          ctx.api.request(
            "/api/v1/reports/batches/" + safeId(v.batch_id) + "/snapshots",
            { method: "POST" },
          ),
        { confirmation: true },
      ),
    );
  if (
    allowed(ctx, "reports.beneficiary.read") &&
    allowed(ctx, "medical_fields.beneficiary_token.read")
  )
    ctx.root.append(
      operation(
        ctx,
        L("كشف مستفيد مصرح", "Authorized beneficiary statement"),
        L(
          "تتطلب صلاحية الحقل الطبي؛ لا تُصدّر الحقول الأصلية تلقائيًا.",
          "Requires sensitive-field permission; original fields are never exported automatically.",
        ),
        [
          idField("report_id", L("التقرير", "Report ID")),
          {
            name: "beneficiary_token",
            label: L("رمز المستفيد", "Beneficiary token"),
            maxLength: 128,
          },
        ],
        "reports.beneficiary.read",
        (v) =>
          ctx.api.request(
            "/api/v1/reports/snapshots/" +
              safeId(v.report_id) +
              "/beneficiary-statement",
            {
              method: "POST",
              body: { beneficiary_token: v.beneficiary_token },
            },
          ),
      ),
    );
}
async function reportEntries(ctx, id, offset = 0, state = "", currency = "") {
  const content = panel(
      L("مطالبات التقرير", "Report claims"),
      L(
        "عرض محكوم دون حقول مصدر طبية خام",
        "Governed view without raw medical source fields",
      ),
    ),
    filters = el("div", null, "filters");
  const sf = field("state", L("الحالة", "State"), {
      value: state,
      required: false,
      options: [
        ["", L("الكل", "All")],
        ["approved", L("معتمد", "Approved")],
        ["held", L("معلّق", "Held")],
      ],
    }),
    cf = field("currency", L("العملة (ISO)", "Currency (ISO)"), {
      value: currency,
      required: false,
      pattern: "[A-Z]{3}",
      maxLength: 3,
    });
  filters.append(
    sf.wrap,
    cf.wrap,
    button(L("تطبيق", "Apply"), () => {
      if (cf.input.reportValidity())
        void reportEntries(ctx, id, 0, sf.input.value, cf.input.value);
    }),
  );
  content.append(filters);
  const target = el("div");
  content.append(target);
  openDrawer(L("أدلة التقرير", "Report evidence"), content);
  const query = new URLSearchParams({ limit: "25", offset: String(offset) });
  if (state) query.set("state", state);
  if (currency) query.set("currency", currency);
  await fetchPanel(
    ctx,
    target,
    "/api/v1/report-explorer/snapshots/" + safeId(id) + "/entries?" + query,
    (data) => {
      table(target, data.items, {
        columns: [
          "claim_id",
          "currency",
          "claimed",
          "state",
          "payable",
          "hold_reason",
        ],
        offset,
        hasMore: offset + data.items.length < data.total,
        onPage: (o) => void reportEntries(ctx, id, o, state, currency),
        open: (r) => {
          const n = el("div");
          n.append(details(r));
          if (r.audit_snapshot_id)
            n.append(
              button(
                L("لقطة التدقيق", "Audit snapshot"),
                () => void auditDetail(ctx, r.audit_snapshot_id),
              ),
            );
          if (r.governance_case_id)
            n.append(
              button(
                L("تاريخ المراجعة", "Review history"),
                () => void caseDetail(ctx, r.governance_case_id),
              ),
            );
          openDrawer(L("أدلة المطالبة", "Claim evidence"), n);
        },
      });
    },
  );
}
function catalog(ctx) {
  const { root, route } = ctx;
  const mapping = { ingestion: "jobs", quarantine: "jobs", appeals: "cases" };
  const kind = mapping[route.kind] || route.kind;
  const card = panel(
      L("سجلات المؤسسة الحالية", "Current organization records"),
      L(
        "بيانات مصرح بها، قراءة محدودة وتتبّع للمصدر.",
        "Authorized data, bounded reads and source traceability.",
      ),
      route.icon,
    ),
    target = el("div");
  card.append(target);
  root.append(card);
  function load(offset = 0) {
    void fetchPanel(
      ctx,
      target,
      "/api/v1/workspace/catalog/" + kind + "?limit=25&offset=" + offset,
      (data) => {
        table(target, data.items, {
          offset,
          hasMore: data.has_more,
          onPage: load,
          open: (r) => {
            if (kind === "audits") {
              void auditDetail(ctx, r.id);
              return;
            }
            if (kind === "cases") {
              void caseDetail(ctx, r.id);
              return;
            }
            if (kind === "claims") {
              ctx.navigate("/institution/claims/" + safeId(r.id));
              return;
            }
            if (kind === "batches") {
              void batchDetail(ctx, r.id);
              return;
            }
            if (kind === "documents") {
              void documentDetail(ctx, r.id);
              return;
            }
            if (kind === "jobs") {
              void jobDetail(ctx, r.id);
              return;
            }
            openDrawer(L("تفاصيل السجل", "Record details"), details(r));
          },
        });
        if (!data.items.length)
          target.append(
            empty(
              L("لا توجد سجلات في هذه الصفحة", "No records on this page"),
              L(
                "لم يُرجع الخادم بيانات؛ لا توجد إحصاءات تقديرية.",
                "The backend returned no data; no estimated statistics are shown.",
              ),
              route.icon,
            ),
          );
        target.append(
          el(
            "p",
            L("وقت قراءة الصفحة: ", "Page retrieved at: ") +
              (data.retrieved_at || L("عرض اصطناعي", "Synthetic preview")) +
              " · " +
              L("ليس وقت آخر مزامنة", "Not the last synchronization time"),
            "chart-note",
          ),
        );
      },
    );
  }
  load();
  if (kind === "jobs") {
    const flow = el("div", null, "flow");
    for (const [a, b] of [
      ["رفع المصدر", "Upload"],
      ["التسجيل", "Register"],
      ["الاستخراج", "Extract"],
      ["التحقق / الحجر", "Validate / quarantine"],
      ["التطبيع", "Normalize"],
      ["الربط المرجعي", "Reference linking"],
      ["استيراد المطالبات", "Claims import"],
      ["جاهزية التدقيق", "Audit readiness"],
    ])
      flow.append(el("span", L(a, b)));
    root.append(flow);
  }
  if (route.kind === "ingestion" && allowed(ctx, "ingestion.upload")) {
    const card = panel(
        L("رفع مصدر أصلي", "Upload original source"),
        L(
          "Excel، CSV، PDF، PNG، JPEG حتى 20 MiB. يحفظ الخادم الأصل والبصمة ويقرر الاستخراج أو الحجر.",
          "Excel, CSV, PDF, PNG, JPEG up to 20 MiB. The backend preserves originals and fingerprints and decides extraction or quarantine.",
        ),
        "ingestion",
      ),
      form = el("form"),
      f = field("source-file", L("المستند المصدر", "Source document"), {
        type: "file",
      });
    f.input.accept = ".xlsx,.csv,.pdf,.png,.jpg,.jpeg";
    const submit = el(
      "button",
      L("رفع وتسجيل المصدر", "Upload & register source"),
      "button primary",
    );
    submit.type = "submit";
    submit.disabled = ctx.demo;
    const output = el("div");
    output.setAttribute("aria-live", "polite");
    form.append(f.wrap, submit, output);
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      if (submit.disabled) return;
      const file = f.input.files[0];
      if (!file || file.size === 0 || file.size > 20 * 1024 * 1024) {
        output.replaceChildren(
          errorState(
            new Error(
              L(
                "اختر ملفًا غير فارغ لا يتجاوز 20 MiB",
                "Select a nonempty file no larger than 20 MiB",
              ),
            ),
          ),
        );
        return;
      }
      submit.disabled = true;
      output.replaceChildren(loading());
      try {
        const data = await ctx.api.request(
          "/api/v1/ingestion/uploads?filename=" + encodeURIComponent(file.name),
          { method: "POST", body: file, raw: true },
        );
        output.replaceChildren(details(data));
        f.input.value = "";
        load();
      } catch (err) {
        output.replaceChildren(errorState(err));
      } finally {
        submit.disabled = ctx.demo;
      }
    });
    card.append(form);
    root.append(card);
  }
  if (kind === "batches" && allowed(ctx, "claims.import")) {
    root.append(
      operation(
        ctx,
        L("تجهيز دفعة من مصدر موثّق", "Stage batch from verified source"),
        L(
          "استخدم معرّف المستند المسجل. الخادم يفرض سلامة المصدر والمؤسسة.",
          "Use a registered document ID. The backend enforces source integrity and tenant scope.",
        ),
        [idField("document_id", L("المستند", "Document ID"))],
        "claims.import",
        (v) =>
          ctx.api.request(
            "/api/v1/claims/batches/from-document/" + safeId(v.document_id),
            { method: "POST" },
          ),
      ),
    );
    root.append(
      operation(
        ctx,
        L("استئناف استيراد الدفعة", "Resume batch import"),
        L(
          "استيراد قابل للاستئناف دون تكرار سجلات مالية.",
          "Resumable import without duplicate financial records.",
        ),
        [
          idField("batch_id", L("الدفعة", "Batch ID")),
          {
            name: "chunk_size",
            label: L("حجم الجزء", "Chunk size"),
            type: "number",
            min: 1,
            max: 1000,
            value: 100,
          },
        ],
        "claims.import",
        (v) =>
          ctx.api.request(
            "/api/v1/claims/batches/" +
              safeId(v.batch_id) +
              "/resume?chunk_size=" +
              v.chunk_size,
            { method: "POST" },
          ),
        { confirmation: true },
      ),
    );
  }
  if (kind === "claims" && allowed(ctx, "claims.import"))
    root.append(
      operation(
        ctx,
        L("ربط دليل بمطالبة", "Link claim evidence"),
        L(
          "ربط مستند موثّق دون تعديل أعمدة المطالبة الأصلية.",
          "Links a verified document without changing original claim fields.",
        ),
        [
          idField("claim_id", L("المطالبة", "Claim ID")),
          idField("document_id", L("المستند", "Document ID")),
        ],
        "claims.import",
        (v) =>
          ctx.api.request(
            "/api/v1/claims/entries/" +
              safeId(v.claim_id) +
              "/attachments/" +
              safeId(v.document_id),
            { method: "POST" },
          ),
      ),
    );
  if (kind === "audits") {
    root.append(
      el(
        "p",
        L(
          "لا توجد عملية تنفيذ تدقيق إنتاجي في API. النتائج أدناه من لقطات الخادم غير القابلة للتعديل.",
          "There is no production audit execution API. Results below come from immutable backend snapshots.",
        ),
        "auth-note",
      ),
    );
    const grid = el("div", null, "grid feature-grid");
    for (const names of Object.values(agentNames)) {
      const p = panel(
        L(...names),
        L(
          "تُعرض الحالة والسبب والسياسة والمرجع داخل لقطة التدقيق.",
          "Status, reason, policy and evidence are shown within the audit snapshot.",
        ),
      );
      p.append(badge(L("بانتظار اختيار لقطة", "Awaiting snapshot selection")));
      grid.append(p);
    }
    root.append(grid);
  }
  if (kind === "cases") {
    root.append(
      operation(
        ctx,
        L("فتح حالة مراجعة", "Open review case"),
        L(
          "تتطلب لقطة تدقيق موجودة. التعيين والتصعيد والتعليقات الحرة غير متاحة.",
          "Requires an existing audit snapshot. Assignment, escalation and free-text comments are unavailable.",
        ),
        [idField("snapshot_id", L("لقطة التدقيق", "Audit snapshot ID"))],
        "claims.read",
        (v) =>
          ctx.api.request(
            "/api/v1/governance/cases/from-audit/" + safeId(v.snapshot_id),
            { method: "POST" },
          ),
      ),
    );
  }
  if (kind === "contracts") {
    referenceForms(ctx);
  }
  if (kind === "users")
    root.append(
      el(
        "p",
        L(
          "قائمة للمؤسسة الحالية فقط. إنشاء المستخدمين وتعديلهم وتعطيلهم غير متاح عبر API.",
          "Current organization only. User creation, editing and deactivation are unavailable through an API.",
        ),
        "auth-note",
      ),
    );
}
async function batchDetail(ctx, id, offset = 0) {
  const n = panel(
      L("تفاصيل الدفعة", "Batch detail"),
      L(
        "الأصل محفوظ؛ التصفية على الصفحة الحالية.",
        "Originals are preserved; filtering applies to this page.",
      ),
    ),
    target = el("div");
  n.append(target);
  openDrawer(L("دفعة المطالبات", "Claim batch"), n);
  await fetchPanel(
    ctx,
    target,
    "/api/v1/claims/batches/" + safeId(id),
    (meta) => {
      target.append(details(meta));
      const rows = el("div");
      target.append(rows);
      void fetchPanel(
        ctx,
        rows,
        "/api/v1/claims/batches/" +
          safeId(id) +
          "/entries?limit=25&offset=" +
          offset,
        (data) => {
          table(rows, data.entries, {
            offset,
            hasMore: offset + data.entries.length < meta.imported_count,
            onPage: (o) => void batchDetail(ctx, id, o),
            open: (r) => ctx.navigate("/institution/claims/" + safeId(r.id)),
          });
        },
      );
    },
  );
}
async function documentDetail(ctx, id) {
  const n = panel(
      L("مصدر ثابت", "Immutable source"),
      L(
        "عرض البصمة وسجل الاكتمال. تنزيل الأصل محجوب لعدم وجود API تنزيل مصرح.",
        "Fingerprint and completeness manifest. Original download is unavailable without an authorized download API.",
      ),
    ),
    target = el("div");
  n.append(target);
  openDrawer(L("مركز الأدلة", "Evidence center"), n);
  await fetchPanel(
    ctx,
    target,
    "/api/v1/ingestion/documents/" + safeId(id) + "/manifest",
    (data) => target.append(details(data)),
  );
}
async function jobDetail(ctx, id) {
  const n = panel(
      L("الاستخراج والحجر", "Extraction & quarantine"),
      L(
        "الأسباب ومواضع المصدر من الخادم. مراجعة الحجر وإعادة المعالجة متاحتان في الخادم ولم تُدمجا بعد في هذه الشاشة.",
        "Reasons and source locators come from the backend. Quarantine review and reprocessing APIs exist but are not integrated in this screen.",
      ),
    ),
    target = el("div"),
    quarantine = el("div");
  n.append(target, quarantine);
  openDrawer(L("متابعة الاستيعاب", "Ingestion monitoring"), n);
  await fetchPanel(
    ctx,
    target,
    "/api/v1/ingestion/jobs/" + safeId(id),
    (data) => target.append(details(data)),
  );
  await fetchPanel(
    ctx,
    quarantine,
    "/api/v1/ingestion/jobs/" + safeId(id) + "/quarantine",
    (data) => {
      if (data.items.length) quarantine.append(details(data));
      else
        quarantine.append(
          empty(
            L("لا توجد عناصر محجورة", "No quarantined items"),
            L(
              "أرجع الخادم قائمة فارغة لهذه المهمة.",
              "The backend returned an empty quarantine list for this job.",
            ),
            "ingestion",
            true,
          ),
        );
    },
  );
}
async function auditDetail(ctx, id) {
  const n = panel(
      L("لقطة تدقيق غير قابلة للتعديل", "Immutable audit snapshot"),
      L(
        "نتيجة قاعدة حتمية وليست قرارًا ماليًا نهائيًا؛ الاعتماد المؤسسي مستقل.",
        "A deterministic rule result, not a final financial decision. Institutional acceptance remains separate.",
      ),
    ),
    target = el("div");
  n.append(target);
  openDrawer(L("التدقيق المالي · G5", "Financial audit · G5"), n);
  await fetchPanel(ctx, target, "/api/v1/audits/" + safeId(id), (data) => {
    target.append(
      details({
        id: data.id,
        claim_id: data.claim_id,
        policy_id: data.policy_id,
        policy_fingerprint: data.policy_fingerprint,
      }),
    );
    const calc = data.calculation || {},
      finance = panel(
        L("التفصيل المالي والمطابقة", "Financial breakdown & reconciliation"),
        L(
          "مبالغ عشرية مسترجعة دون إعادة حساب في المتصفح",
          "Backend decimal amounts without browser recalculation",
        ),
      );
    finance.append(
      details({
        status: calc.status,
        claimed: calc.claimed,
        currency: calc.currency,
        total_deduction: calc.total_deduction,
        payable: calc.payable,
      }),
    );
    for (const step of calc.deductions || []) finance.append(details(step));
    finance.append(details({ verification: data.verification }));
    target.append(finance);
    const findings = el("div");
    for (const [key, names] of Object.entries(agentNames)) {
      const f = (data.findings?.agents || []).find((x) => x.agent === key),
        card = el("article", null, "finding");
      card.append(
        el("h3", L(...names)),
        badge(
          f ? display(f.status) : L("غير موجود في اللقطة", "Not in snapshot"),
          f?.status === "pass" ? "success" : "warning",
        ),
      );
      if (f)
        card.append(
          details({
            reason: f.reason,
            reference: f.reference,
            policy_id: data.policy_id,
          }),
        );
      else
        card.append(
          el(
            "p",
            L(
              "لا توجد نتيجة مسجلة؛ لا نفترض النجاح.",
              "No recorded result; no pass is inferred.",
            ),
          ),
        );
      findings.append(card);
    }
    target.append(
      findings,
      el(
        "p",
        L(
          "المراجع وأسباب الوكلاء أدلة محفوظة كما أعادها الخادم. تقييم الثقة أو التكليف أو القرار النهائي لا يُستنتج من هذه النتائج.",
          "References and agent reasons are preserved as returned by the backend. Confidence, assignment and final disposition are not inferred.",
        ),
        "chart-note",
      ),
    );
    if (calc.fingerprint)
      target.append(el("p", "SHA-256 " + calc.fingerprint, "provenance"));
  });
}
async function caseDetail(ctx, id) {
  const n = panel(
      L("المراجعة وتاريخ القرارات", "Review & decision history"),
      L(
        "أحداث وإصدارات ثابتة؛ لا يوجد تعديل قرار سابق.",
        "Append-only events and immutable versions; prior decisions cannot be edited.",
      ),
    ),
    target = el("div");
  n.append(target);
  openDrawer(L("حوكمة المراجعة · G6", "Review governance · G6"), n);
  await fetchPanel(
    ctx,
    target,
    "/api/v1/governance/cases/" + safeId(id),
    (data) => {
      target.append(
        details({
          id: data.id,
          claim_id: data.claim_id,
          audit_snapshot_id: data.audit_snapshot_id,
        }),
      );
      const timeline = el("div", null, "timeline");
      for (const event of data.events || []) {
        const entry = el("article", null, "event");
        entry.append(
          el("strong", display(event.kind) + " · v" + event.version),
          el("small", L("المراجع: ", "Reviewer: ") + event.actor_id),
        );
        if (event.evidence_document_id)
          entry.append(
            button(
              L("دليل الاعتراض", "Objection evidence"),
              () => void documentDetail(ctx, event.evidence_document_id),
              "link-button",
            ),
          );
        entry.append(details(event.payload));
        timeline.append(entry);
      }
      if (!data.events?.length)
        timeline.append(
          empty(
            L("لا توجد أحداث بعد", "No events yet"),
            L(
              "الحالة مفتوحة دون قرار مسجل.",
              "The case is open without a recorded decision.",
            ),
            "audit",
            true,
          ),
        );
      target.append(timeline);
      const options = [
        ["propose", L("اقتراح", "Propose"), "governance.propose"],
        [
          "hold",
          L("طلب أدلة / تعليق", "Evidence required / hold"),
          "governance.review",
        ],
        [
          "approve",
          L("اعتماد مستقل", "Independent approval"),
          "governance.approve",
        ],
        ["reject", L("رفض", "Reject"), "governance.approve"],
        ["object", L("اعتراض موثّق", "Evidenced objection"), "claims.read"],
        [
          "request_reaudit",
          L("طلب إعادة تدقيق", "Request re-audit"),
          "governance.reaudit",
        ],
        [
          "link_reaudit",
          L("ربط لقطة إعادة التدقيق", "Link re-audit snapshot"),
          "governance.reaudit",
        ],
      ].filter(([, , permission]) => allowed(ctx, permission));
      if (options.length) {
        const form = el("form"),
          row = el("div", null, "form-grid"),
          kind = field("event-kind", L("الإجراء", "Action"), {
            options: options.map(([v, l]) => [v, l]),
          }),
          reason = field("reason_code", L("رمز السبب", "Reason code"), {
            options: reasons(),
          }),
          evidence = field(
            "evidence_document_id",
            L("معرّف الدليل للاعتراض", "Objection evidence ID"),
            { pattern: idPattern, required: false },
          ),
          snap = field(
            "new_snapshot_id",
            L("لقطة إعادة التدقيق الجديدة", "New re-audit snapshot ID"),
            { pattern: idPattern, required: false },
          );
        row.append(kind.wrap, reason.wrap, evidence.wrap, snap.wrap);
        const submit = el(
          "button",
          L("تسجيل إصدار جديد", "Record new version"),
          "button primary",
        );
        submit.type = "submit";
        submit.disabled = ctx.demo;
        const result = el("div");
        result.setAttribute("aria-live", "polite");
        const update = () => {
          evidence.input.required = kind.input.value === "object";
          snap.input.required = kind.input.value === "link_reaudit";
        };
        kind.input.addEventListener("change", update);
        update();
        form.append(
          row,
          el(
            "p",
            L(
              "يحظر الخادم الاعتماد الذاتي؛ الاعتراض يتطلب مستندًا مستخرجًا وموثّقًا.",
              "The backend prohibits self-approval. Objections require an extracted, verified source document.",
            ),
            "auth-note",
          ),
          submit,
          result,
        );
        form.addEventListener("submit", async (e) => {
          e.preventDefault();
          if (
            submit.disabled ||
            !form.reportValidity() ||
            !(await confirm(L("تسجيل حدث حوكمة", "Record governance event")))
          )
            return;
          submit.disabled = true;
          try {
            const payload = { reason_code: reason.input.value };
            if (kind.input.value === "link_reaudit")
              payload.new_snapshot_id = snap.input.value;
            await ctx.api.request(
              "/api/v1/governance/cases/" + safeId(id) + "/events",
              {
                method: "POST",
                body: {
                  kind: kind.input.value,
                  payload,
                  evidence_document_id: evidence.input.value || null,
                },
              },
            );
            await caseDetail(ctx, id);
            toast(L("تم حفظ إصدار قرار جديد", "New decision version saved"));
          } catch (err) {
            result.replaceChildren(errorState(err));
          } finally {
            submit.disabled = ctx.demo;
          }
        });
        target.append(form);
      }
      target.append(
        el(
          "p",
          L(
            "تعيين المراجعين والتصعيد والتعليقات الحرة ومراحل الاستئناف غير متاحة في API الحالية.",
            "Reviewer assignment, escalation, free-text comments and appeal stages are unavailable in current APIs.",
          ),
          "auth-note",
        ),
      );
    },
  );
}
function recordDetail(ctx) {
  const id = safeId(ctx.recordId),
    card = panel(
      L("تفاصيل سجل مصرح", "Authorized record detail"),
      L(
        "المعرّفات والحقول المحمية لا تُستنتج من الرابط.",
        "Protected fields and identifiers are not inferred from URLs.",
      ),
      ctx.route.icon,
    ),
    target = el("div");
  card.append(target);
  ctx.root.append(card);
  const path =
    ctx.route.kind === "claim-detail"
      ? "/api/v1/workspace/claims/" + id
      : "/api/v1/workspace/users/" + id;
  void fetchPanel(ctx, target, path, (data) => target.append(details(data)));
}
function lookup(ctx) {
  const kind = ctx.route.kind;
  if (kind === "eligibility") {
    ctx.root.append(
      operation(
        ctx,
        L("التحقق من أهلية مستفيد", "Check beneficiary eligibility"),
        L(
          "أهلية زمنية من بيانات G3؛ لا توجد لوحة تعداد أو سجل طبي للمستفيدين.",
          "Temporal eligibility from G3. A beneficiary census dashboard or medical profile is unavailable.",
        ),
        [
          {
            name: "token",
            label: L("رمز المستفيد", "Beneficiary token"),
            value: ctx.recordId || "",
            maxLength: 128,
          },
          dateField("at", L("تاريخ الخدمة", "Service date")),
        ],
        "reference.read",
        (v) =>
          ctx.api.request(
            "/api/v1/reference/eligibility/" +
              encodeURIComponent(v.token) +
              "?at=" +
              v.at,
          ),
      ),
    );
    return;
  }
  if (kind === "provider-detail") {
    ctx.root.append(
      operation(
        ctx,
        L("عقد المزود الساري", "Active provider contract"),
        L(
          "الإصدار والتواريخ من مرجع G3؛ لا يُفترض نوع المزود.",
          "Version and dates from G3. Provider type is never inferred.",
        ),
        [
          {
            name: "provider_code",
            label: L("رمز المزود", "Provider code"),
            value: ctx.recordId || "",
            maxLength: 80,
          },
          dateField("at", L("التاريخ", "Date")),
        ],
        "reference.read",
        (v) =>
          ctx.api.request(
            "/api/v1/reference/contracts/active/" +
              encodeURIComponent(v.provider_code) +
              "?at=" +
              v.at,
          ),
      ),
    );
    return;
  }
  if (kind === "impact") {
    ctx.root.append(
      operation(
        ctx,
        L("أثر العقد الرجعي", "Retroactive contract impact"),
        L(
          "تحليل الخادم يتطلب مراجعة بشرية؛ لا يغيّر المطالبات الأصلية.",
          "Backend analysis requires human review and never changes original claims.",
        ),
        [idField("contract_id", L("العقد", "Contract ID"))],
        "reference.read",
        (v) =>
          ctx.api.request(
            "/api/v1/reference/contracts/" + safeId(v.contract_id) + "/impact",
          ),
      ),
    );
    return;
  }
  if (kind === "rule") {
    ctx.root.append(
      operation(
        ctx,
        L("فحص إصدار قاعدة", "Inspect rule version"),
        L(
          "عرض الحالة فقط؛ تفعيل القاعدة يتطلب تفويضًا كتابيًا وفصل المسؤوليات.",
          "Read rule state; activation requires written authorization and separated duties.",
        ),
        [idField("rule_id", L("القاعدة", "Rule ID"))],
        "rules.read",
        (v) => ctx.api.request("/api/v1/rules/" + safeId(v.rule_id)),
      ),
    );
    ctx.root.append(
      operation(
        ctx,
        L("تفعيل قاعدة مصرح بها", "Activate authorized rule"),
        L(
          "لن يتجاوز الطلب التوقيع أو الموافقة المستقلة أو قيود المؤسسة.",
          "This request cannot bypass signatures, independent approval or tenant constraints.",
        ),
        [idField("rule_id", L("القاعدة", "Rule ID"))],
        "rules.activate",
        (v) =>
          ctx.api.request("/api/v1/rules/" + safeId(v.rule_id) + "/activate", {
            method: "POST",
          }),
        { confirmation: true },
      ),
    );
    return;
  }
  if (kind === "audit-lookup") {
    ctx.root.append(
      operation(
        ctx,
        L("فحص مؤشرات التكرار", "Inspect duplicate indicators"),
        L(
          "اختر لقطة G5 لرؤية نتيجة وكيل التكرار؛ لا يوجد بحث شامل أو حكم احتيال.",
          "Select a G5 snapshot for the duplicate agent finding. No global duplicate search or fraud verdict exists.",
        ),
        [idField("snapshot_id", L("لقطة التدقيق", "Audit snapshot ID"))],
        "claims.read",
        async (v) => {
          await auditDetail(ctx, v.snapshot_id);
          return { review_only: true };
        },
      ),
    );
    return;
  }
  if (kind === "policy") {
    const intro = panel(
      L("الموافقة على السياسات المالية", "Financial policy approval"),
      L(
        "السجل يربط السياسة وبصمتها وتوقيع التفويض ومراجعين مستقلين. لا يوجد محرر حسابات مالية أو تنفيذ تدقيق إنتاجي.",
        "The registry links policy, fingerprint, authorization signature and independent reviewers. No financial-calculation editor or production audit execution is exposed.",
      ),
      "policy",
    );
    intro.append(
      details({ institutionally_accepted: false }),
      el(
        "p",
        L(
          "توقيع التفويض يُنتج خارج الواجهة بواسطة المسار المؤسسي؛ لا تُدخل مفاتيح التوقيع أو أسرار التشفير.",
          "Authorization signatures are produced outside the interface by the institutional process. Never enter signing keys or encryption secrets.",
        ),
        "auth-note",
      ),
    );
    ctx.root.append(intro);
    ctx.root.append(
      operation(
        ctx,
        L("تسجيل تفويض سياسة", "Register policy grant"),
        L(
          "يتحقق الخادم من الأدوار والتوقيع والاستقلال. عدم حسم السياسة الإنتاجية يبقي التنفيذ محجوبًا.",
          "The backend verifies roles, signature and independence. Unresolved production policy keeps execution blocked.",
        ),
        [
          idField(
            "organization_id",
            L("المؤسسة", "Organization ID"),
            ctx.context.organization?.id || "",
          ),
          idField("policy_id", L("معرّف السياسة", "Policy ID")),
          {
            name: "policy_fingerprint",
            label: L("بصمة السياسة SHA-256", "Policy SHA-256 fingerprint"),
            pattern: "[0-9a-f]{64}",
            maxLength: 64,
          },
          idField(
            "approver_id",
            L("المعتمد المؤسسي", "Institutional approver ID"),
          ),
          idField(
            "reviewer_id",
            L("المراجع المستقل", "Independent reviewer ID"),
          ),
          {
            name: "signature",
            label: L(
              "توقيع التفويض (ليس مفتاحًا)",
              "Authorization signature (not a key)",
            ),
            pattern: "[0-9a-f]{64}",
            maxLength: 64,
          },
        ],
        "policies.approve",
        (v) =>
          ctx.api.request("/api/v1/audit-policies/grants", {
            method: "POST",
            body: v,
          }),
        { confirmation: true },
      ),
    );
    ctx.root.append(
      operation(
        ctx,
        L("إلغاء تفويض سياسة", "Revoke policy grant"),
        L(
          "إلغاء موثّق دون تعديل الحسابات أو اللقطات القديمة.",
          "Audited revocation without changing prior calculations or snapshots.",
        ),
        [idField("grant_id", L("التفويض", "Grant ID"))],
        "policies.revoke",
        (v) =>
          ctx.api.request(
            "/api/v1/audit-policies/grants/" + safeId(v.grant_id) + "/revoke",
            { method: "POST" },
          ),
        { confirmation: true },
      ),
    );
  }
}
function referenceForms(ctx) {
  if (ctx.scope !== "admin") {
    const card = panel(
      L("المزود والعقد الساري", "Provider active contract"),
      L(
        "البيانات المرجعية لا توفر تصنيف مستشفى أو مختبر أو صيدلية.",
        "Reference data does not provide hospital, laboratory or pharmacy categorization.",
      ),
    );
    const f = operation(
      ctx,
      L("بحث عن عقد", "Find contract"),
      L(
        "اختر رمز مزود وتاريخًا ساريًا.",
        "Select a provider code and effective date.",
      ),
      [
        {
          name: "provider_code",
          label: L("رمز المزود", "Provider code"),
          maxLength: 80,
        },
        dateField("at", L("التاريخ", "Date")),
      ],
      "reference.read",
      (v) =>
        ctx.api.request(
          "/api/v1/reference/contracts/active/" +
            encodeURIComponent(v.provider_code) +
            "?at=" +
            v.at,
        ),
    );
    card.append(f);
    ctx.root.append(card);
    return;
  }
  ctx.root.append(
    operation(
      ctx,
      L("مسودة عقد جديدة", "New contract draft"),
      L(
        "الإصدارات المعتمدة لا تُعدّل؛ المراجعة والتفويض مستقلان.",
        "Approved versions cannot be edited. Review and authorization are separate.",
      ),
      [
        {
          name: "provider_code",
          label: L("رمز المزود", "Provider code"),
          maxLength: 80,
        },
        dateField("effective_from", L("ساري من", "Effective from")),
        dateField("effective_until", L("ساري حتى", "Effective until")),
        {
          name: "precedence",
          label: L("الأسبقية", "Precedence"),
          type: "number",
          min: 0,
          max: 10000,
          value: 0,
        },
      ],
      "reference.write",
      (v) => {
        if (v.effective_from >= v.effective_until)
          throw new Error(
            L(
              "نهاية العقد يجب أن تلي البداية",
              "End date must follow start date",
            ),
          );
        return ctx.api.request("/api/v1/reference/contracts", {
          method: "POST",
          body: { ...v, precedence: Number(v.precedence) },
        });
      },
    ),
  );
  ctx.root.append(
    operation(
      ctx,
      L("إضافة تعرفة لمسودة", "Add draft tariff"),
      L(
        "لا يمكن تعديل تعرفة عقد معتمد. القيمة عشرية يفسرها الخادم.",
        "Approved contract tariffs cannot be edited. The decimal value is interpreted by the backend.",
      ),
      [
        idField("contract_id", L("العقد", "Contract ID")),
        {
          name: "service_code",
          label: L("رمز الخدمة", "Service code"),
          maxLength: 100,
        },
        {
          name: "amount",
          label: L("المبلغ العشري", "Decimal amount"),
          pattern: "[0-9]+(\\.[0-9]{1,4})?",
          maxLength: 30,
        },
        {
          name: "currency",
          label: L("العملة ISO", "ISO currency"),
          pattern: "[A-Z]{3}",
          maxLength: 3,
        },
      ],
      "reference.write",
      (v) =>
        ctx.api.request(
          "/api/v1/reference/contracts/" + safeId(v.contract_id) + "/tariffs",
          {
            method: "POST",
            body: {
              service_code: v.service_code,
              amount: v.amount,
              currency: v.currency,
            },
          },
        ),
    ),
  );
  ctx.root.append(
    operation(
      ctx,
      L("فحص واستيراد تعريفات CSV", "Preview & import tariff CSV"),
      L(
        "حتى 2 MB. المعاينة لا تغيّر البيانات؛ التطبيق ذري في الخادم بعد اكتمال التحقق.",
        "Up to 2 MB. Preview does not change data; application is atomic on the server after complete validation.",
      ),
      [
        idField("contract_id", L("العقد", "Contract ID")),
        {
          name: "file",
          label: L("ملف التعريفات CSV", "Tariff CSV file"),
          type: "file",
        },
        {
          name: "apply",
          label: L("الإجراء", "Action"),
          options: [
            ["false", L("معاينة فقط", "Preview only")],
            ["true", L("تطبيق الاستيراد", "Apply import")],
          ],
        },
      ],
      "reference.write",
      async (v, inputs) => {
        const file = inputs.file.files[0];
        if (!file || file.size === 0 || file.size > 2000000)
          throw new Error(
            L("اختر CSV غير فارغ حتى 2 MB", "Choose a nonempty CSV up to 2 MB"),
          );
        if (
          v.apply === "true" &&
          !(await confirm(L("تطبيق استيراد التعريفات", "Apply tariff import")))
        )
          throw new Error(L("تم الإلغاء", "Cancelled"));
        return ctx.api.request(
          "/api/v1/reference/contracts/" +
            safeId(v.contract_id) +
            "/tariffs/import?apply=" +
            v.apply,
          { method: "POST", body: file, raw: true },
        );
      },
    ),
  );
  for (const [action, ar, en] of [
    ["precedence-review", "مراجعة أسبقية العقد", "Review contract precedence"],
    ["impact-review", "مراجعة أثر العقد", "Review contract impact"],
  ])
    ctx.root.append(
      operation(
        ctx,
        L(ar, en),
        L(
          "مراجعة موثّقة مستقلة؛ لا تتضمن بيانات طبية في النص.",
          "Documented independent review; do not include medical data in rationale.",
        ),
        [
          idField("contract_id", L("العقد", "Contract ID")),
          {
            name: "rationale",
            label: L(
              "مبرر المراجعة (20–2000 حرف)",
              "Review rationale (20–2000 characters)",
            ),
            type: "textarea",
            maxLength: 2000,
          },
        ],
        "reference.approve",
        (v) => {
          if (v.rationale.length < 20)
            throw new Error(
              L(
                "المبرر يجب ألا يقل عن 20 حرفًا",
                "Rationale must contain at least 20 characters",
              ),
            );
          return ctx.api.request(
            "/api/v1/reference/contracts/" +
              safeId(v.contract_id) +
              "/" +
              action,
            { method: "POST", body: { rationale: v.rationale } },
          );
        },
        { confirmation: true },
      ),
    );
  ctx.root.append(
    operation(
      ctx,
      L("ربط تفويض كتابي", "Link written authorization"),
      L(
        "تفويض موثّق من مخزن المصادر الحالي.",
        "A documented authorization from the current source store.",
      ),
      [
        idField("contract_id", L("العقد", "Contract ID")),
        idField("authorization_id", L("التفويض", "Authorization ID")),
      ],
      "reference.approve",
      (v) =>
        ctx.api.request(
          "/api/v1/reference/contracts/" +
            safeId(v.contract_id) +
            "/authorization",
          { method: "POST", body: { authorization_id: v.authorization_id } },
        ),
      { confirmation: true },
    ),
  );
  ctx.root.append(
    operation(
      ctx,
      L("اعتماد عقد مستقل", "Independently approve contract"),
      L(
        "يحظر الخادم اعتماد الكاتب لنفسه أو التفعيل دون سياسة أسبقية معتمدة.",
        "The backend prohibits author self-approval and activation without approved precedence policy.",
      ),
      [idField("contract_id", L("العقد", "Contract ID"))],
      "reference.approve",
      (v) =>
        ctx.api.request(
          "/api/v1/reference/contracts/" + safeId(v.contract_id) + "/approve",
          { method: "POST" },
        ),
      { confirmation: true },
    ),
  );
  ctx.root.append(
    operation(
      ctx,
      L("تعريف فئة مستفيد", "Define beneficiary category"),
      L(
        "سجل مرجعي للمؤسسة الحالية.",
        "Reference record scoped to the current organization.",
      ),
      [
        { name: "code", label: L("الرمز", "Code"), maxLength: 80 },
        {
          name: "description",
          label: L("وصف الفئة", "Category description"),
          maxLength: 200,
        },
      ],
      "reference.write",
      (v) =>
        ctx.api.request("/api/v1/reference/categories", {
          method: "POST",
          body: v,
        }),
    ),
  );
  ctx.root.append(
    operation(
      ctx,
      L("تسجيل أهلية زمنية", "Register temporal eligibility"),
      L(
        "رمز مستفيد دون اسم أو سجل طبي؛ الخادم يتحقق من الفئة وتداخل التواريخ.",
        "A beneficiary token without name or medical record. The backend validates category and date overlap.",
      ),
      [
        {
          name: "beneficiary_token",
          label: L("رمز المستفيد", "Beneficiary token"),
          maxLength: 128,
        },
        idField("category_id", L("الفئة", "Category ID")),
        dateField("effective_from", L("ساري من", "Effective from")),
        dateField("effective_until", L("ساري حتى", "Effective until")),
      ],
      "reference.write",
      (v) =>
        ctx.api.request("/api/v1/reference/enrollments", {
          method: "POST",
          body: v,
        }),
    ),
  );
}
function intelligence(ctx) {
  const { root, route } = ctx;
  const intro = el("section", null, "hero"),
    text = el("div");
  text.append(
    badge(L("G8 · استشارات محكومة", "G8 · governed advisory analytics")),
    el(
      "h2",
      L(
        "تحليل قابل للتفسير، ومراجعة مستقلة لكل أثر",
        "Explainable analysis, independent review for every consequence",
      ),
    ),
    el(
      "p",
      L(
        "مصادر G7 الثابتة فقط. لا SQL أو كود حر أو إرسال طبي خارجي. ليست هذه مخرجات قرار طبي أو مالي.",
        "Frozen G7 sources only. No SQL, arbitrary code or external medical data transfer. These outputs are not medical or financial decisions.",
      ),
    ),
  );
  intro.append(text, icon("ai"));
  root.append(intro);
  if (route.kind === "capabilities") {
    const target = panel(
      L("المؤشرات والأبعاد المسموحة", "Allowed indicators & dimensions"),
      L("القدرات المُعلنة من الخادم فقط", "Backend-declared capabilities only"),
      "ai",
    );
    root.append(target);
    const result = el("div");
    target.append(result);
    void fetchPanel(ctx, result, "/api/v1/intelligence/capabilities", (d) =>
      result.append(details(d)),
    );
    return;
  }
  if (route.kind === "tasks") {
    studio(ctx);
    return;
  }
  const list = panel(
      L("التحاليل المحفوظة", "Saved analysis runs"),
      L(
        "نتائج مرتبطة ببصمات التقارير وقابلة لإعادة الفحص.",
        "Results are linked to report fingerprints and can be inspected.",
      ),
      "ai",
    ),
    target = el("div");
  list.append(target);
  root.append(list);
  const load = (offset = 0) =>
    void fetchPanel(
      ctx,
      target,
      "/api/v1/intelligence/runs?limit=25&offset=" + offset,
      (d) => {
        table(target, d.items, {
          offset,
          hasMore: d.has_more,
          onPage: load,
          open: (r) => void inspectRun(ctx, r.id),
        });
        if (!d.items.length)
          target.append(
            empty(
              L("لا توجد تحاليل محفوظة", "No saved runs"),
              L(
                "اختر مصادر مصرحًا بها لإنشاء تحليل محكوم.",
                "Select authorized sources to create a governed analysis.",
              ),
              "ai",
              true,
            ),
          );
      },
    );
  load();
  const runKind =
    route.kind === "signals"
      ? "signals"
      : route.kind === "simulation"
        ? "simulation"
        : "summary";
  const formCard = panel(
      L("إنشاء تحليل موثّق", "Create evidenced analysis"),
      L(
        "1–12 تقريرًا من دفعات مختلفة. يتطلب التنفيذ صلاحية التقارير والتحليل.",
        "1–12 reports from different batches. Execution requires report and analysis permissions.",
      ),
      "ai",
    ),
    sources = el("div");
  root.append(formCard);
  formCard.append(sources);
  void fetchPanel(
    ctx,
    sources,
    "/api/v1/report-explorer/snapshots?limit=100",
    async (d) => {
      if (!d.items.length) {
        sources.append(
          empty(
            L("لا توجد مصادر تقرير", "No report sources"),
            L(
              "يلزم تقرير ثابت قبل التحليل.",
              "A frozen report is required before analysis.",
            ),
            "reports",
            true,
          ),
        );
        return;
      }
      const form = el("form"),
        grid = el("div", null, "form-grid");
      const source = field(
        "report_ids",
        L(
          "التقارير المصدرية (اختيار متعدد)",
          "Source reports (multiple selection)",
        ),
        {
          options: d.items.map((r) => [
            r.id,
            "v" + r.version + " / " + r.batch_id.slice(0, 10),
          ]),
          multiple: true,
        },
      );
      source.input.options[0].selected = true;
      grid.append(source.wrap);
      let dimension, reduction, task;
      if (runKind === "summary") {
        dimension = field(
          "dimension",
          L("بُعد التجميع", "Grouping dimension"),
          {
            options: dimensions(),
            value: route.path.includes("trends") ? "month" : "provider",
          },
        );
        grid.append(dimension.wrap);
      }
      if (runKind === "simulation") {
        reduction = field(
          "reduction_percent",
          L("تخفيض افتراضي %", "Hypothetical reduction %"),
          { pattern: "[0-9]+(\\.[0-9]+)?", value: "10", maxLength: 20 },
        );
        grid.append(reduction.wrap);
      }
      if (runKind === "signals") {
        task = field("task_id", L("مهمة مختبرة ونشطة", "Tested active task"), {
          options: [["", L("جارٍ قراءة المهام", "Loading tasks")]],
        });
        grid.append(task.wrap);
        try {
          const tasks = await ctx.api.request(
            "/api/v1/intelligence/studio/tasks?limit=100",
          );
          task.input.replaceChildren();
          for (const t of tasks.items.filter((t) => t.status === "activated")) {
            const o = el("option", t.code + " / v" + t.version);
            o.value = t.id;
            task.input.append(o);
          }
          if (!task.input.options.length) {
            const o = el("option", L("لا توجد مهمة نشطة", "No active task"));
            o.value = "";
            task.input.append(o);
          }
        } catch (err) {
          sources.append(errorState(err));
        }
      }
      const submit = el(
        "button",
        L("إنشاء نتيجة للمراجعة", "Create review-only result"),
        "button violet",
      );
      submit.type = "submit";
      submit.disabled =
        ctx.demo ||
        !allowed(ctx, "intelligence.run") ||
        !allowed(ctx, "reports.read");
      const output = el("div");
      output.setAttribute("aria-live", "polite");
      form.append(
        grid,
        el(
          "p",
          L(
            "حجم الخصوصية الأدنى 5؛ المجموعات الصغيرة قد تُحجب. لا توجد تحليلات جغرافية أو AI توليدي في الخادم.",
            "Minimum privacy group is 5; small groups may be suppressed. Geographic analytics and generative AI are unavailable in the backend.",
          ),
          "auth-note",
        ),
        submit,
        output,
      );
      sources.append(form);
      form.addEventListener("submit", async (event) => {
        event.preventDefault();
        if (submit.disabled || !form.reportValidity()) return;
        const ids = Array.from(source.input.selectedOptions).map(
          (o) => o.value,
        );
        if (ids.length > 12) {
          output.replaceChildren(
            errorState(
              new Error(L("اختر حتى 12 تقريرًا", "Select at most 12 reports")),
            ),
          );
          return;
        }
        let params =
          runKind === "summary"
            ? { dimension: dimension.input.value, min_group_size: 5 }
            : runKind === "simulation"
              ? { reduction_percent: reduction.input.value }
              : {};
        if (
          reduction &&
          (Number(reduction.input.value) < 0 ||
            Number(reduction.input.value) > 100)
        ) {
          output.replaceChildren(
            errorState(
              new Error(
                L("النسبة بين 0 و100", "Percentage must be between 0 and 100"),
              ),
            ),
          );
          return;
        }
        submit.disabled = true;
        output.replaceChildren(loading());
        try {
          const run = await ctx.api.request("/api/v1/intelligence/runs", {
            method: "POST",
            body: {
              kind: runKind,
              report_ids: ids,
              parameters: params,
              task_id: task?.input.value || null,
            },
          });
          output.replaceChildren(runResult(ctx, run));
          load();
        } catch (err) {
          output.replaceChildren(errorState(err));
        } finally {
          submit.disabled =
            ctx.demo ||
            !allowed(ctx, "intelligence.run") ||
            !allowed(ctx, "reports.read");
        }
      });
    },
  );
}
function studio(ctx) {
  const list = panel(
      L("إصدارات مهام التحليل", "Analysis task versions"),
      L(
        "مسودة ← اختبار مثبت ← اعتماد مستقل ← تفعيل. كل تعديل إصدار جديد.",
        "Draft → evidenced test → independent approval → activation. Each change creates a new version.",
      ),
      "ai",
    ),
    target = el("div");
  list.append(target);
  ctx.root.append(list);
  const load = (offset = 0) =>
    void fetchPanel(
      ctx,
      target,
      "/api/v1/intelligence/studio/tasks?limit=25&offset=" + offset,
      (d) => {
        table(target, d.items, {
          columns: [
            "code",
            "version",
            "status",
            "id",
            "configuration_fingerprint",
          ],
          offset,
          hasMore: d.has_more,
          onPage: load,
          open: (t) => {
            const result = el("div");
            result.append(details(t));
            const actions = el("div", null, "switch-links");
            const steps =
              t.status === "draft"
                ? [
                    [
                      "test",
                      L("اختبار الخادم", "Server test"),
                      "intelligence.studio.test",
                    ],
                  ]
                : t.status === "tested"
                  ? [
                      [
                        "activate",
                        L(
                          "اعتماد مستقل وتفعيل",
                          "Independent approval & activation",
                        ),
                        "intelligence.studio.activate",
                      ],
                    ]
                  : t.status === "activated"
                    ? [
                        [
                          "deactivate",
                          L("إيقاف موثّق", "Audited deactivation"),
                          "intelligence.studio.activate",
                        ],
                      ]
                    : [];
            for (const [action, label, permission] of steps) {
              const b = actionButton(ctx, label, permission, async () => {
                if (!(await confirm(label))) return;
                b.disabled = true;
                try {
                  const event = await ctx.api.request(
                    "/api/v1/intelligence/studio/tasks/" +
                      safeId(t.id) +
                      "/" +
                      action,
                    { method: "POST" },
                  );
                  result.append(details(event));
                  load(offset);
                  toast(L("تم حفظ حدث إصدار جديد", "New version event saved"));
                } catch (err) {
                  result.append(errorState(err));
                } finally {
                  b.disabled = ctx.demo || !allowed(ctx, permission);
                }
              });
              actions.append(b);
            }
            actions.append(
              button(
                L("سجل الإصدارات", "Version history"),
                () =>
                  void fetchPanel(
                    ctx,
                    result,
                    "/api/v1/intelligence/studio/tasks/" + safeId(t.id),
                    (d) => result.append(details(d)),
                  ),
              ),
            );
            result.append(actions);
            openDrawer(L("حوكمة المهمة", "Task governance"), result);
          },
        });
        if (!d.items.length)
          target.append(
            empty(
              L("لا توجد مهام معرفة", "No configured tasks"),
              L(
                "إنشاء المهام لا يمنحها حق التنفيذ قبل الاختبار والاعتماد المستقل.",
                "Creating tasks does not allow execution before testing and independent approval.",
              ),
              "ai",
              true,
            ),
          );
      },
    );
  load();
  ctx.root.append(
    operation(
      ctx,
      L("منشئ مهمة تحليل محكومة", "Governed analysis task builder"),
      L(
        "إعدادات الخادم المسموحة فقط. الاسم الوصفي والغرض والجدولة وقوالب المطالبات الحرة ليست حقولًا مدعومة بعد.",
        "Only backend-whitelisted configuration. Descriptive name, purpose, scheduling and free-form prompts are not yet supported.",
      ),
      [
        {
          name: "code",
          label: L("رمز المهمة / اسمها", "Task code / name"),
          pattern: "[a-z][a-z0-9_]{2,63}",
          maxLength: 64,
        },
        {
          name: "indicator",
          label: L("المؤشر", "Indicator"),
          options: indicators(),
        },
        {
          name: "dimension",
          label: L("بُعد التجميع", "Grouping dimension"),
          options: dimensions(),
        },
        {
          name: "threshold_percent",
          label: L("العتبة %", "Threshold %"),
          pattern: "[0-9]+(\\.[0-9]+)?",
          maxLength: 20,
          value: "60",
        },
        {
          name: "min_group_size",
          label: L("حد الخصوصية (5–1000)", "Privacy floor (5–1000)"),
          type: "number",
          min: 5,
          max: 1000,
          value: 5,
        },
      ],
      "intelligence.studio.manage",
      (v) => {
        if (Number(v.threshold_percent) > 100)
          throw new Error(
            L("العتبة لا تتجاوز 100", "Threshold cannot exceed 100"),
          );
        if (
          v.indicator === "provider_claimed_share" &&
          v.dimension !== "provider"
        )
          throw new Error(
            L(
              "حصة المزود تتطلب بُعد المزود",
              "Provider share requires provider grouping",
            ),
          );
        return ctx.api.request("/api/v1/intelligence/studio/tasks", {
          method: "POST",
          body: {
            code: v.code,
            configuration: {
              source: "g7_frozen_report_snapshots",
              indicator: v.indicator,
              dimension: v.dimension,
              threshold_percent: v.threshold_percent,
              min_group_size: Number(v.min_group_size),
            },
          },
        });
      },
    ),
  );
}
async function inspectRun(ctx, id) {
  const card = panel(
      L("نتيجة تحليل موثقة", "Evidenced analysis result"),
      L(
        "إشارات للمراجعة دون قرارات تلقائية",
        "Review signals without automatic decisions",
      ),
    ),
    target = el("div");
  card.append(target);
  openDrawer(L("التحليل والمصدر", "Analysis & source"), card);
  await fetchPanel(
    ctx,
    target,
    "/api/v1/intelligence/runs/" + safeId(id),
    (r) => target.append(runResult(ctx, r)),
  );
}
function runResult(ctx, run) {
  const n = el("div"),
    output = run.result.output;
  n.append(
    badge(
      L(
        "توصية تحليلية · للمراجعة فقط",
        "Analysis recommendation · review only",
      ),
      "violet",
    ),
    details({
      id: run.id,
      analysis_type: run.kind,
      fingerprint: run.fingerprint,
      parameters: run.parameters,
      sources: run.sources,
    }),
  );
  if (run.kind === "summary") {
    const p = panel(
      L("التوزيع والتكاليف", "Distribution & expenditure"),
      L(
        "المقام وحجب المجموعات من الخادم؛ لا تُنشأ مقارنات زمنية ناقصة.",
        "Denominators and group suppression come from the backend. Incomplete time comparisons are not inferred.",
      ),
    );
    p.append(
      details({
        denominator_count: output.denominator_count,
        suppressed_groups: output.suppressed_groups,
        dimension: output.dimension,
      }),
    );
    const chart = panel(
      L("توزيع المؤشرات", "Indicator distribution"),
      L(
        "أول 10 مجموعات مسجلة؛ عملة واحدة دون دمج أو تحويل. الأشهر الغائبة ليست صفرًا.",
        "First 10 recorded groups; one currency without aggregation or conversion. Missing months are not zeros.",
      ),
    );
    const controls = el("div", null, "filters"),
      currencies = [...new Set((output.groups || []).map((g) => g.currency))],
      currency = field(
        "chart_currency",
        L("عملة التحليل", "Analysis currency"),
        { options: currencies.map((c) => [c, c]) },
      ),
      metric = field("chart_metric", L("المؤشر المرئي", "Visible metric"), {
        options: [
          ["claimed", L("المطالب به", "Claimed")],
          ["payable", L("المستحق", "Payable")],
          ["count", L("عدد المطالبات", "Claim count")],
        ],
      }),
      graph = el("div");
    controls.append(currency.wrap, metric.wrap);
    chart.append(controls, graph);
    const draw = () => {
      const selected = (output.groups || []).filter(
        (g) => g.currency === currency.input.value,
      );
      graph.replaceChildren(
        groupChart(selected, {
          dimension: output.dimension,
          metric: metric.input.value,
          onOpen: (g) =>
            openDrawer(L("دليل المجموعة", "Group evidence"), details(g)),
        }),
      );
    };
    currency.input.addEventListener("change", draw);
    metric.input.addEventListener("change", draw);
    draw();
    p.append(chart);
    const tableTarget = el("div");
    table(tableTarget, output.groups || [], {
      columns: [
        "group",
        "currency",
        "count",
        "claimed",
        "payable",
        "deductions",
        "hold_rate_percent",
      ],
      open: (g) =>
        openDrawer(L("منهج التجميع", "Grouping evidence"), details(g)),
    });
    p.append(tableTarget);
    n.append(p);
  }
  if (run.kind === "simulation") {
    n.append(
      panel(
        L("سيناريو افتراضي", "Hypothetical scenario"),
        L(
          "الفارق الافتراضي ليس وفرًا محققًا ولا يؤثر على المطالبات أو السياسات.",
          "The hypothetical difference is not realized savings and does not affect claims or policy.",
        ),
      ),
    );
    n.append(details(output));
  }
  if (run.kind === "signals") {
    if (!output.findings?.length)
      n.append(
        empty(
          L("لا توجد إشارات مستوفية", "No qualifying signals"),
          L(
            "غياب الإشارة لا يعني غياب المخاطر.",
            "Absence of signals does not establish absence of risk.",
          ),
          "ai",
          true,
        ),
      );
    for (const [index, finding] of (output.findings || []).entries()) {
      const card = panel(
        L("إشارة رقم ", "Signal ") + (index + 1),
        L(
          "عدم يقين يتطلب مراجعة الأدلة؛ لا يوجد حكم احتيال أو قرار طبي.",
          "Uncertainty requires evidence review; no fraud verdict or medical decision.",
        ),
      );
      card.append(details(finding));
      const review = operation(
        ctx,
        L("تقييم مستقل للإشارة", "Independent signal assessment"),
        L(
          "التقييم مستقل عن منشئ التحليل وبسبب مصنف دون نص طبي.",
          "Assessment must be independent from the run creator, using a coded reason without medical text.",
        ),
        [
          {
            name: "disposition",
            label: L("تقييم المراجع", "Reviewer assessment"),
            options: [
              ["needs_followup", L("تحتاج متابعة", "Needs follow-up")],
              ["false_positive", L("إيجابية كاذبة", "False positive")],
              [
                "insufficient_evidence",
                L("أدلة غير كافية", "Insufficient evidence"),
              ],
            ],
          },
          {
            name: "reason_code",
            label: L("رمز السبب", "Reason code"),
            options: reasons(),
          },
        ],
        "intelligence.review",
        (v) =>
          ctx.api.request(
            "/api/v1/intelligence/runs/" +
              safeId(run.id) +
              "/signals/" +
              index +
              "/reviews",
            { method: "POST", body: v },
          ),
        { confirmation: true },
      );
      card.append(review);
      n.append(card);
    }
    const summary = panel(
        L("تقييم جودة الإشارات", "Signal review quality"),
        L(
          "نسبة الإيجابيات الكاذبة تستخدم الإشارات المراجعة فقط مقامًا، ولا تقيس انتشار الاحتيال.",
          "False-positive rate uses reviewed signals only as denominator and does not measure fraud prevalence.",
        ),
      ),
      target = el("div");
    summary.append(target);
    n.append(summary);
    void fetchPanel(
      ctx,
      target,
      "/api/v1/intelligence/runs/" + safeId(run.id) + "/review-summary",
      (d) => target.append(details(d)),
    );
  }
  return n;
}

function retention(ctx) {
  const card = panel(L("أرشفة سجل التدقيق", "Audit log archival"),
    L("احتفاظ مقترح لمدة 7 سنوات ينتظر الاعتماد المؤسسي. لا يُحذف أي سجل.",
      "Proposed seven-year retention awaits institutional approval. Audit rows are preserved."));
  const result = el("div");
  card.append(result); ctx.root.append(card);
  fetchPanel(ctx, result, "/api/v1/admin/retention/status", (data) => {
    result.append(details(data));
    result.append(badge(L("الحذف الدوري معطّل", "Purge disabled"), "warning"));
  });
  ctx.root.append(operation(ctx, L("طلب أرشفة شهر مكتمل", "Request completed-month archive"),
    L("يُسجّل الطلب وينفذه العامل المحلي المشفّر. لا يشمل سجلات المؤسسات الأخرى.",
      "The local encrypted worker processes this request; other institutions are excluded."),
    [{name:"month", label:L("الشهر", "Month"), type:"month", required:true}],
    "retention.archive", (inputs) => ctx.api.request("/api/v1/admin/retention/archive",
      {method:"POST", body:{month:inputs.month}}), {confirmation:true}));
}
