// Pure helpers: route matching and checkbox diffs never confer server authority.
export function matchRoute(routes, path) {
  const exact = routes.find(route => route.path === path);
  if (exact) return { route: exact, recordId: null };
  for (const route of routes) {
    const expected = route.path.split("/"), actual = path.split("/");
    if (expected.length !== actual.length) continue;
    let recordId = null, matches = true;
    for (let i = 0; i < expected.length; i++) {
      if (expected[i] === ":id") {
        try { recordId = decodeURIComponent(actual[i]); } catch { matches = false; break; }
        if (!recordId || recordId.includes("/")) matches = false;
      } else if (expected[i] !== actual[i]) matches = false;
    }
    if (matches) return { route, recordId };
  }
  return null;
}

export function selectionDiff(initial, selected) {
  const a = new Set(initial), b = new Set(selected);
  return { grant: [...b].filter(c => !a.has(c)).sort(), revoke: [...a].filter(c => !b.has(c)).sort() };
}

export function routeVisible(route, access) {
  if (access?.super_admin) return true;
  if (route.admin) return false;
  if (route.path.startsWith("/shared/") || route.kind === "settings") return true;
  if (route.kind === 'input-list' && access?.authority === 'super_admin')
    return Boolean(access.features?.includes(route.feature)
      && access.permissions?.includes(`registry.${route.feature}.read`));
  return Boolean(route.feature && access?.features?.includes(route.feature)
    && (!route.permission || access.permissions.includes(route.permission)));
}

// Current owner decision: five top-level workspaces, with reference trees inside Inputs.
export function workspaceNavigation(routes, scope) {
  const prefix = scope === 'admin' ? '/admin' : '/institution';
  const page = path => routes.filter(r => r.path === path);
  const intake = routes.filter(r => r.kind === 'input-list' && r.feature !== 'inputs.insurers');
  return [
    ['الرئيسية', 'Home', page(`${prefix}/dashboard`)],
    ['المدخلات', 'Inputs', intake],
    ['التدقيق والمراجعة', 'Audit and review', page(`${prefix}/audit-workspace`)],
    ['التقارير', 'Reports', page(`${prefix}/result-reports`)],
    ['الإدارة', 'Administration', page(`${prefix}/administration`)],
  ];
}

export function isWorkspacePage(route) {
  return route.kind === 'input-list' && route.feature !== 'inputs.insurers'
    || /\/(dashboard|audit-workspace|result-reports|administration)$/.test(route.path);
}

export function navigationGroups(routes, scope) {
  const intake = routes.filter(r => r.kind === "input-list");
  const rest = routes.filter(r => r.kind !== "input-list");
  const groups = scope === "admin" ? [
    ["الإدارة المركزية", "Central administration", rest],
  ] : [
    ["الرئيسية", "Home", rest.filter(r => r.feature === "dashboard.summary")],
    ["المطالبات والدفعات", "Claims and batches", rest.filter(r => r.feature?.startsWith("claims."))],
    ["التدقيق والمراجعة", "Audit and review", rest.filter(r => r.feature?.startsWith("audit.") || r.feature?.startsWith("governance."))],
    ["التحليلات", "Analytics", rest.filter(r => r.feature?.startsWith("intelligence."))],
    ["التقارير", "Reports", rest.filter(r => r.feature?.startsWith("reports."))],
    ["مستخدمو الجهة", "Institution users", rest.filter(r => r.feature?.startsWith("users."))],
    ["الإعدادات والمساعدة", "Settings and help", rest.filter(r => !r.feature)],
  ];
  if (intake.length) groups.splice(scope === "admin" ? 1 : 1, 0, ["المدخلات والبيانات", "Inputs and data", intake]);
  return groups.filter(g => g[2].length);
}

// A focused institutional menu: seven sections, operational pages only.
export function institutionNavigation(routes) {
  const pages = routes.filter(route => route.kind !== "unavailable" && !route.path.includes(":id"));
  const paths = list => pages.filter(route => list.includes(route.path));
  return [
    ["الرئيسية", "Home", paths(["/institution/dashboard"])],
    ["المدخلات والبيانات", "Inputs and data", pages.filter(route => route.kind === "input-list")],
    ["المطالبات والدفعات", "Claims and batches", paths(["/institution/claims", "/institution/claims/batches"])],
    ["التدقيق والمراجعة", "Audit and review", paths(["/institution/financial-audit", "/institution/duplicates", "/institution/reviews", "/institution/appeals"])],
    ["التحليلات", "Analytics", paths(["/institution/ai-intelligence", "/institution/anomalies", "/institution/trends", "/institution/cost-optimization"])],
    ["التقارير", "Reports", paths(["/institution/reports"])],
    ["مستخدمو الجهة", "Institution users", paths(["/institution/users"])],
  ].filter(group => group[2].length);
}
