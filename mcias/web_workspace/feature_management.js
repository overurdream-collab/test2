import { L, el, panel, button, field, loading, empty, errorState, toast } from "./ui.js";
import { selectionDiff } from "./feature_navigation.js";

export function featuresManagement(ctx) {
  const { root, api, demo, recordId } = ctx;
  if (demo) {
    root.append(empty(L("إدارة ميزات الجهات", "Organization feature management"),
      L("العرض الاصطناعي للقراءة فقط. سجّل الدخول بحساب Super Admin لإدارة الميزات.",
        "The synthetic preview is read-only. Sign in as Super Admin to manage features."), "settings"));
    return;
  }
  const card = panel(L("الميزات المتاحة للجهة", "Organization entitlements"),
    L("تفعيل الميزة لا يمنح صلاحية المستخدم ولا يعتمد سياسة مالية.", "Entitlements do not grant user permissions or approve financial policies."), "settings");
  const target = el("div"); card.append(target); root.append(card);
  let generation = 0;
  async function load(offset = 0) {
    const current = ++generation;
    target.replaceChildren(loading());
    try {
      const [organizations, tree] = await Promise.all([
        api.request(`/api/v1/admin/feature-organizations?offset=${offset}&limit=100`),
        api.request("/api/v1/admin/features/tree"),
      ]);
      if (current !== generation || !target.isConnected) return;
      target.replaceChildren();
      if (!organizations.items.length) { target.append(empty(L("لا جهات", "No organizations"), L("لم تُسجل جهات متاحة.", "No organizations are registered."))); return; }
      const selector = field("feature-organization", L("الجهة", "Organization"), {
        options: organizations.items.map(o => [o.id, o.name]),
      });
      if (recordId && organizations.items.some(o => o.id === recordId)) selector.input.value = recordId;
      const content = el("div"), paging = el("div", null, "actions");
      target.append(selector.wrap, content, paging);
      if (offset) paging.append(button(L("السابق", "Previous"), () => load(Math.max(0, offset - 100))));
      if (organizations.has_more) paging.append(button(L("التالي", "Next"), () => load(offset + 100)));
      selector.input.addEventListener("change", () => void edit(selector.input.value));
      let editorGeneration = 0;
      async function edit(orgId) {
        const version = ++editorGeneration;
        content.replaceChildren(loading());
        try {
          const state = await api.request(`/api/v1/organizations/${encodeURIComponent(orgId)}/features`);
          if (version !== editorGeneration || !content.isConnected) return;
          const initial = state.items.map(r => r.feature_code), selected = new Set(initial);
          const form = el("form"), branches = el("div", null, "feature-tree"), checks = new Map();
          const reason = field("feature-revoke-reason", L("سبب سحب الميزات", "Reason for revocation"), { required: false, maxLength: 2000 });
          const feedback = el("div"); feedback.setAttribute("aria-live", "polite");
          for (const branch of tree.items) {
            const group = el("fieldset", null, "feature-branch"), legend = el("legend");
            const parent = el("input"); parent.type = "checkbox"; parent.id = `feature-parent-${branch.code}`;
            const label = el("label", L(branch.name_ar, branch.name_en)); label.htmlFor = parent.id;
            legend.append(parent, label); group.append(legend);
            function sync() {
              const count = branch.children.filter(c => selected.has(c.code)).length;
              parent.checked = count === branch.children.length && count > 0;
              parent.indeterminate = count > 0 && count < branch.children.length;
              for (const leaf of branch.children) checks.get(leaf.code).checked = selected.has(leaf.code);
            }
            parent.addEventListener("change", () => {
              for (const leaf of branch.children) parent.checked ? selected.add(leaf.code) : selected.delete(leaf.code);
              sync();
            });
            for (const leaf of branch.children) {
              const row = el("div", null, "feature-choice"), check = el("input"), text = el("label", L(leaf.name_ar, leaf.name_en));
              check.type = "checkbox"; check.id = `feature-leaf-${leaf.code}`; check.dataset.feature = leaf.code;
              text.htmlFor = check.id; checks.set(leaf.code, check);
              check.addEventListener("change", () => { check.checked ? selected.add(leaf.code) : selected.delete(leaf.code); sync(); });
              row.append(check, text); group.append(row);
            }
            sync(); branches.append(group);
          }
          const actions = el("div", null, "actions"), save = el("button", L("حفظ", "Save"), "button primary"); save.type = "submit";
          actions.append(save, button(L("إلغاء", "Cancel"), () => void edit(orgId)));
          form.append(branches, reason.wrap, actions, feedback);
          form.addEventListener("submit", async event => {
            event.preventDefault();
            if (save.disabled || !form.reportValidity()) return;
            const diff = selectionDiff(initial, selected);
            if (!diff.grant.length && !diff.revoke.length) { feedback.replaceChildren(el("p", L("لا تغييرات", "No changes"))); return; }
            if (diff.revoke.length && !reason.input.value.trim()) { reason.input.setCustomValidity(L("سبب السحب مطلوب", "Revocation reason is required")); reason.input.reportValidity(); return; }
            save.disabled = true; selector.input.disabled = true;
            try {
              await api.request(`/api/v1/organizations/${encodeURIComponent(orgId)}/features`, { method: "PUT", body: {
                codes: [...selected].sort(), expected_revision: state.revision, reason: reason.input.value.trim(),
              }});
              toast(L("تم حفظ ميزات الجهة", "Organization features saved"));
              await edit(orgId);
            } catch (error) { feedback.replaceChildren(errorState(error)); }
            finally { save.disabled = false; selector.input.disabled = false; }
          });
          reason.input.addEventListener("input", () => reason.input.setCustomValidity(""));
          content.replaceChildren(form);
        } catch (error) { content.replaceChildren(errorState(error, () => void edit(orgId))); }
      }
      await edit(selector.input.value);
    } catch (error) { target.replaceChildren(errorState(error, () => void load(offset))); }
  }
  void load();
}
