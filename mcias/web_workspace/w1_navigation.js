// W1: adapted route matching/grouping ideas from Windows feature_navigation.js at 50ffd4bfd586.
// Main permissions are authoritative; no Windows entitlements, grants, or signatures.
export function matchRoute(routes, path) {
  const exact = routes.find(r => r.path === path);
  if (exact) return { route: exact, recordId: null };
  for (const route of routes) {
    const a = route.path.split('/'), b = path.split('/');
    if (a.length !== b.length) continue;
    let id = null, ok = true;
    for (let i = 0; i < a.length; i++) {
      if (a[i] !== ':id' && a[i] !== b[i]) { ok = false; break; }
      if (a[i] === ':id') {
        try { id = decodeURIComponent(b[i]); } catch { ok = false; break; }
        if (!id || id.includes('/')) { ok = false; break; }
      }
    }
    if (ok) return { route, recordId: id };
  }
  return null;
}
export function routeVisibleForContext(route, context) {
  if (!context || route.kind === 'missing' || route.kind === 'unavailable' || route.availability === 'unavailable') return false;
  const roles = context.roles || [], permissions = context.permissions || [];
  if (route.admin && !roles.includes('super_admin')) return false;
  return !route.permission || permissions.includes(route.permission);
}
export function navigationGroupsForContext(routes, scope, context) {
  const visible = routes.filter(r => !r.path.includes(':id') && routeVisibleForContext(r, context));
  if (scope === 'admin') return [['الإدارة المركزية', 'Central administration', visible]].filter(g => g[2].length);
  const groups = [
    ['الرئيسية', 'Overview', visible.filter(r => r.kind === 'dashboard')],
    ['المطالبات والدفعات', 'Claims and batches', visible.filter(r => ['claims','batches','documents','ingestion'].includes(r.kind))],
    ['التدقيق والمراجعة', 'Audit and review', visible.filter(r => ['audits','cases','appeals'].includes(r.kind))],
    ['التحليلات والتقارير', 'Analytics and reports', visible.filter(r => ['analysis','signals','reports','simulation'].includes(r.kind))],
    ['المستخدمون والإعدادات', 'Users and settings', visible.filter(r => ['users','user-detail','settings','profile'].includes(r.kind))],
  ];
  const used = new Set(groups.flatMap(g => g[2].map(r => r.path)));
  groups.push(['مساحات أخرى', 'Other workspaces', visible.filter(r => !used.has(r.path))]);
  return groups.filter(g => g[2].length);
}
