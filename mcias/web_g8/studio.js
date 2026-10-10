"use strict";
/* MCIAS G8: same-origin, no patient details, no persistent auth tokens. */
(() => {
  const byId = name => document.getElementById(name);
  const app = {token:null, view:"summary", tasks:[], reports:[]};
  const names = {
    summary:["التحليل التاريخي للمطالبات","مؤشرات وصفية قابلة للتتبع إلى نسخ التقارير المالية."],
    signals:["إشارات للمراجعة","نتائج احتمالية تحتاج تدقيقاً بشرياً ولا تعني احتيالاً."],
    scenario:["المحاكاة الافتراضية","افتراضات تحليلية لا تعدّل السقوف أو الخصومات أو المطالبات."],
    studio:["استوديو المهام","إدارة الإصدارات والاختبارات والمراجعة المستقلة للمؤشرات."]
  };
  const taskStates = {draft:"مسودة",tested:"مُختبَرة",activated:"نشطة",deactivated:"موقوفة"};
  const dimensions = {provider:"مقدم الخدمة",service:"الخدمة",month:"الشهر"};
  const indicators = {hold_rate:"نسبة المطالبات المعلقة",provider_claimed_share:"تركيز المطالبات على مقدم خدمة"};

  function el(tag, content, cls) {
    const e=document.createElement(tag);
    if(content!==undefined && content!==null) e.textContent=String(content);
    if(cls)e.className=cls;
    return e;
  }
  function empty(name){const n=byId(name);n.replaceChildren();return n;}
  function warn(content,error=false) {
    const n=byId("g8Notice");n.textContent=String(content||"");
    n.hidden=!content;n.className=error?"notice error":"notice";
  }
  function value(input){return byId(input).value.trim();}
  function fmt(data){
    if(data===null||data===undefined)return "—";
    const s=String(data);
    if(!/^\d+(?:\.\d+)?$/.test(s))return s;
    const [x,y]=s.split(".");
    return x.replace(/\B(?=(\d{3})+(?!\d))/g,",")+(y===undefined?"":"."+y);
  }
  function brief(s,count=20){s=String(s||"—");return s.length>count?s.slice(0,count)+"…":s;}
  async function api(path, data, method="GET") {
    const headers={"Accept":"application/json"};
    if(app.token) headers.Authorization="Bearer "+app.token;
    if(data!==undefined)headers["Content-Type"]="application/json";
    const response=await fetch(path,{method,headers,
      body:data===undefined?undefined:JSON.stringify(data),
      cache:"no-store",credentials:"omit",referrerPolicy:"no-referrer"});
    if(response.status===401 && app.token) {
      authReset();throw new Error("انتهت الجلسة. يرجى تسجيل الدخول من جديد.");
    }
    if(!response.ok) {
      let detail="";
      try {
        const d=await response.json();
        detail=typeof d.detail==="string"?d.detail:"";
      }catch(_error){}
      const message=response.status===403?"صلاحيات المستخدم لا تسمح بهذا الإجراء."
        :response.status===404?"لم يتم العثور على المرجع المطلوب."
        :response.status===409?"تعذّر تنفيذ هذا الإجراء بسبب حالة المراجعة أو سلامة السجلات."
        :response.status===422?"يرجى التحقق من شروط الإدخال أو حد المجموعة المسموح."
        :"تعذّر الاتصال بالواجهة ("+response.status+").";
      throw new Error(message+(detail && ![401,403].includes(response.status)?" "+detail:""));
    }
    return response.status===204?null:response.json();
  }
  function authReset() {
    app.token=null;app.tasks=[];app.reports=[];
    byId("workArea").hidden=true;byId("loginSection").hidden=false;
    byId("logout").hidden=true;
    byId("g8Connected").classList.remove("connected");
    byId("connectionText").textContent="غير متصل";
    byId("password").value="";byId("otp").value="";
    empty("summaryOutput");empty("signalsOutput");empty("simulationOutput");empty("taskList");
    byId("manualSources").value="";
  }
  async function login(event){
    event.preventDefault();
    const button=byId("loginBtn");button.disabled=true;warn("");
    try{
      const credentials={username:value("user"),password:byId("password").value};
      if(value("otp"))credentials.totp_code=value("otp");
      const result=await api("/api/v1/auth/login",credentials,"POST");
      if(!result.access_token)throw new Error("لم يصدر رمز جلسة.");
      app.token=result.access_token;
      byId("loginSection").hidden=true;byId("workArea").hidden=false;
      byId("logout").hidden=false;
      byId("g8Connected").classList.add("connected");
      byId("connectionText").textContent="جلسة نشطة";
      byId("password").value="";byId("otp").value="";
      await Promise.all([loadReports(),loadTasks()]);
    }catch(error){warn(error.message,true);}
    finally{button.disabled=false;}
  }
  function changeView(view) {
    if(!names[view])return;
    app.view=view;
    document.querySelectorAll("[data-view]").forEach(button=>{
      const selected=button.dataset.view===view;
      button.classList.toggle("is-active",selected);
      if(selected)button.setAttribute("aria-current","page");
      else button.removeAttribute("aria-current");
    });
    for(const key of Object.keys(names))byId("view-"+key).hidden=key!==view;
    byId("currentTitle").textContent=names[view][0];
    byId("currentDescription").textContent=names[view][1];
    warn("");
    if(view==="studio")void loadTasks();
  }
  function selectedReports() {
    const manual=value("manualSources");
    const ids=manual?manual.split(/[,\n،;]/).map(s=>s.trim()).filter(Boolean):
      Array.from(byId("sources").selectedOptions,option=>option.value);
    if(ids.length<1||ids.length>12||new Set(ids).size!==ids.length||
       ids.some(s=>s.length>36||!s))throw new Error("حدد من 1 إلى 12 معرّف تقرير مختلف، دون تكرار.");
    return ids;
  }
  function updateSelection() {
    let count=0;
    try{count=selectedReports().length;}catch(_error){}
    byId("selectionCaption").textContent=count?"مصادر محددة: "+count:
      "يرجى اختيار مصدر أو إدخال معرّف التقرير.";
  }
  async function loadReports(){
    const selector=empty("sources");
    try {
      const response=await api("/api/v1/report-explorer/snapshots?limit=100&offset=0");
      app.reports=response.items;
      if(!app.reports.length){
        selector.append(el("option","لا توجد نسخ G7 محفوظة"));
        selector.firstChild.disabled=true;return;
      }
      for(const report of app.reports){
        const label="v"+report.version+" | "+brief(report.batch_id,12)+
                    " | "+report.summary.total_claims+" مطالبة";
        const option=el("option",label);
        option.value=report.id;
        selector.append(option);
      }
      selector.firstChild.selected=true;
      updateSelection();
    }catch(error) {
      selector.append(el("option","لا يمكن استعراض قائمة التقارير بهذه الصلاحية."));
      selector.firstChild.disabled=true;
      byId("selectionCaption").textContent="يمكن إدخال معرّفات التقارير يدوياً.";
    }
  }
  async function loadTasks(){
    const area=empty("taskList"), selector=empty("approvedTask");
    try{
      const result=await api("/api/v1/intelligence/studio/tasks?limit=100&offset=0");
      app.tasks=result.items;
      if(!result.items.length) area.append(el("div","لا توجد مهام تحليل محفوظة بعد.","empty-state"));
      for(const task of result.items){
        const item=el("div",null,"g8-task"),
              title=el("div",null,"g8-task-title"),
              controls=el("div",null,"g8-task-actions"),
              status=el("span",taskStates[task.status]||task.status,
                        "g8-badge"+(task.status==="activated"?" ready":
                                    task.status==="tested"?" warning":""));
        title.append(el("strong",task.code+" · v"+task.version),
                     el("small","SHA-256 "+brief(task.configuration_fingerprint,30)));
        controls.append(status);
        const transitions = task.status==="draft"?[["test","إجراء الاختبار"]]:
          task.status==="tested"?[["activate","تفعيل بموافقة مستقلة"]]:
          task.status==="activated"?[["deactivate","إيقاف"]]:[];
        for(const [action,label] of transitions) {
          const btn=el("button",label,"btn btn-ghost g8-small-button");
          btn.type="button";
          btn.addEventListener("click",()=>void taskAction(task,action));
          controls.append(btn);
        }
        item.append(title,controls);area.append(item);
        if(task.status==="activated"){
          const option=el("option",task.code+" — v"+task.version);
          option.value=task.id;selector.append(option);
        }
      }
      if(!selector.childElementCount) {
        const option=el("option","لا يوجد مؤشر نشط ومختبَر.");
        option.value="";option.disabled=true;selector.append(option);
      }
    }catch(error){
      area.append(el("div","لا توجد صلاحية للاطلاع على مهام الاستوديو.","empty-state"));
      selector.append(el("option","تحتاج صلاحية عرض مهام الاستوديو."));
      selector.firstChild.disabled=true;
    }
  }
  function resultHeader(run,title){
    const node=el("div",null,"g8-result-head");
    const text=el("div");
    text.append(el("h3",title),
                el("small","نتيجة محفوظة: "+brief(run.id,25),
                  "g8-source-fingerprint"));
    node.append(text,el("span","للمراجعة فقط","g8-badge"));
    return node;
  }
  function sourceFoot(run) {
    const p=el("p",null,"g8-note");
    const sourceList=run.sources.map(s=>"v"+s.version+" / "+brief(s.fingerprint,14)).join("، ");
    p.textContent="تتبع المصدر: "+sourceList+".  بصمة التحليل: "+brief(run.fingerprint,26)+
                  " — لا تُصدر القرارات المالية من هذه المخرجات.";
    return p;
  }
  function table(headings,records){
    const wrapper=el("div",null,"g8-data-grid");
    const t=el("table"),head=el("thead"),tr=el("tr"),body=el("tbody");
    headings.forEach(h=>tr.append(el("th",h)));
    head.append(tr);
    for(const row of records){
      const line=el("tr");
      row.forEach(cell=>line.append(el("td",cell)));
      body.append(line);
    }
    t.append(head,body);wrapper.append(t);return wrapper;
  }
  function renderSummary(run) {
    const area=empty("summaryOutput"),output=run.result.output;
    const panel=el("article",null,"panel");
    panel.append(resultHeader(run,"توزيع المطالبات حسب "+(dimensions[output.dimension]||output.dimension)));
    panel.append(el("p","إجمالي عينة المطالبات: "+output.denominator_count+
                      " | مجموعات محجوبة: "+output.suppressed_groups,"g8-note"));
    const rows=output.groups.map(x=>[
      x.group==="__suppressed__"?"مجموعات صغيرة محجوبة":x.group,
      x.currency,String(x.count),String(x.approved_count),String(x.held_count),
      fmt(x.claimed),fmt(x.payable),fmt(x.deductions),
      x.hold_rate_percent===null?"—":brief(x.hold_rate_percent,9)+"%"
    ]);
    if(rows.length)panel.append(table(
      ["المجموعة","العملة","عدد المطالبات","معتمدة","معلقة",
       "المطالب به","صافي المستحق","الخصومات","نسبة التعليق"],rows));
    else panel.append(el("div","لا توجد بيانات مطابقة في هذا المصدر.","empty-state"));
    panel.append(sourceFoot(run));area.append(panel);
  }
  function renderSignals(run){
    const area=empty("signalsOutput"),out=run.result.output;
    const panel=el("article",null,"panel");
    panel.append(resultHeader(run,"إشارات للمراجعة — "+(indicators[out.indicator]||out.indicator)));
    panel.append(el("p","عدد العناصر المفحوصة: "+out.sources_count+
      ". تنبيه إحصائي وليس تشخيصاً أو اتهاماً. يجب فحص الإيجابيات الكاذبة.","g8-note"));
    area.append(panel);
    if(!out.findings.length)area.append(el("div","لم تظهر إشارات تتجاوز العتبة والعينة المطلوبة. هذا لا يعني غياب المخاطر.","empty-state"));
    for(const signal of out.findings){
      const item=el("article",null,"panel g8-signal"),
            head=el("div",null,"g8-result-head");
      head.append(el("h3",(dimensions[signal.dimension]||signal.dimension)+" : "+
                            signal.group+" / "+signal.currency),
                  el("span","إشارة تحتاج مراجعة","g8-badge warning"));
      item.append(head,el("p","نتيجة تجاوز العتبة ضمن عينة محددة؛ لا يترتب عليها إجراء تلقائي."));
      const dl=el("dl",null,"g8-signal-metrics");
      for(const [label,val] of [
        ["المؤشر المرصود",brief(signal.observed_percent,9)+"%"],
        ["عتبة الإشارة",signal.threshold_percent+"%"],
        ["خط الأساس",brief(signal.baseline_percent,9)+"%"],
        ["حجم العينة",signal.sample_count+" / "+signal.cohort_count],
        ["البسط",fmt(signal.numerator)],["المقام",fmt(signal.denominator)]
      ]){
        const block=el("div");
        block.append(el("dt",label),el("dd",val));dl.append(block);
      }
      item.append(dl);area.append(item);
    }
  }
  function renderScenario(run){
    const area=empty("simulationOutput"),out=run.result.output;
    const panel=el("article",null,"panel");
    panel.append(resultHeader(run,"سيناريو افتراضي بنسبة "+
      out.assumption.approved_payable_reduction_percent+"%"));
    panel.append(el("p","المحاكاة للمقارنة فقط، ولا تغيّر مبالغ G5/G6/G7 أو تنشئ تعليمات صرف.","g8-note"));
    const cards=el("div",null,"g8-scenario-grid");
    for(const item of out.by_currency){
      const card=el("div",null,"g8-scenario-item");
      card.append(el("strong",item.currency+" — "+item.approved_count+" مطالبة معتمدة"),
        el("p","المستحق المسجل (خط الأساس)"),
        el("div",fmt(item.baseline_payable),"g8-figure"),
        el("p","المستحق الافتراضي"),
        el("div",fmt(item.hypothetical_payable),"g8-figure"),
        el("p","الفارق الافتراضي: "+fmt(item.hypothetical_difference)));
      cards.append(card);
    }
    panel.append(cards,sourceFoot(run));area.append(panel);
  }
  async function run(event,kind) {
    event.preventDefault();warn("");
    let reportIds;
    try{reportIds=selectedReports();}catch(error){warn(error.message,true);return;}
    const params=kind==="summary"?
      {dimension:value("summaryDimension"),min_group_size:Number(value("summaryPrivacy"))}:
      kind==="simulation"?{reduction_percent:value("assumedReduction")}:{};
    const taskId=kind==="signals"?value("approvedTask"):null;
    if(kind==="signals"&&!taskId){warn("يجب تحديد مؤشر مختبَر ونشط.",true);return;}
    const btn=event.submitter;if(btn)btn.disabled=true;
    try{
      const result=await api("/api/v1/intelligence/runs",
        {kind,report_ids:reportIds,parameters:params,task_id:taskId},"POST");
      if(kind==="summary")renderSummary(result);
      if(kind==="signals")renderSignals(result);
      if(kind==="simulation")renderScenario(result);
      warn("تم حفظ نتيجة التحليل ببصمة ومستندات مصدرية ثابتة.");
    }catch(error){warn(error.message,true);}
    finally{if(btn)btn.disabled=false;}
  }
  async function createTask(event){
    event.preventDefault();warn("");
    const code=value("taskCode");
    const indicator=value("indicator");
    const dimension=indicator==="provider_claimed_share"?"provider":value("taskDimension");
    const body={code,configuration:{
      source:"g7_frozen_report_snapshots",indicator,dimension,
      threshold_percent:value("taskThreshold"),
      min_group_size:Number(value("taskMin"))
    }};
    const btn=event.submitter;if(btn)btn.disabled=true;
    try{
      const task=await api("/api/v1/intelligence/studio/tasks",body,"POST");
      warn("تم إنشاء مسودة "+task.code+" الإصدار "+task.version+
           ". يجب إجراء اختبار ومراجعة من حساب مستقل قبل التفعيل.");
      await loadTasks();
    }catch(error){warn(error.message,true);}
    finally{if(btn)btn.disabled=false;}
  }
  async function taskAction(task,action){
    const label={test:"الاختبار",activate:"التفعيل",deactivate:"الإيقاف"}[action]||action;
    warn("");
    try{
      const event=await api("/api/v1/intelligence/studio/tasks/"+
        encodeURIComponent(task.id)+"/"+action,{},"POST");
      warn("تم تنفيذ "+label+" وتوثيق الحدث رقم "+event.version+
           ". هذا إجراء هندسي ولا يمثل اعتماداً مؤسسياً نهائياً.");
      await loadTasks();
    }catch(error){warn(error.message,true);}
  }
  function wire(){
    byId("loginForm").addEventListener("submit",ev=>void login(ev));
    byId("logout").addEventListener("click",async()=>{
      try{await api("/api/v1/auth/logout",{},"POST");}catch(_error){}
      authReset();
    });
    document.querySelectorAll("[data-view]").forEach(btn=>{
      btn.addEventListener("click",()=>changeView(btn.dataset.view));
    });
    byId("reloadReports").addEventListener("click",()=>void loadReports());
    byId("sources").addEventListener("change",updateSelection);
    byId("manualSources").addEventListener("input",updateSelection);
    byId("summaryForm").addEventListener("submit",event=>void run(event,"summary"));
    byId("signalsForm").addEventListener("submit",event=>void run(event,"signals"));
    byId("simulationForm").addEventListener("submit",event=>void run(event,"simulation"));
    byId("newTaskForm").addEventListener("submit",event=>void createTask(event));
    byId("refreshTasks").addEventListener("click",()=>void loadTasks());
    byId("indicator").addEventListener("change",()=>{
      const providerShare=value("indicator")==="provider_claimed_share";
      byId("taskDimension").value="provider";
      byId("taskDimension").disabled=providerShare;
    });
  }
  wire();
})();