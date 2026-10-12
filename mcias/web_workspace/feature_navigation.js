// Pure helpers: route matching and checkbox diffs never confer server authority.
export function matchRoute(routes, path) {
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
