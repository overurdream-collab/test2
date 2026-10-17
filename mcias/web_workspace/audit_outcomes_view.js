/* Four mutually exclusive audit files. Read-only exports, not payment decisions. */
import { L, el, button, panel, field, loading, errorState, toast } from "./ui.js";

const OUTCOMES = [
  ["REJECTED_RULE_CERTAIN", "مرفوض وفق قاعدة قطعية", "Confirmed rule failure"],
  ["ACCEPTED_RULES", "مقبول بعد فحص القواعد", "Rules passed"],
  ["MISSING_ATTACHMENTS", "مرفقات غير مكتملة", "Missing attachments"],
  ["HUMAN_REVIEW", "يحتاج تدقيقًا بشريًا", "Human review required"],
];
export function auditOutcomesView(ctx) {
  const card = panel(L("الملفات الأربعة لنتائج التدقيق", "Four audit result files"),
    L("تصنيفات مبدئية من لقطات التدقيق المحفوظة؛ لا يمثل أي ملف إذنًا للصرف أو رفضًا نهائيًا.",
      "Provisional classifications from immutable audit snapshots; not payment or final rejection authorization."),
    "reports");
  card.classList.add("audit-outcome-panel");
  const form = el("form"), row = el("div", null, "reference-point-toolbar"),
    chosen = field("triage_batch_id", L("معرّف دفعة المطالبات", "Claims batch ID"),
      {pattern:"[a-zA-Z0-9_-]{1,120}", maxLength:120}), output = el("div");
  const submit = el("button", L("عرض النتائج", "Show results"), "button primary");
  submit.type = "submit";
  submit.disabled = ctx.demo || !ctx.context.permissions.includes("reports.read");
  row.append(chosen.wrap, submit);
  form.append(row, output);
  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    if (!form.reportValidity() || submit.disabled) return;
    const id = encodeURIComponent(chosen.input.value.trim());
    submit.disabled = true;
    output.replaceChildren(loading());
    try {
      const result = await ctx.api.request("/api/v1/audit-outcomes/batches/" + id + "/summary");
      output.replaceChildren();
      const note = el("p", L("النتائج للمراجعة وليست قرارات دفع.", "Review-only; not payment decisions."), "muted"),
        cards = el("div", null, "audit-outcome-grid");
      cards.append();
      for (const [kind, ar, en] of OUTCOMES) {
        const item = el("section", null, "audit-outcome-item"),
          count = el("strong", String(result.counts[kind] || 0)), text = el("span", L(ar, en)),
          download = button(L("تنزيل CSV", "Download CSV"), async () => {
            try {
              await ctx.api.download("/api/v1/audit-outcomes/batches/" + id +
                                     "/export/" + kind, "mcias-" + kind.toLowerCase() + ".csv");
              toast(L("تم تنزيل الملف المصرح", "Authorized file downloaded"));
            } catch(e) {toast(e.message);}
          }, "button");
        download.disabled = ctx.demo || !ctx.context.permissions.includes("reports.export");
        item.append(count, text, download);
        cards.append(item);
      }
      output.append(note, cards,
        el("p", L("إجمالي المطالبات: ", "Total claims: ") + result.total, "muted"));
    } catch(err) {output.replaceChildren(errorState(err));}
    finally {submit.disabled = ctx.demo || !ctx.context.permissions.includes("reports.read");}
  });
  card.append(form);
  ctx.root.append(card);
}
