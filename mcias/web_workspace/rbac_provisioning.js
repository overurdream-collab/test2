import {L,el,panel,button,loading,errorState,toast,table,confirm} from "./ui.js";

export function rbacProvisioning(ctx) {
  const card=panel(L("ترحيل محكوم للصلاحيات","Reviewed permission migration"),
    L("الفئات المعتمدة هي المصدر الوظيفي الوحيد. يحتفظ الترحيل بالمنح القديمة وأصلها؛ المعاينة لا تفعّلها. تعتمد الجهة الخطة بتوقيع مستقل قبل تطبيقها.",
      "Approved groups are the sole functional authority. Historical grants and provenance are retained; preview does not activate them. An independent institution signature is required."));
  const result=el("div"),actions=el("div",null,"actions");
  const load=async()=>{
    result.replaceChildren(loading());
    try {
      const plan=await ctx.api.request("/api/v1/admin/rbac/migration-preview");
      result.replaceChildren();
      const columns=[L("الفئة","Group"),L("النطاق","Scope"),L("الصلاحيات","Permissions"),L("العضويات","Memberships")];
      table(result,plan.groups.map(g=>({[columns[0]]:g.name_ar,[columns[1]]:g.scope,[columns[2]]:g.permissions.length,[columns[3]]:g.memberships.length})),{columns,caption:L("خطة مراجعة الصلاحيات","Permission review plan")});
      const exportPlan=button(L("تنزيل خطة المراجعة","Download review plan"),()=>{
        const url=URL.createObjectURL(new Blob([JSON.stringify(plan,null,2)],{type:"application/json"}));
        const link=el("a");link.href=url;link.download="rbac-review-plan.json";link.click();URL.revokeObjectURL(url);
      });
      result.append(el("p",L("المنح المستبعدة من المعاينة: ","Excluded source grants: ")+plan.excluded.length),exportPlan);
    } catch(error){result.replaceChildren(errorState(error,load));}
  };
  const form=el("form"),label=el("label",L("خطة معتمدة وموقّعة (JSON)","Approved signed plan (JSON)"));
  const input=el("input");input.id="rbac-signed-plan";input.type="file";input.accept=".json,application/json";input.required=true;label.htmlFor=input.id;
  const submit=el("button",L("التحقق وتطبيق الترحيل","Verify and apply migration"),"button primary");submit.type="submit";
  const feedback=el("div");feedback.setAttribute("aria-live","polite");
  form.append(label,input,submit,feedback);
  form.addEventListener("submit",async event=>{
    event.preventDefault();if(submit.disabled||!form.reportValidity())return;
    const file=input.files[0];if(file.size>2097152){feedback.replaceChildren(el("p",L("الحد الأقصى 2 ميغابايت","Maximum size: 2 MB")));return;}
    submit.disabled=true;
    try {
      const envelope=JSON.parse(await file.text());
      if(!await confirm(L("تطبيق الخطة المعتمدة؟","Apply the approved plan?"),L("سيُحفظ التوقيع وأصل كل منح. لا يمنح هذا الإجراء اعتمادًا ماليًا.","The signature and grant origins will be retained. This action confers no financial decision.")))return;
      const applied=await ctx.api.request("/api/v1/admin/rbac/apply",{method:"POST",body:envelope});
      feedback.replaceChildren(el("p",L("تم التطبيق. معرّف المراجعة: ","Applied. Review ID: ")+applied.id));
      await ctx.refreshAccess();
      input.value="";toast(L("تم توثيق الترحيل","Migration recorded"));await load();
    } catch(error){feedback.replaceChildren(errorState(error));}
    finally{submit.disabled=false;}
  });
  actions.append(button(L("تحديث المعاينة","Refresh preview"),load));
  card.append(actions,result,form);ctx.root.append(card);void load();
}
