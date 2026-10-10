/** DOM-only component library. Server data is always text, never executable markup. */
export const preferences = { lang: "ar", theme: "light" };
export const L = (ar, en) => (preferences.lang === "ar" ? ar : en);
export function el(tag, text, cls) {
  const n = document.createElement(tag);
  if (text !== null && text !== undefined) n.textContent = String(text);
  if (cls) n.className = cls;
  return n;
}
export function icon(name) {
  const n = el("img");
  n.src = "/workspace-assets/icons/" + name + ".svg";
  n.alt = "";
  n.loading = "lazy";
  n.width = 64;
  n.height = 56;
  return n;
}
const vectorPaths = {
  menu: "M3 5h18M3 12h18M3 19h18",
  search: "m21 21-5-5M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0",
  sun: "M12 3v2m0 14v2M3 12h2m14 0h2M5 5l2 2m10 10 2 2M5 19l2-2M17 7l2-2M16 12a4 4 0 1 1-8 0 4 4 0 0 1 8 0",
  bell: "M5 17h14l-2-3V9a5 5 0 0 0-10 0v5ZM10 21h4",
  close: "m6 6 12 12M6 18 18 6",
  download: "M12 3v12m-5-5 5 5 5-5M4 17v4h16v-4",
  logout: "M9 3H3v18h6m5-15 6 6-6 6m-7-6h13",
  chevron: "m9 5 7 7-7 7",
  refresh:
    "M20 7v-4m0 4h-4M4 17v4m0-4h4M4 9a8 8 0 0 1 14-5m2 11a8 8 0 0 1-14 5",
  shield: "m12 2 8 3v7c0 5-8 10-8 10S4 17 4 12V5Z",
  plus: "M12 4v16M4 12h16",
};
export function vector(name) {
  const n = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  n.setAttribute("viewBox", "0 0 24 24");
  n.setAttribute("aria-hidden", "true");
  const p = document.createElementNS(n.namespaceURI, "path");
  p.setAttribute("d", vectorPaths[name] || vectorPaths.chevron);
  p.setAttribute("fill", "none");
  p.setAttribute("stroke", "currentColor");
  p.setAttribute("stroke-width", "1.7");
  p.setAttribute("stroke-linecap", "round");
  p.setAttribute("stroke-linejoin", "round");
  n.append(p);
  return n;
}
export function button(label, fn, cls = "button", symbol) {
  const b = el("button", null, cls);
  b.type = "button";
  if (symbol) b.append(vector(symbol));
  b.append(el("span", label));
  if (fn) b.addEventListener("click", fn);
  return b;
}
export function link(label, path, cls = "") {
  const a = el("a", label, cls);
  a.href = path;
  return a;
}
export const badge = (text, cls = "") => el("span", text, "badge " + cls);
export function panel(title, description, asset) {
  const n = el("section", null, "panel");
  const head = el("div", null, "panel-head"),
    text = el("div");
  text.append(el("h2", title));
  if (description) text.append(el("p", description));
  head.append(text);
  if (asset) head.append(icon(asset));
  n.append(head);
  return n;
}
export function empty(title, description, asset = "reports", compact = false) {
  const n = el("div", null, "empty" + (compact ? " compact" : ""));
  n.append(icon(asset), el("h2", title), el("p", description));
  return n;
}
export function loading() {
  const n = el("div");
  n.setAttribute("aria-busy", "true");
  n.setAttribute("aria-label", L("جارٍ التحميل", "Loading"));
  for (let i = 0; i < 3; i++)
    n.append(el("div", null, "skeleton" + (i === 1 ? " large" : "")));
  return n;
}
export function errorState(error, retry) {
  const n = el("div", null, "error");
  n.setAttribute("role", "alert");
  n.append(
    el(
      "strong",
      error.status === 403
        ? L("لا تملك الصلاحية المطلوبة", "Permission required")
        : L("تعذر إتمام الطلب", "Request could not be completed"),
    ),
    el("p", error.message),
  );
  if (retry) n.append(button(L("إعادة المحاولة", "Retry"), retry));
  return n;
}
let toastTimer;
export function toast(text) {
  const n = document.getElementById("toast");
  n.textContent = text;
  n.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    n.hidden = true;
    n.textContent = "";
  }, 7000);
}
export function field(
  name,
  label,
  {
    type = "text",
    value = "",
    options,
    required = true,
    pattern,
    min,
    max,
    maxLength = 200,
    placeholder = "",
    multiple = false,
  } = {},
) {
  const wrap = el("div", null, "field"),
    id = "field-" + name + "-" + Math.random().toString(36).slice(2, 8);
  const lab = el("label", label);
  lab.htmlFor = id;
  const input = el(
    options ? "select" : type === "textarea" ? "textarea" : "input",
  );
  if (!options && type !== "textarea") input.type = type;
  input.id = id;
  input.name = name;
  input.required = required;
  input.autocomplete = type === "password" ? "current-password" : "off";
  input.maxLength = maxLength;
  if (pattern) input.pattern = pattern;
  if (min !== undefined) input.min = min;
  if (max !== undefined) input.max = max;
  if (type === "number") input.step = "1";
  if (placeholder) input.placeholder = placeholder;
  if (options) {
    input.multiple = multiple;
    for (const [v, t] of options) {
      const o = el("option", t);
      o.value = v;
      input.append(o);
    }
  }
  if (!options || value !== "" || options.some(([v]) => v === ""))
    input.value = value;
  wrap.append(lab, input);
  return { wrap, input };
}
export const idPattern = "[a-zA-Z0-9_-]{1,120}";
export function safeId(value) {
  const text = String(value).trim();
  if (!/^[a-zA-Z0-9_-]{1,120}$/.test(text))
    throw new Error(L("معرّف غير صالح", "Invalid identifier"));
  return encodeURIComponent(text);
}
const labels = {
  approved_count: ["مطالبات معتمدة", "Approved claims"],
  held_count: ["مطالبات معلّقة", "Held claims"],
  deductions: ["الخصومات", "Deductions"],
  group: ["المجموعة", "Group"],
  count: ["عدد المطالبات", "Claim count"],
  hold_rate_percent: ["معدل التعليق %", "Hold rate %"],
  suppressed_groups: ["مجموعات محجوبة", "Suppressed groups"],
  denominator_count: ["عدد السجلات في المقام", "Denominator count"],
  revision_of: ["إصدار المصدر السابق", "Previous source version"],
  hold_reason: ["سبب التعليق", "Hold reason"],
  audit_snapshot_id: ["لقطة التدقيق", "Audit snapshot"],
  governance_case_id: ["حالة المراجعة", "Review case"],
  state: ["الحالة", "State"],
  id: ["المعرّف", "ID"],
  status: ["الحالة", "Status"],
  claimed: ["المطالب به", "Claimed"],
  claimed_amount: ["المطالب به", "Claimed"],
  currency: ["العملة", "Currency"],
  payable: ["المستحق الموثّق", "Verified payable"],
  total_deduction: ["إجمالي الخصومات", "Total deductions"],
  deduction: ["الخصم", "Deduction"],
  fingerprint: ["البصمة", "Fingerprint"],
  policy_id: ["السياسة", "Policy"],
  policy_fingerprint: ["بصمة السياسة", "Policy fingerprint"],
  claim_id: ["المطالبة", "Claim"],
  batch_id: ["الدفعة", "Batch"],
  source_sha256: ["بصمة المصدر", "Source SHA-256"],
  source_id: ["المصدر", "Source"],
  service_date: ["تاريخ الخدمة", "Service date"],
  claim_reference: ["مرجع المطالبة", "Claim reference"],
  provider_code: ["رمز المزود", "Provider code"],
  version: ["الإصدار", "Version"],
  created_at: ["تاريخ التسجيل", "Created"],
  effective_from: ["ساري من", "Effective from"],
  effective_until: ["ساري حتى", "Effective until"],
  imported_count: ["المستورد", "Imported"],
  record_count: ["عدد السجلات", "Records"],
  sha256: ["بصمة المصدر", "Source hash"],
  document_id: ["المستند", "Document"],
  reason: ["السبب", "Reason"],
  reference: ["الدليل المرجعي", "Evidence reference"],
  reason_code: ["رمز السبب", "Reason code"],
  actor_id: ["المراجع", "Actor"],
  kind: ["النوع", "Type"],
  code: ["الرمز", "Code"],
  username: ["اسم المستخدم", "Username"],
  active: ["نشط", "Active"],
  configuration: ["الإعدادات", "Configuration"],
  configuration_fingerprint: ["بصمة الإعدادات", "Configuration fingerprint"],
  evidence: ["الأدلة", "Evidence"],
  rule: ["القاعدة", "Rule"],
  remaining: ["المتبقي", "Remaining"],
  source_count: ["عدد المصادر", "Source count"],
  scope: ["نطاق البيانات", "Data scope"],
  retrieved_at: ["وقت القراءة", "Retrieved at"],
  eligible: ["الأهلية", "Eligible"],
  category_id: ["الفئة", "Category"],
  sources: ["المصادر", "Sources"],
  analysis_type: ["نوع التحليل", "Analysis type"],
  reviewed_signals: ["الإشارات المراجعة", "Reviewed signals"],
  signal_count: ["عدد الإشارات", "Signal count"],
  false_positive_rate_among_reviewed: [
    "النسبة بين المراجَعة فقط",
    "Rate among reviewed only",
  ],
  numerator: ["البسط", "Numerator"],
  denominator: ["المقام", "Denominator"],
  baseline_percent: ["خط الأساس", "Baseline %"],
  observed_percent: ["المؤشر المرصود", "Observed %"],
  threshold_percent: ["العتبة", "Threshold %"],
  sample_count: ["حجم العينة", "Sample count"],
  cohort_count: ["حجم المجموعة", "Cohort count"],
  report_id: ["التقرير", "Report"],
  min_group_size: ["حد الخصوصية", "Privacy floor"],
  source: ["المصدر المعتمد", "Approved source"],
  indicator: ["المؤشر", "Indicator"],
  dimension: ["بُعد التجميع", "Grouping"],
  expires_at: ["انتهاء الجلسة", "Session expiry"],
  institutionally_accepted: ["اعتماد مؤسسي", "Institutional acceptance"],
  review_only: ["للمراجعة فقط", "Review only"],
};
export const labelFor = (key) =>
  labels[key] ? L(...labels[key]) : key.replaceAll("_", " ");
export function display(value) {
  if (value === null || value === undefined) return "—";
  if (typeof value === "boolean")
    return value ? L("نعم", "Yes") : L("لا", "No");
  return String(value);
}
export function details(value, depth = 0) {
  const list = el("dl", null, "detail-grid");
  if (!value || typeof value !== "object") return el("p", display(value));
  for (const [key, v] of Object.entries(value)) {
    const box = el("div", null, "detail");
    box.append(el("dt", labelFor(key)));
    const dd = el("dd");
    if (v && typeof v === "object" && depth < 3) {
      if (Array.isArray(v)) {
        for (const item of v.slice(0, 100))
          dd.append(
            typeof item === "object"
              ? details(item, depth + 1)
              : el("div", display(item)),
          );
      } else dd.append(details(v, depth + 1));
    } else dd.textContent = display(v);
    box.append(dd);
    list.append(box);
  }
  return list;
}
export function openDrawer(title, content) {
  const dialog = document.getElementById("drawer");
  dialog.replaceChildren();
  const head = el("div", null, "dialog-head");
  const h = el("h2", title);
  h.id = "drawer-title";
  head.append(
    h,
    button(L("إغلاق", "Close"), () => dialog.close(), "icon-button", "close"),
  );
  dialog.append(head, content);
  if (!dialog.open) dialog.showModal();
}
export function confirm(label) {
  return new Promise((resolve) => {
    const d = document.getElementById("confirmation");
    d.returnValue = "";
    d.replaceChildren();
    const h = el("h2", label);
    h.id = "confirm-title";
    d.append(
      h,
      el(
        "p",
        L(
          "سيُسجّل الخادم الإجراء وفق الصلاحيات وفصل المسؤوليات. لا يمكن تعديل النسخ الثابتة.",
          "The server records this action under authorization and separation of duties. Immutable versions cannot be edited.",
        ),
      ),
    );
    const row = el("div", null, "header-actions");
    row.append(
      button(L("إلغاء", "Cancel"), () => d.close("cancel")),
      button(
        L("تأكيد الإجراء", "Confirm action"),
        () => d.close("confirm"),
        "button primary",
      ),
    );
    d.append(row);
    d.addEventListener("close", () => resolve(d.returnValue === "confirm"), {
      once: true,
    });
    d.showModal();
  });
}
/** @param {HTMLElement} target @param {object[]} rows */
export function table(
  target,
  rows,
  { columns, open, offset = 0, hasMore = false, onPage, caption } = {},
) {
  let current = rows.slice(),
    sort = null,
    descending = false;
  const wrap = el("div"),
    filters = el("div", null, "filters");
  const search = field(
    "page-filter",
    L("تصفية هذه الصفحة", "Filter this page"),
    {
      required: false,
      placeholder: L("بحث في السجلات المعروضة", "Search displayed records"),
    },
  );
  filters.append(
    search.wrap,
    el(
      "p",
      L(
        "الفرز والتصفية على الصفحة المحمّلة فقط. الترقيم من الخادم.",
        "Sorting and filtering apply to this loaded page only. Pagination is server-backed.",
      ),
      "filter-note",
    ),
  );
  wrap.append(filters);
  const scroller = el("div", null, "table-scroll");
  scroller.tabIndex = 0;
  scroller.setAttribute("role", "region");
  scroller.setAttribute(
    "aria-label",
    caption || L("جدول النتائج", "Results table"),
  );
  const t = el("table"),
    cap = el(
      "caption",
      caption || L("نتائج من الخادم المصرح", "Authorized server results"),
      "sr-only",
    );
  t.append(cap);
  const thead = el("thead"),
    tr = el("tr");
  columns =
    columns ||
    Object.keys(rows[0] || {})
      .filter(
        (k) =>
          ![
            "summary",
            "configuration",
            "events",
            "sources",
            "permissions",
            "roles",
          ].includes(k),
      )
      .slice(0, 7);
  for (const key of columns) {
    const th = el("th");
    th.scope = "col";
    th.append(
      button(
        labelFor(key),
        () => {
          descending = sort === key ? !descending : false;
          sort = key;
          thead
            .querySelectorAll("th")
            .forEach((x) => x.removeAttribute("aria-sort"));
          th.setAttribute("aria-sort", descending ? "descending" : "ascending");
          render();
        },
        "link-button",
      ),
    );
    tr.append(th);
  }
  if (open) {
    const th = el("th", L("التفاصيل", "Details"));
    th.scope = "col";
    tr.append(th);
  }
  thead.append(tr);
  t.append(thead);
  const body = el("tbody"),
    pageCount = el("span");
  t.append(body);
  scroller.append(t);
  wrap.append(scroller);
  function render() {
    body.replaceChildren();
    current = rows.filter((r) =>
      columns.some((k) =>
        display(r[k])
          .toLocaleLowerCase()
          .includes(search.input.value.toLocaleLowerCase()),
      ),
    );
    if (sort)
      current.sort(
        (a, b) =>
          display(a[sort]).localeCompare(display(b[sort]), preferences.lang, {
            numeric: true,
          }) * (descending ? -1 : 1),
      );
    for (const r of current) {
      const row = el("tr");
      for (const key of columns) {
        const value = r[key];
        const td = el(
          "td",
          display(value),
          /id|sha256|fingerprint/.test(key) ? "table-id" : "",
        );
        td.title = display(value);
        row.append(td);
      }
      if (open) {
        const td = el("td");
        td.append(
          button(
            L("عرض الدليل", "View evidence"),
            () => open(r),
            "link-button",
          ),
        );
        row.append(td);
      }
      body.append(row);
    }
    pageCount.textContent =
      L("السجلات المعروضة: ", "Displayed records: ") +
      current.length +
      " · " +
      L("الإزاحة: ", "Offset: ") +
      offset;
    if (!current.length) {
      const row = el("tr"),
        td = el("td", L("لا توجد سجلات مطابقة", "No matching records"));
      td.colSpan = columns.length + (open ? 1 : 0);
      row.append(td);
      body.append(row);
    }
  }
  search.input.addEventListener("input", render);
  render();
  const paging = el("div", null, "pagination");
  paging.append(pageCount);
  const actions = el("div", null, "header-actions");
  if (onPage) {
    const prev = button(L("السابق", "Previous"), () =>
        onPage(Math.max(0, offset - 25)),
      ),
      next = button(L("التالي", "Next"), () => onPage(offset + 25));
    prev.disabled = offset === 0;
    next.disabled = !hasMore;
    actions.append(prev, next);
  }
  paging.append(actions);
  wrap.append(paging);
  target.replaceChildren(wrap);
  return wrap;
}
export function kpi(title, value, asset, note, href) {
  const n = el("article", null, "kpi");
  const top = el("div", null, "kpi-top");
  top.append(el("span", title, "kpi-label"), icon(asset));
  const num = el("div", value, "kpi-value");
  num.dir = "ltr";
  num.setAttribute("aria-label", title + ": " + value);
  const foot = el("div", null, "kpi-foot");
  foot.append(el("span", note));
  if (href) foot.append(link(L("التفاصيل", "Details"), href));
  n.append(top, num, foot);
  return n;
}
export function currencyChart(totals, onSelect) {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 500 200");
  svg.setAttribute("class", "chart");
  svg.setAttribute("role", onSelect ? "group" : "img");
  svg.setAttribute(
    "aria-label",
    L(
      "المطالب به والمستحق حسب العملة؛ القيم الدقيقة في الجدول",
      "Claimed and verified payable by currency; exact amounts in the table",
    ),
  );
  const s = (tag, attrs, text) => {
    const n = document.createElementNS(svg.namespaceURI, tag);
    for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
    if (text !== undefined) n.textContent = text;
    svg.append(n);
    return n;
  };
  for (let i = 0; i < 4; i++)
    s("line", {
      x1: 25,
      x2: 480,
      y1: 30 + i * 40,
      y2: 30 + i * 40,
      class: "gridline",
    });
  const entries = Object.entries(totals).slice(0, 8),
    max = Math.max(1, ...entries.map(([, v]) => Number(v.claimed)));
  for (let i = 0; i < entries.length; i++) {
    const [currency, v] = entries[i],
      x = 45 + i * (420 / entries.length),
      claimed = Math.min(150, (Number(v.claimed) / max) * 150),
      payable = Math.min(150, (Number(v.payable) / max) * 150);
    const bars = [
      s("rect", {
        x,
        y: 170 - claimed,
        width: 20,
        height: claimed,
        rx: 4,
        class: "claimed",
      }),
      s("rect", {
        x: x + 25,
        y: 170 - payable,
        width: 20,
        height: payable,
        rx: 4,
        class: "payable",
      }),
    ];
    if (onSelect)
      for (const bar of bars) {
        bar.setAttribute("tabindex", "0");
        bar.setAttribute("role", "button");
        bar.setAttribute(
          "aria-label",
          currency +
            " / " +
            display(v.claimed) +
            " / " +
            display(v.payable) +
            " / " +
            L("استعراض المطالبات", "Browse claims"),
        );
        bar.addEventListener("click", () => onSelect(currency));
        bar.addEventListener("keydown", (e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            onSelect(currency);
          }
        });
      }
    s("text", { x: x + 22, y: 192, "text-anchor": "middle" }, currency);
  }
  return svg;
}
export function donut(total, approved, held) {
  const wrap = el("div", null, "donut-wrap"),
    svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("class", "donut");
  svg.setAttribute("viewBox", "0 0 160 160");
  svg.setAttribute("role", "img");
  svg.setAttribute(
    "aria-label",
    L("معتمد: ", "Approved: ") + approved + L("، معلّق: ", ", held: ") + held,
  );
  const make = (tag, attrs, text) => {
    const n = document.createElementNS(svg.namespaceURI, tag);
    for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
    if (text) n.textContent = text;
    svg.append(n);
  };
  make("circle", {
    cx: 80,
    cy: 80,
    r: 63,
    fill: "none",
    "stroke-width": 15,
    class: "track",
  });
  if (total) {
    make("circle", {
      cx: 80,
      cy: 80,
      r: 63,
      fill: "none",
      "stroke-width": 15,
      class: "held",
    });
    make("circle", {
      cx: 80,
      cy: 80,
      r: 63,
      fill: "none",
      "stroke-width": 15,
      class: "approved",
      "stroke-dasharray": (approved / total) * 396 + " 396",
      transform: "rotate(-90 80 80)",
    });
  }
  make("text", { x: 80, y: 81, "text-anchor": "middle" }, String(total));
  make(
    "text",
    { x: 80, y: 102, "text-anchor": "middle", class: "small" },
    L("مطالبة", "claims"),
  );
  wrap.append(svg);
  const legend = el("div");
  legend.append(
    el("p", L("معتمد: ", "Approved: ") + approved),
    el("p", L("معلّق: ", "Held: ") + held),
    el(
      "small",
      L(
        "لا تشمل المطالبات خارج اللقطة",
        "Excludes claims outside this snapshot",
      ),
    ),
  );
  wrap.append(legend);
  return wrap;
}
/** Visualization ratios are approximate; every displayed metric is a backend value. */
export function groupChart(
  groups,
  { dimension = "provider", metric = "claimed", onOpen } = {},
) {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 640 235");
  svg.setAttribute("class", "chart");
  svg.setAttribute("role", onOpen ? "group" : "img");
  svg.setAttribute(
    "aria-label",
    L(
      "رسم من قيم التحليل؛ انقر لعرض الدليل",
      "Chart from analysis values; select a point for evidence",
    ),
  );
  const make = (tag, attrs, text) => {
    const n = document.createElementNS(svg.namespaceURI, tag);
    for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
    if (text !== undefined) n.textContent = text;
    svg.append(n);
    return n;
  };
  const rows = groups
      .filter((g) => g[metric] !== null && g[metric] !== undefined)
      .slice(0, 10),
    max = Math.max(1, ...rows.map((g) => Number(g[metric])));
  for (let i = 0; i < 4; i++)
    make("line", {
      x1: 24,
      x2: 620,
      y1: 25 + i * 50,
      y2: 25 + i * 50,
      class: "gridline",
    });
  const points = rows.map((g, i) => ({
    g,
    x: 50 + i * (540 / Math.max(rows.length - 1, 1)),
    y: 180 - (Number(g[metric]) / max) * 155,
  }));
  if (dimension === "month" && points.length > 1)
    make("polyline", {
      points: points.map((p) => p.x + "," + p.y).join(" "),
      fill: "none",
      stroke: "#2563eb",
      "stroke-width": 3,
    });
  for (const { g, x, y } of points) {
    const mark =
      dimension === "month"
        ? make("circle", { cx: x, cy: y, r: 6, fill: "#2563eb" })
        : make("rect", {
            x: x - 10,
            y,
            width: 22,
            height: 180 - y,
            rx: 4,
            class: "claimed",
          });
    const label =
      g.group === "__suppressed__" ? L("محجوب", "Suppressed") : String(g.group);
    make("text", { x, y: 207, "text-anchor": "middle" }, label.slice(0, 14));
    if (onOpen) {
      mark.setAttribute("tabindex", "0");
      mark.setAttribute("role", "button");
      mark.setAttribute(
        "aria-label",
        label + " / " + display(g[metric]) + " / " + g.currency,
      );
      mark.addEventListener("click", () => onOpen(g));
      mark.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          onOpen(g);
        }
      });
    }
  }
  return svg;
}
