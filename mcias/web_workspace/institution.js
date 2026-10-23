import { L, el, icon, link, button, badge, panel, kpi, loading, empty, errorState,
  field, openDrawer, confirm, toast, preferences } from "./ui.js";

const sections = [
  ["المدخلات والبيانات", "Inputs and data", "/institution/inputs/contracts", "ingestion", "العقود، شركات التأمين، المستفيدون ومقدمو الخدمة", "Contracts, insurers, beneficiaries and providers"],
  ["المطالبات والدفعات", "Claims and batches", "/institution/claims", "claims", "متابعة المطالبات والدفعات المستوردة", "Track imported claims and batches"],
  ["التدقيق والمراجعة", "Audit and review", "/institution/reviews", "audit", "النتائج والأدلة والمراجعات والاعتراضات", "Findings, evidence, reviews and appeals"],
  ["التحليلات", "Analytics", "/institution/ai-intelligence", "ai", "تحليل البيانات والإشارات والاتجاهات", "Data analysis, signals and trends"],
  ["التقارير", "Reports", "/institution/reports", "reports", "التقارير المحفوظة والتصدير المصرح", "Frozen reports and authorized exports"],
  ["مستخدمو الجهة", "Institution users", "/institution/users", "beneficiaries", "إدارة الموظفين وإسناد الفئات المعتمدة", "Manage employees and assign approved groups"],
];

export function institutionOverview(ctx) {
  const hero = el("section", null, "hero institution-hero"), text = el("div");
  text.append(badge(L("مساحة مدير الجهة", "Institution administrator workspace")),
    el("h2", ctx.context.organization?.name || L("الجهة", "Organization")),
    el("p", L("نظرة واحدة على سجلات الجهة، ومتابعة العمل من الإدخال إلى التقرير.",
      "One view of organization records, from intake through reporting.")));
  hero.append(text, icon("dashboard")); ctx.root.append(hero);
  const output = el("div"); ctx.root.append(output);
  const links = el("div", null, "grid institution-sections");
  for (const [ar, en, path, asset, descriptionAr, descriptionEn] of sections) {
    if (!ctx.visibleRoute(path)) continue;
    const card = link("", path, "feature-card");
    card.append(icon(asset), el("h3", L(ar, en)), el("p", L(descriptionAr, descriptionEn)));
    links.append(card);
  }
  ctx.root.append(panel(L("مساحات العمل", "Workspaces"), L("اختر القسم لمتابعة العمل.", "Choose a section to continue.")));
  ctx.root.lastChild.append(links);
  async function load() {
    output.replaceChildren(loading());
    const responses = await Promise.allSettled([
      ctx.api.request("/api/v1/institution/overview"), ctx.api.request("/health/live"), ctx.api.request("/health/ready"),
    ]);
    output.replaceChildren();
    if (responses[0].status === "rejected") output.append(errorState(responses[0].reason, load));
    else {
      const data = responses[0].value;
      const freshness = el("div", null, "institution-freshness");
      freshness.append(badge(L("بيانات الجهة الحالية", "Current organization data")),
        el("span", L("آخر تحديث: ", "Retrieved: ") + new Date(data.retrieved_at).toLocaleString(preferences.lang)),
        el("span", L("آخر عملية استخراج مسجلة: ", "Latest extracted job created: ") +
          (data.last_extracted_job_created_at ? new Date(data.last_extracted_job_created_at).toLocaleString(preferences.lang) : L("لم يُسجّل بعد", "Not recorded yet"))));
      output.append(freshness);
      const grid = el("div", null, "grid institution-kpis"); grid.id = "institution-metrics";
      const definitions = [
        ["beneficiaries", "عدد المستفيدين", "Beneficiaries", "beneficiaries", "/institution/beneficiaries/names",
          "مستفيدون حاليون دون تكرار بين سجل الأهلية وسجل الأسماء.", "Current unique beneficiaries across enrollment and names."],
        ["insurers", "شركات التأمين المتعاقد معها", "Contracted insurance companies", "claims", "/institution/inputs/insurers",
          "شركات مسجلة بعقود حالية؛ تسجيل العقد لا يعني تفعيل سياسة مالية.", "Unique insurers with registered current contracts; registration does not activate financial policy."],
        ["providers", "عدد مقدمي الخدمات", "Healthcare providers", "hospitals", "/institution/providers/hospitals",
          "رموز مقدمي الخدمة الفريدة في السجلات الحالية والعقود المعتمدة السارية.", "Unique current provider codes from registry and effective approved contracts."],
        ["users", "عدد المستخدمين للنظام", "System users", "security", "/institution/users",
          "حسابات الجهة النشطة والسارية، دون هويات التوقيع الاصطناعية الداخلية.", "Active, effective organization accounts, excluding internal synthetic signing principals."],
      ];
      for (const [key, ar, en, asset, path, noteAr, noteEn] of definitions) {
        const metric = data.metrics[key], available = metric.status === "available";
        const card = kpi(L(ar, en), available ? new Intl.NumberFormat(preferences.lang).format(metric.value) : "—",
          asset, available ? L(noteAr, noteEn) : L("لا توجد صلاحية لهذا المؤشر", "This metric is restricted"),
          available && ctx.visibleRoute(path) ? path : null);
        card.dataset.metric = key;
        const evidence = el("details", null, "metric-provenance");
        evidence.append(el("summary", L("مصدر المؤشر", "Metric source")), el("p", L(noteAr, noteEn)),
          el("code", metric.sources.join(" + ") || "—")); card.append(evidence); grid.append(card);
      }
      const healthy = responses[1].status === "fulfilled" && responses[1].value.status === "ok"
        && responses[2].status === "fulfilled" && responses[2].value.status === "ready";
      const health = kpi(L("صحة النظام", "System health"), healthy ? L("جاهز", "Ready") : L("تعذر التحقق", "Not verified"),
        "security", L("فحص مباشر لخدمة التطبيق واتصال قاعدة البيانات.", "Live checks of the application and database connection."));
      health.dataset.metric = "health";
      health.append(button(L("إعادة الفحص", "Check again"), load, "link-button")); grid.append(health); output.append(grid);
      if (definitions.every(([key]) => data.metrics[key].value === 0))
        output.append(empty(L("ابدأ بإدخال بيانات الجهة", "Start adding organization data"),
          L("ستتحدث الأعداد من السجلات التي تحفظها، دون أرقام تجريبية مختلقة.", "Counts update from saved records; no invented demo totals."), "ingestion", true));
    }
  }
  void load();
}

export function institutionUsers(ctx) {
  if (ctx.demo) { ctx.root.append(empty(L("مستخدمو الجهة", "Institution users"), L("إدارة الحسابات تتطلب جلسة مصرحًا بها.", "Account management requires an authorized session."))); return; }
  const can = code => ctx.context.permissions.includes(code);
  const card = panel(L("إدارة مستخدمي الجهة", "Manage organization users"),
    L("أنشئ حساب الموظف ثم أسند له فئة وافقت عليها الجهة. الحسابات المغلقة والتاريخ تبقى محفوظة.",
      "Create an employee account, then assign an institution-approved group. Closed accounts and history are retained."), "security");
  const actions = el("div", null, "actions"), filters = el("form", null, "filters"), target = el("div");
  const search = field("staff-search", L("بحث في المستخدمين", "Search users"), {required:false,maxLength:120});
  const status = field("staff-status", L("حالة الحساب", "Account status"), {required:false,options:[["",L("الكل","All")],["open",L("مفتوح","Open")],["closed",L("مغلق","Closed")]]});
  const submit = el("button", L("بحث", "Search"), "button"); submit.type = "submit";
  filters.append(search.wrap,status.wrap,submit); let offset=0, generation=0;
  filters.addEventListener("submit", event=>{event.preventDefault();offset=0;void load();});
  status.input.addEventListener("change",()=>{offset=0;void load();});
  if(can("users.create")) actions.append(button(L("إضافة مستخدم", "Add user"),create,"button primary","plus"));
  actions.append(button(L("تحديث القائمة", "Refresh list"),()=>void load(),"button","refresh"));
  card.append(actions,filters,target);ctx.root.append(card);

  function closeDrawer(){document.getElementById("drawer").close();}
  function create(){
    const form=el("form"),grid=el("div",null,"form-grid"),result=el("div");result.setAttribute("aria-live","polite");
    const fields=[field("staff-username",L("اسم المستخدم","Username"),{maxLength:120}),
      field("staff-name",L("الاسم الكامل","Full name"),{maxLength:200,required:false}),
      field("staff-email",L("البريد الإلكتروني","Email"),{type:"email",maxLength:200,required:false}),
      field("staff-password",L("كلمة المرور الأولية","Initial password"),{type:"password",maxLength:1024})];
    fields[3].input.minLength=12;fields[3].input.autocomplete="new-password";
    fields.forEach(f=>grid.append(f.wrap));
    const save=el("button",L("إنشاء الحساب","Create account"),"button primary");save.type="submit";
    form.append(grid,el("p",L("12 حرفًا على الأقل. لا تمنح إضافة الحساب أي صلاحيات تلقائيًا.","At least 12 characters. Creating an account grants no automatic permissions."),"muted"),save,result);
    form.addEventListener("submit",async event=>{
      event.preventDefault();if(save.disabled||!form.reportValidity())return;save.disabled=true;
      try{const user=await ctx.api.request("/api/v1/users",{method:"POST",body:{username:fields[0].input.value.trim(),full_name_ar:fields[1].input.value.trim()||null,email:fields[2].input.value.trim()||null,password:fields[3].input.value}});
        closeDrawer();toast(L("تم إنشاء الحساب. أسند فئة لتفعيل صلاحياته.","Account created. Assign a group to enable permissions."));await load();await show({...user,manageable:true,groups:[]});
      }catch(error){result.replaceChildren(errorState(error));}finally{fields[3].input.value="";save.disabled=false;}
    });openDrawer(L("إضافة مستخدم للجهة","Add organization user"),form);
  }

  async function show(user){
    const body=el("div");body.append(el("h3",user.full_name_ar||user.username),el("p",user.username),
      badge(user.status==="open"?L("مفتوح","Open"):L("مغلق","Closed")),
      el("p",L("تاريخ الإنشاء: ","Created: ")+new Date(user.created_at).toLocaleString(preferences.lang)),
      el("p",L("بداية السريان: ","Effective from: ")+user.effective_from));
    if(user.effective_to)body.append(el("p",L("تاريخ الإغلاق: ","Closed: ")+user.effective_to));
    const groupSection=el("div"),feedback=el("div");feedback.setAttribute("aria-live","polite");
    body.append(el("h3",L("الفئات المسندة","Assigned groups")),groupSection);
    for(const group of user.groups){
      const line=el("div",null,"staff-group");line.append(el("span",L(group.name_ar,group.name_en||group.name_ar)));
      if(user.manageable&&user.status==="open"&&can("groups.members.remove"))line.append(button(L("إزالة الإسناد","Remove assignment"),()=>reasonAction(L("إزالة إسناد الفئة","Remove group assignment"),`/api/v1/groups/${group.id}/members/${user.id}/remove`)));
      groupSection.append(line);
    }
    if(!user.groups.length)groupSection.append(el("p",L("لا توجد فئة مسندة. لا يكتسب الحساب صلاحيات تشغيل تلقائيًا.","No assigned group. Operational permissions are not granted automatically."),"muted"));
    if(user.manageable&&user.status==="open"&&can("groups.members.add")&&can("groups.read")){
      const add=button(L("إسناد فئة معتمدة","Assign approved group"),async()=>{
        add.disabled=true;feedback.replaceChildren(loading());
        try{const response=await ctx.api.request("/api/v1/institution/assignment-groups");
          const options=response.items.filter(g=>!user.groups.some(current=>current.id===g.id));
          if(!options.length){feedback.replaceChildren(empty(L("لا توجد فئات إضافية","No additional groups"),L("تحتاج الفئات إلى إعداد واعتماد مسبق من Super Admin والجهة.","Groups require prior configuration and institutional approval."),"security",true));return;}
          const form=el("form"),choose=field("staff-group",L("الفئة الوظيفية","Functional group"),{options:options.map(g=>[g.id,L(g.name_ar,g.name_en||g.name_ar)])}),save=el("button",L("تأكيد الإسناد","Confirm assignment"),"button primary");save.type="submit";
          form.append(choose.wrap,save);feedback.replaceChildren(form);
          form.addEventListener("submit",async event=>{event.preventDefault();if(save.disabled||!form.reportValidity())return;save.disabled=true;
            try{await ctx.api.request(`/api/v1/groups/${choose.input.value}/members`,{method:"POST",body:{user_id:user.id}});closeDrawer();await load();toast(L("تم إسناد الفئة","Group assigned"));}
            catch(error){feedback.append(errorState(error));save.disabled=false;}
          });
        }catch(error){feedback.replaceChildren(errorState(error));}finally{add.disabled=false;}
      });body.append(add);
    }
    if(user.manageable&&user.status==="open"&&can("users.close"))
      body.append(button(L("إغلاق الحساب","Close account"),()=>reasonAction(L("إغلاق حساب المستخدم","Close user account"),`/api/v1/users/${user.id}/close`)));
    if(!user.manageable)body.append(el("p",L("هذا حسابك أو حساب تقني محمي؛ تعديل الصلاحيات أو الإغلاق غير متاح هنا.","This is your own account or a protected technical identity; permission changes or closure are unavailable here."),"muted"));
    body.append(feedback);openDrawer(L("تفاصيل المستخدم","User details"),body);
    function reasonAction(title,path){
      const form=el("form"),reason=field("staff-reason",L("سبب الإجراء","Reason"),{type:"textarea",maxLength:2000}),save=el("button",L("تنفيذ الإجراء","Apply action"),"button primary"),result=el("div");save.type="submit";result.setAttribute("aria-live","polite");form.append(reason.wrap,save,result);
      form.addEventListener("submit",async event=>{event.preventDefault();if(save.disabled||!form.reportValidity())return;
        if(!await confirm(title))return;save.disabled=true;
        try{await ctx.api.request(path,{method:"POST",body:{reason:reason.input.value.trim()}});closeDrawer();await load();toast(L("تم تسجيل الإجراء","Action recorded"));}
        catch(error){result.replaceChildren(errorState(error));}finally{save.disabled=false;}
      });openDrawer(title,form);
    }
  }

  async function load(){
    const current=++generation;target.replaceChildren(loading());
    try{const params=new URLSearchParams({q:search.input.value.trim(),status:status.input.value,offset:String(offset),limit:"25"});if(!status.input.value)params.delete("status");
      const data=await ctx.api.request("/api/v1/institution/users?"+params);if(current!==generation)return;target.replaceChildren();
      if(!data.items.length)target.append(empty(L("لا توجد حسابات مطابقة","No matching accounts"),L("غيّر البحث أو أضف موظفًا جديدًا ضمن صلاحياتك.","Change the filter or add an employee under your permissions."),"security",true));
      const list=el("div",null,"staff-list");
      for(const user of data.items){const row=el("article",null,"staff-card"),identity=el("div");
        identity.append(el("h3",user.full_name_ar||user.username),el("p",user.username,"muted"),
          el("p",user.groups.map(g=>L(g.name_ar,g.name_en||g.name_ar)).join(" · ")||L("دون فئة مسندة","No assigned group")));
        row.append(identity,badge(user.status==="open"?L("مفتوح","Open"):L("مغلق","Closed")),button(L("إدارة الحساب","Manage account"),()=>void show(user)));list.append(row);
      }target.append(list);
      const paging=el("div",null,"pagination"),previous=button(L("السابق","Previous"),()=>{offset=Math.max(0,offset-25);void load();}),next=button(L("التالي","Next"),()=>{offset+=25;void load();});previous.disabled=offset===0;next.disabled=!data.has_more;paging.append(previous,el("span",L("الصفحة ","Page ")+(offset/25+1)),next);target.append(paging);
    }catch(error){if(current===generation)target.replaceChildren(errorState(error,load));}
  }
  void load();
}
