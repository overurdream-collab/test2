import {
  preferences,
  L,
  el,
  icon,
  vector,
  button,
  link,
  badge,
  empty,
  errorState,
  field,
  loading,
  toast,
} from "./ui.js";
import { ApiClient } from "./api.js";
import { renderView } from "./views.js";
import { matchRoute, routeVisible } from "./feature_navigation.js";
const api = new ApiClient();
let routes = [],
  context = null,
  demo = false,
  expiryTimer,
  search = "",
  collapsed = false;
let access = null;
async function refreshAccess() {
  access = await api.request("/api/v1/me/features");
  api.enableFeatureData();
  context = { ...access.user, organization: access.organization, permissions: access.permissions,
    roles: access.roles, expires_at: access.expires_at, institutionally_accepted: false, tenant_switching: false };
}
const app = document.getElementById("app");
api.onExpiry = () => {
  signOutLocal();
  toast(
    L("انتهت الجلسة؛ أعد تسجيل الدخول.", "Session expired; sign in again."),
  );
};
function routeAt(path) {
  return matchRoute(routes, path);
}
function navigate(path) {
  if (document.getElementById("drawer").open)
    document.getElementById("drawer").close();
  history.pushState({}, "", path + (demo ? "?demo=1" : ""));
  search = "";
  render();
  window.scrollTo(0, 0);
}
function toggleLanguage() {
  preferences.lang = preferences.lang === "ar" ? "en" : "ar";
  render();
}
function toggleTheme() {
  preferences.theme = preferences.theme === "light" ? "dark" : "light";
  document.documentElement.dataset.theme = preferences.theme;
}
function signOutLocal() {
  clearTimeout(expiryTimer);
  api.clear();
  context = null;
  access = null;
  demo = false;
  for (const id of ["drawer", "confirmation"]) {
    const d = document.getElementById(id);
    if (d.open) d.close();
    d.replaceChildren();
  }
  document.getElementById("toast").hidden = true;
  history.replaceState({}, "", "/login");
  render();
}
async function signOut() {
  try {
    if (!demo) await api.request("/api/v1/auth/logout", { method: "POST" });
  } catch (_error) {
    /* Always clear medical data and session in the browser. */
  } finally {
    signOutLocal();
  }
}
function auth() {
  const container = el("div", null, "auth-shell"),
    aside = el("aside", null, "auth-aside");
  aside.append(
    icon("audit"),
    el("div", "MCIAS  /  V2.0", "eyebrow"),
    el(
      "h1",
      L("ثقة في البيانات. دقة في المراجعة.", "Trusted data. Precise review."),
    ),
    el(
      "p",
      L(
        "منصة ذكاء المطالبات الطبية والتدقيق المالي، داخل المؤسسة وبإشراف بشري مستقل.",
        "Medical claims intelligence and financial audit, on premises and under independent human oversight.",
      ),
    ),
    el(
      "small",
      L(
        "جميع البوابات غير معتمدة مؤسسيًا · G0–G9",
        "All gates institutionally unaccepted · G0–G9",
      ),
    ),
  );
  const main = el("main", null, "auth-main");
  main.id = "main";
  const card = el("section", null, "auth-card"),
    tools = el("div", null, "auth-tools");
  tools.append(
    button(L("English", "العربية"), toggleLanguage, "icon-button"),
    button(L("الثيم", "Theme"), toggleTheme, "icon-button", "sun"),
  );
  card.append(tools);
  if (location.pathname === "/forgot-password") {
    card.append(
      empty(
        L(
          "استعادة كلمة المرور عبر المسؤول",
          "Password recovery through administrator",
        ),
        L(
          "لا توجد API لاستعادة كلمة المرور. اتبع إجراء الاستعادة المحلي المعتمد لدى مؤسستك.",
          "A password recovery API is unavailable. Follow your institution’s approved local recovery procedure.",
        ),
        "security",
      ),
      link(L("العودة لتسجيل الدخول", "Back to sign in"), "/login", "button"),
    );
    main.append(card);
    container.append(aside, main);
    app.replaceChildren(container);
    return;
  }
  card.append(
    el("div", L("وصول محكوم وآمن", "SECURE, GOVERNED ACCESS"), "eyebrow"),
    el("h1", L("مرحبًا بك في MCIAS", "Welcome to MCIAS")),
    el(
      "p",
      L(
        "سجّل الدخول إلى مساحة عمل المؤسسة.",
        "Sign in to your organization workspace.",
      ),
    ),
  );
  const form = el("form");
  form.id = "login-form";
  const username = field("username", L("اسم المستخدم", "Username"), {
      maxLength: 120,
    }),
    password = field("password", L("كلمة المرور", "Password"), {
      type: "password",
      maxLength: 1024,
    }),
    mfa = field(
      "totp_code",
      L(
        "رمز التحقق (إلزامي للإدارة)",
        "MFA code (required for administrators)",
      ),
      { required: false, pattern: "[0-9]{6}", maxLength: 6 },
    );
  username.input.autocomplete = "username";
  password.input.autocomplete = "current-password";
  mfa.input.autocomplete = "one-time-code";
  mfa.input.inputMode = "numeric";
  const submit = el(
    "button",
    L("تسجيل الدخول بأمان", "Sign in securely"),
    "button primary",
  );
  submit.type = "submit";
  const result = el("div", null, "auth-error");
  result.setAttribute("aria-live", "polite");
  form.append(username.wrap, password.wrap, mfa.wrap, submit, result);
  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    if (!form.reportValidity() || submit.disabled) return;
    submit.disabled = true;
    result.replaceChildren(loading());
    try {
      const response = await api.request("/api/v1/auth/login", {
        method: "POST",
        body: {
          username: username.input.value.trim(),
          password: password.input.value,
          totp_code: mfa.input.value || null,
        },
      });
      api.setToken(response.access_token);
      await refreshAccess();
      const wait = new Date(context.expires_at).getTime() - Date.now();
      if (Number.isFinite(wait))
        expiryTimer = setTimeout(
          () => {
            signOutLocal();
            toast(L("انتهت الجلسة", "Session expired"));
          },
          Math.min(2147483647, Math.max(0, wait)),
        );
      if (["/login", "/mfa", "/forgot-password"].includes(location.pathname))
        history.replaceState({}, "", "/institution/dashboard");
      render();
    } catch (err) {
      api.clear();
      context = null;
      result.replaceChildren(errorState(err));
    } finally {
      password.input.value = "";
      mfa.input.value = "";
      submit.disabled = false;
    }
  });
  card.append(
    form,
    link(L("استعادة كلمة المرور", "Password recovery"), "/forgot-password"),
    el(
      "p",
      L(
        "الجلسة في ذاكرة الصفحة فقط. لا تُرسل السجلات الطبية خارج تثبيت المؤسسة.",
        "Session exists only in page memory. Medical records never leave the organization installation.",
      ),
      "auth-note",
    ),
  );
  main.append(card);
  container.append(aside, main);
  app.replaceChildren(container);
}
function render() {
  document.documentElement.lang = preferences.lang;
  document.documentElement.dir = preferences.lang === "ar" ? "rtl" : "ltr";
  document.documentElement.dataset.theme = preferences.theme;
  document.title =
    "MCIAS · " + L("ذكاء المطالبات والتدقيق", "Claims intelligence & audit");
  if (!context) {
    auth();
    return;
  }
  const found = routeAt(location.pathname),
    route = found?.route || {
      ar: "المسار غير موجود",
      en: "Page not found",
      kind: "missing",
      icon: "reports",
      permission: "",
    },
    scope = location.pathname.startsWith("/admin") ? "admin" : "institution";
  const shell = el("div", null, "shell" + (collapsed ? " collapsed" : "")),
    sidebar = el("aside", null, "sidebar");
  sidebar.id = "sidebar";
  sidebar.inert = window.innerWidth <= 760;
  sidebar.append(
    button(
      L("إغلاق القائمة", "Close menu"),
      () => {
        shell.classList.remove("nav-open");
        sidebar.inert = window.innerWidth <= 760;
        mobile.focus();
      },
      "icon-button mobile-menu",
      "close",
    ),
  );
  sidebar.setAttribute("aria-label", L("التنقل الرئيسي", "Main navigation"));
  const brand = link(
    "",
    scope === "admin" ? "/admin/dashboard" : "/institution/dashboard",
    "brand",
  );
  brand.append(el("span", "M", "brand-mark"));
  const brandText = el("div");
  brandText.append(
    el("strong", "MCIAS", "brand-name"),
    el("small", L("ذكاء المطالبات والتدقيق", "Claims intelligence & audit")),
  );
  brand.append(brandText);
  sidebar.append(brand);
  const workspaceLabel = el("div", null, "workspace-switch");
  workspaceLabel.append(
    el(
      "strong",
      scope === "admin"
        ? L("الإدارة المركزية", "Central administration")
        : L("مساحة المؤسسة", "Institution workspace"),
    ),
    el(
      "small",
      context.organization?.name ||
        L("لا توجد مؤسسة مرتبطة", "No organization assigned"),
    ),
  );
  sidebar.append(workspaceLabel);
  const nav = el("nav");
  nav.setAttribute("aria-label", L("الوحدات", "Modules"));
  const scopeRoutes = routes.filter(
    (r) => r.path.startsWith("/" + scope + "/") && !r.path.includes(":id") && routeVisible(r, access),
  );
  const groups =
    scope === "admin"
      ? [
          [L("المنصة والوصول", "PLATFORM & ACCESS"), 0, 7],
          [L("البيانات والحوكمة", "DATA & GOVERNANCE"), 7, 14],
          [L("التحليل والعمليات", "ANALYSIS & OPERATIONS"), 14, 99],
        ]
      : [
          [L("نظرة شاملة", "OVERVIEW"), 0, 3],
          [L("الرعاية والإنفاق", "CARE & EXPENDITURE"), 3, 12],
          [L("التدقيق والذكاء", "AUDIT & INTELLIGENCE"), 12, 20],
          [L("الأدلة والمراجعة", "EVIDENCE & REVIEW"), 20, 99],
        ];
  for (const [title, start, end] of groups) {
    if (!scopeRoutes.slice(start, end).length) continue;
    nav.append(el("p", title, "nav-heading"));
    for (const r of scopeRoutes.slice(start, end)) {
      const a = link("", r.path, "nav-link");
      a.title = L(r.ar, r.en);
      if (route.path === r.path) a.setAttribute("aria-current", "page");
      a.append(icon(r.icon), el("span", L(r.ar, r.en), "nav-text"));
      if (r.kind === "unavailable")
        a.append(el("span", L("مخطط", "Planned"), "nav-state"));
      else if (r.permission && !context.permissions.includes(r.permission))
        a.append(el("span", L("مقيد", "Restricted"), "nav-state"));
      nav.append(a);
    }
  }
  if (!scopeRoutes.some(r => r.feature)) nav.append(el("p", L("لا ميزات مفعّلة", "No enabled features"), "nav-heading"));
  nav.append(el("p", L("مساحات العمل", "WORKSPACES"), "nav-heading"));
  if (context.roles.includes("super_admin"))
    nav.append(
      link(
        scope === "admin"
          ? L("واجهة المؤسسة", "Institution interface")
          : L("واجهة الإدارة", "Administration interface"),
        scope === "admin" ? "/institution/dashboard" : "/admin/dashboard",
        "nav-link",
      ),
    );
  nav.append(link(L("المساعدة", "Help"), "/shared/help", "nav-link"));
  sidebar.append(nav);
  const foot = el("div", null, "sidebar-foot");
  foot.append(
    el(
      "strong",
      L("داخل المؤسسة · بيانات محمية", "On premises · protected data"),
    ),
    el(
      "span",
      L("G0–G9 غير معتمدة مؤسسيًا", "G0–G9 institutionally unaccepted"),
    ),
  );
  sidebar.append(foot);
  const workspace = el("div", null, "workspace"),
    topbar = el("header", null, "topbar");
  const mobile = button(
    L("القائمة", "Menu"),
    () => {
      const opened = shell.classList.toggle("nav-open");
      mobile.setAttribute("aria-expanded", String(opened));
      sidebar.inert = !opened && window.innerWidth <= 760;
      if (opened) sidebar.querySelector("button").focus();
    },
    "icon-button mobile-menu",
    "menu",
  );
  mobile.setAttribute("aria-controls", "sidebar");
  mobile.setAttribute("aria-expanded", "false");
  topbar.append(
    mobile,
    button(
      L("طي", "Collapse"),
      () => {
        collapsed = !collapsed;
        render();
      },
      "icon-button desktop-collapse",
      "menu",
    ),
  );
  const searchWrap = el("div", null, "search-wrap");
  searchWrap.append(vector("search"));
  const searchInput = el("input");
  searchInput.type = "search";
  searchInput.placeholder = L(
    "ابحث عن وحدة أو مساحة عمل…",
    "Find a module or workspace…",
  );
  searchInput.setAttribute(
    "aria-label",
    L("بحث في أسماء الوحدات", "Search module names"),
  );
  const searchResults = el("div", null, "search-results");
  searchResults.hidden = true;
  searchInput.addEventListener("input", () => {
    search = searchInput.value.trim().toLocaleLowerCase();
    searchResults.replaceChildren();
    searchResults.hidden = !search;
    if (search) {
      const results = routes.filter(r => routeVisible(r, access))
        .filter(
          (r) =>
            !r.path.includes(":id") &&
            L(r.ar, r.en).toLocaleLowerCase().includes(search) &&
            (!r.admin || context.roles.includes("super_admin")),
        )
        .slice(0, 15);
      for (const r of results)
        searchResults.append(link(L(r.ar, r.en), r.path));
      if (!results.length)
        searchResults.append(
          el("p", L("لا توجد وحدات مطابقة", "No matching modules")),
        );
    }
  });
  searchWrap.append(searchInput, searchResults);
  topbar.append(searchWrap, el("div", null, "topbar-spacer"));
  const tenant = button(
    context.organization?.name || L("المؤسسة", "Organization"),
    null,
    "icon-button",
  );
  tenant.title = L(
    "تثبيت منفصل؛ تبديل المؤسسة غير متاح",
    "Separate installation; tenant switching is unavailable",
  );
  tenant.disabled = true;
  tenant.classList.add("tenant-selector");
  topbar.append(
    tenant,
    button(
      preferences.lang === "ar" ? "EN" : "عربي",
      toggleLanguage,
      "icon-button",
    ),
    button(L("الثيم", "Theme"), toggleTheme, "icon-button", "sun"),
  );
  const notifications = button(
    L("الإشعارات", "Notifications"),
    () => navigate("/shared/notifications"),
    "icon-button",
    "bell",
  );
  notifications.title = L(
    "لا يوجد مركز إشعارات تشغيلي",
    "An operational notification inbox is unavailable",
  );
  topbar.append(notifications);
  const profile = button(
    context.username,
    () => navigate("/shared/profile"),
    "profile-button",
  );
  profile.replaceChildren(
    el("span", context.username.slice(0, 2).toUpperCase(), "avatar"),
    el("span", context.username, "username"),
  );
  topbar.append(
    profile,
    button(
      L("خروج", "Sign out"),
      () => void signOut(),
      "icon-button",
      "logout",
    ),
  );
  const main = el("main", null, "main");
  main.id = "main";
  main.tabIndex = -1;
  const crumb = el("nav", null, "breadcrumb");
  crumb.setAttribute("aria-label", L("مسار التنقل", "Breadcrumb"));
  crumb.append(
    link(
      scope === "admin"
        ? L("الإدارة", "Administration")
        : L("المؤسسة", "Institution"),
      scope === "admin" ? "/admin/dashboard" : "/institution/dashboard",
    ),
    vector("chevron"),
    el("span", L(route.ar, route.en)),
  );
  main.append(crumb);
  if (demo) {
    const demoBanner = el("div", null, "banner demo");
    demoBanner.append(
      el(
        "strong",
        L(
          "عرض اصطناعي فقط — ليس بيانات حية أو اعتمادًا مؤسسيًا",
          "SYNTHETIC PREVIEW — NOT LIVE DATA OR INSTITUTIONAL ACCEPTANCE",
        ),
      ),
      el("span", L("كل الإجراءات للقراءة فقط", "All actions are read-only")),
    );
    main.append(demoBanner);
  }
  const head = el("div", null, "page-header"),
    heading = el("div");
  heading.append(
    el(
      "div",
      scope === "admin"
        ? L("حوكمة المنصة", "PLATFORM GOVERNANCE")
        : L("ذكاء الرعاية والإنفاق", "CARE & EXPENDITURE INTELLIGENCE"),
      "eyebrow",
    ),
    el("h1", L(route.ar, route.en)),
    el(
      "p",
      L("مرحبًا، ", "Welcome, ") +
        context.username +
        " · " +
        (context.organization?.name ||
          L("لا توجد مؤسسة مرتبطة", "No organization assigned")),
    ),
  );
  head.append(heading);
  const actions = el("div", null, "header-actions");
  if (route.kind === "dashboard")
    actions.append(
      link(
        L("التقارير والتصدير", "Reports & export"),
        "/institution/reports",
        "button",
      ),
    );
  actions.append(button(L("تحديث", "Refresh"), async () => {
    try { if (!demo) await refreshAccess(); render(); }
    catch (error) { toast(error.message); }
  }, "button", "refresh"));
  head.append(actions);
  main.append(head);
  const banner = el("div", null, "banner");
  banner.append(
    el(
      "span",
      L(
        "قدرات هندسية جزئية؛ جميع بوابات القبول مفتوحة.",
        "Partial engineering capabilities; all acceptance gates remain open.",
      ),
    ),
    badge(
      route.kind === "unavailable"
        ? L("غير متاح", "Unavailable")
        : L("غير معتمد مؤسسيًا", "Institutionally unaccepted"),
      "warning",
    ),
  );
  main.append(banner);
  const root = el("div");
  main.append(root);
  const restricted =
    (route.admin && !context.roles.includes("super_admin")) ||
    (route.permission && !context.permissions.includes(route.permission));
  if (restricted) {
    root.append(
      empty(
        L("وصول غير مصرح", "Access not authorized"),
        L(
          "تتطلب هذه المساحة صلاحية محددة. لا تُسترجع السجلات دونها.",
          "This workspace requires a specific permission. No records are fetched without it.",
        ),
        "security",
      ),
      badge(route.permission || "super_admin", "warning"),
    );
  } else if (!routeVisible(route, access) && route.kind !== "missing") {
    root.append(empty(L("لا ميزات مفعّلة لهذه الصفحة", "This feature is not enabled"),
      L("تحتاج تفعيل الميزة للجهة وصلاحية مناسبة للمستخدم.", "An organization entitlement and user permission are required."), "security"));
  } else if (route.kind === "missing") {
    root.append(
      empty(
        L("الصفحة غير موجودة", "Page not found"),
        L("اختر وحدة من القائمة.", "Choose a module from navigation."),
      ),
    );
  } else {
    renderView({
      root,
      route,
      scope,
      routes,
      recordId: found?.recordId,
      context,
      api,
      demo,
      navigate,
      toggleLanguage,
      toggleTheme,
      signOutLocal,
      refreshAccess,
    });
  }
  main.append(
    el(
      "p",
      L(
        "MCIAS v2.0 · الأصل محفوظ · الأدلة قابلة للتتبع · القرار النهائي بشري ومصرح",
        "MCIAS v2.0 · Originals preserved · Evidence traceable · Final decisions human and authorized",
      ),
      "disclaimer",
    ),
  );
  workspace.append(topbar, main);
  shell.append(sidebar, workspace);
  app.replaceChildren(shell);
}
document.addEventListener("click", (event) => {
  const a = event.target.closest("a");
  if (
    !a ||
    a.target ||
    event.ctrlKey ||
    event.metaKey ||
    event.shiftKey ||
    a.origin !== location.origin ||
    a.hash ||
    !a.pathname.startsWith("/")
  )
    return;
  event.preventDefault();
  navigate(a.pathname);
});
window.addEventListener("popstate", render);
window.addEventListener("resize", () => {
  const sidebar = document.getElementById("sidebar");
  if (sidebar)
    sidebar.inert =
      window.innerWidth <= 760 &&
      !document.querySelector(".shell")?.classList.contains("nav-open");
});
document.addEventListener("keydown", (event) => {
  const shell = document.querySelector(".shell");
  if (event.key === "Escape" && shell?.classList.contains("nav-open")) {
    shell.classList.remove("nav-open");
    document.getElementById("sidebar").inert = window.innerWidth <= 760;
    const mobile = document.querySelector(".topbar .mobile-menu");
    mobile?.setAttribute("aria-expanded", "false");
    mobile?.focus();
  }
  if (
    event.key === "Tab" &&
    shell?.classList.contains("nav-open") &&
    window.innerWidth <= 760
  ) {
    const links = Array.from(
      document.querySelectorAll(".sidebar a,.sidebar button"),
    ).filter((x) => x.offsetParent !== null);
    if (event.shiftKey && document.activeElement === links[0]) {
      event.preventDefault();
      links.at(-1)?.focus();
    } else if (!event.shiftKey && document.activeElement === links.at(-1)) {
      event.preventDefault();
      links[0]?.focus();
    }
  }
});
async function start() {
  try {
    const response = await fetch("/workspace-assets/routes.json", {
      cache: "no-store",
      credentials: "omit",
    });
    if (!response.ok) throw Error("Route catalog unavailable");
    routes = await response.json();
    if (new URLSearchParams(location.search).get("demo") === "1") {
      const availability = await api.request(
        "/api/v1/workspace/demo-availability",
      );
      if (availability.enabled) {
        const fixture = await fetch("/workspace-assets/demo.json", {
          cache: "no-store",
          credentials: "omit",
        }).then((r) => r.json());
        api.demo(fixture);
        context = fixture.context;
        access = {features: routes.map(r => r.feature).filter(Boolean), permissions: context.permissions,
          super_admin: context.roles.includes("super_admin")};
        demo = true;
      } else
        toast(
          L(
            "العرض الاصطناعي غير مفعّل في هذه البيئة",
            "Synthetic preview is disabled in this environment",
          ),
        );
    }
    render();
  } catch (err) {
    app.replaceChildren(errorState(err, () => void start()));
  }
}
void start();
