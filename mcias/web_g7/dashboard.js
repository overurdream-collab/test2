"use strict";
// G7 reporting front-end. No inline scripts, token persistence, external assets, or demo patient data.
(() => {
  const $ = id => document.getElementById(id);
  const state = {token:null, current:null, active:"overview", offset:0, archiveOffset:0, archiveMore:false};
  const labels = {
    overview:["نظرة عامة على المطالبات","المؤشرات مأخوذة من نسخة تقرير ثابتة قابلة للتحقق"],
    claims:["تفاصيل المطالبات","عرض محدود بالأدوار، من دون كشف أعمدة المصدر الطبي"],
    beneficiaries:["كشف المستفيد","الكشف متاح لمستخدمي المؤسسة المصرح لهم فقط"],
    archive:["أرشيف التقارير","تصفح النسخ الثابتة السابقة وحالتها"]
  };
  const reasonLabels = {
    awaiting_verified_approval:"بانتظار اعتماد موثّق",
    open_objection:"اعتراض مفتوح",unverified_calculation_hold:"حساب غير موثّق",
    financial_reconciliation_hold:"اختلاف في المطابقة المالية"
  };
  const actionLabels = {
    propose:"اقتراح",approve:"اعتماد",hold:"تعليق",reject:"رفض",object:"اعتراض",
    request_reaudit:"طلب إعادة تدقيق",link_reaudit:"ربط إعادة التدقيق"
  };
  const currencyLabels = {YER:"ريال يمني",USD:"دولار أمريكي",SAR:"ريال سعودي"};

  function node(tag, value, className) {
    const elem = document.createElement(tag);
    if (value !== undefined && value !== null) elem.textContent = String(value);
    if (className) elem.className = className;
    return elem;
  }
  function clear(element) { element.replaceChildren(); return element; }
  function appendLine(parent, title, value, arabic=false) {
    const line=node("div"), key=node("dt",title), result=node("dd",value);
    if( arabic ) result.className="arabic";
    line.append(key,result);parent.append(line);
  }
  function short(value, length=14) {
    const str=String(value || "—");
    return str.length>length ? str.slice(0,length)+"…" : str;
  }
  function money(value) {
    if(value === null || value === undefined) return "—";
    const str=String(value);
    if (!/^\d+(?:\.\d+)?$/.test(str)) return str;
    const [integer, fraction] = str.split(".");
    return integer.replace(/\B(?=(\d{3})+(?!\d))/g,",") + (fraction === undefined?"":"."+fraction);
  }
  function message(value, error=false) {
    const area=$("notice");
    area.textContent=String(value || "");
    area.className=error?"notice error":"notice";
    area.hidden=!value;
  }
  function busy(button, active) {
    if(button) button.disabled=active;
  }
  function resetAuthentication(showMessage=true) {
    state.token=null;state.current=null;
    $("workspace").hidden=true;
    $("loginPanel").hidden=false;
    $("logoutButton").hidden=true;
    $("connectionIndicator").classList.remove("connected");
    $("connectionIndicator").lastChild.textContent="غير متصل";
    $("pdfButton").disabled=true;$("excelButton").disabled=true;
    clear($("currencyCards"));clear($("claimsRows"));clear($("archiveList"));
    clear($("statementResult"));$("beneficiaryToken").value="";
    $("password").value="";$("mfaCode").value="";
    if (showMessage) message("انتهت الجلسة أو تم تسجيل الخروج. سجل دخولك مرة أخرى.");
  }
  async function api(path, {method="GET",data=null,binary=false}={}) {
    const headers={"Accept":binary?"*/*":"application/json"};
    if(state.token) headers.Authorization="Bearer "+state.token;
    if(data!==null) headers["Content-Type"]="application/json";
    const response=await fetch(path,{
      method,headers,body:data===null?undefined:JSON.stringify(data),
      cache:"no-store",credentials:"omit",referrerPolicy:"no-referrer"
    });
    if(response.status===401 && state.token) resetAuthentication(false);
    if(!response.ok) {
      let explanation="";
      try {
        const detail=await response.json();
        explanation=typeof detail.detail==="string"?detail.detail:"";
      } catch(_error) { /* no response body */ }
      const hint=response.status===403?"ليس لديك صلاحية لهذه العملية."
        :response.status===401?"بيانات الدخول غير صحيحة أو الجلسة منتهية."
        :response.status===404?"لم يتم العثور على التقرير أو المورد المطلوب."
        :response.status===409?"العملية متوقفة لعدم اكتمال الشروط أو سلامة البيانات."
        :"تعذرت العملية ("+response.status+").";
      throw new Error(explanation && response.status!==401 && response.status!==403
        ?hint+" "+explanation:hint);
    }
    if(binary) return response.blob();
    if(response.status===204) return null;
    return response.json();
  }
  function showTab(name) {
    if(!labels[name]) return;
    state.active=name;
    for(const section of ["overview","claims","beneficiaries","archive"]) {
      $("tab-"+section).hidden=section!==name;
    }
    for(const button of document.querySelectorAll("[data-tab]")) {
      const active=button.dataset.tab===name;
      button.classList.toggle("is-active",active);
      if(active) button.setAttribute("aria-current","page");
      else button.removeAttribute("aria-current");
    }
    $("viewTitle").textContent=labels[name][0];
    $("viewSubtitle").textContent=labels[name][1];
    message("");
    if(name==="claims" && state.current) void loadEntries();
    if(name==="archive") void loadArchive();
  }
  function metric(title, value, currency, caption, primary=false, symbol="◈") {
    const box=node("article",null,"metric-card"+(primary?" primary":""));
    const top=node("div",null,"metric-top");
    top.append(node("span",title,"metric-label"),node("span",symbol,"metric-icon"));
    const amount=node("div",value,"metric-value");
    const bottom=node("div",null,"metric-caption");
    if(currency)bottom.append(node("span",currency,"metric-currency"),node("span","  "+caption));
    else bottom.textContent=caption;
    box.append(top,amount,bottom);
    return box;
  }
  function renderSummary() {
    const report=state.current;
    if(!report)return;
    clear($("currencyCards"));clear($("statusBars"));clear($("provenanceList"));
    $("reportMeta").hidden=false;
    $("reportVersion").textContent="الإصدار "+report.version;
    $("reportHash").textContent="SHA-256: "+short(report.fingerprint,24);
    $("reportBatch").textContent="الدفعة "+short(report.batch_id);
    $("pdfButton").disabled=false;$("excelButton").disabled=false;
    $("reportIdInput").value=report.id;
    const totals=report.summary.by_currency || {};
    const currencySelect=$("currencyFilter");
    clear(currencySelect);
    currencySelect.append(node("option","جميع العملات"));
    currencySelect.firstChild.value="";
    for(const [currency,values] of Object.entries(totals)) {
      const option=node("option",currency+" — "+(currencyLabels[currency]||currency));
      option.value=currency;currencySelect.append(option);
      const cards=$("currencyCards");
      cards.append(
        metric("المبلغ المطالب به",money(values.claimed),currency,
          "عدد المطالبات "+values.approved_count+" معتمدة / "+values.held_count+" معلّقة",true,"▤"),
        metric("صافي المستحق المعتمد",money(values.payable),currency,"مبالغ معتمدة فقط",false,"✓"),
        metric("المبالغ المعلقة",money(values.held_claimed),currency,"لا تدخل في المستحق",false,"◷"),
        metric("إجمالي الخصومات",money(values.deductions),currency,"مخصومة من المعتمد فقط",false,"−")
      );
      const group=node("div",null,"currency-status");
      group.append(node("strong",currency+" — "+(currencyLabels[currency]||currency)));
      const total=values.approved_count+values.held_count;
      for(const [title,count,held] of [
        ["معتمدة",values.approved_count,false],["معلّقة",values.held_count,true]
      ]) {
        const line=node("div",null,"bar-row"),
              label=node("span",title,"bar-label"),
              track=node("div",null,"bar-track"),
              fill=node("div",null,"bar-fill"+(held?" held":"")),
              number=node("span",count,"bar-count");
        fill.style.width=(total?Math.min(100,Math.max(0,100*count/total)):0)+"%";
        track.append(fill);line.append(label,track,number);group.append(line);
      }
      $("statusBars").append(group);
    }
    if(!Object.keys(totals).length) {
      $("currencyCards").append(node("div","لا توجد مبالغ مالية ضمن هذه النسخة.","empty-state"));
      $("statusBars").append(node("div","لا توجد مطالبات لعرضها.","empty-state"));
    }
    appendLine($("provenanceList"),"معرّف التقرير",report.id);
    appendLine($("provenanceList"),"الإصدار",report.version);
    appendLine($("provenanceList"),"بصمة سلامة التقرير",report.fingerprint);
    appendLine($("provenanceList"),"بصمة الملف الأصلي",report.source_sha256);
    appendLine($("provenanceList"),"إجمالي عدد المطالبات",report.summary.total_claims);
  }
  async function selectReport(reportId) {
    if(!state.token)return;
    const id=String(reportId).trim();
    if(!id || id.length>36) {message("تحقق من معرّف التقرير.",true);return;}
    try{
      const report=await api("/api/v1/reports/snapshots/"+encodeURIComponent(id));
      state.current=report;state.offset=0;
      renderSummary();message("تم فتح النسخة الثابتة رقم "+report.version+".");
      if(state.active==="claims") await loadEntries();
      if(state.active==="archive") await loadArchive();
    }catch(error){message(error.message,true);}
  }
  async function loadArchive() {
    if(!state.token)return;
    const area=clear($("archiveList"));
    try {
      const result=await api("/api/v1/report-explorer/snapshots?limit=10&offset="+state.archiveOffset);
      state.archiveMore=result.has_more;
      $("archivePrev").disabled=state.archiveOffset===0;
      $("archiveNext").disabled=!result.has_more;
      $("archivePageLabel").textContent="من "+(state.archiveOffset+1)+" إلى "+(state.archiveOffset+result.items.length);
      if(!result.items.length)area.append(node("div","لا توجد إصدارات محفوظة. يمكن إنشاء نسخة من دفعة مكتملة.","empty-state"));
      for(const report of result.items) {
        const item=node("div",null,"archive-item"),
              title=node("div",null,"archive-title"),
              version=node("span","v"+report.version,"archive-version"),
              text=node("div"),
              caption=node("small","SHA-256: "+short(report.fingerprint,22)),
              open=node("button","فتح النسخة","btn btn-outline");
        text.append(node("strong","دفعة "+short(report.batch_id,16)),caption);
        title.append(version,text);
        open.type="button";open.addEventListener("click",()=>void selectReport(report.id));
        item.append(title,open);area.append(item);
      }
    } catch(error) {area.append(node("div",error.message,"empty-state")); }
  }
  async function loadEntries(){
    if(!state.current)return;
    const area=clear($("claimsRows"));
    $("evidencePanel").hidden=true;
    const query=new URLSearchParams({limit:"50",offset:String(state.offset)});
    if($("stateFilter").value)query.set("state",$("stateFilter").value);
    if($("currencyFilter").value)query.set("currency",$("currencyFilter").value);
    try{
      const result=await api("/api/v1/report-explorer/snapshots/"+
        encodeURIComponent(state.current.id)+"/entries?"+query.toString());
      $("prevPage").disabled=state.offset===0;
      $("nextPage").disabled=state.offset+result.items.length>=result.total;
      $("claimsPageLabel").textContent=result.total ?
        "عرض "+(state.offset+1)+"–"+(state.offset+result.items.length)+" من "+result.total : "لا توجد مطالبات";
      if(!result.items.length){
        const tr=node("tr"),td=node("td","لا توجد مطالبات مطابقة أو لا توجد بيانات.","empty-state");
        td.colSpan=6;tr.append(td);area.append(tr);return;
      }
      for(const row of result.items) {
        const tr=node("tr");
        for(const [value,css] of [
          [short(row.claim_id,20),"mono"],[row.currency,"num"],
          [money(row.claimed),"num"],[money(row.payable),"num"]
        ]) tr.append(node("td",value,css));
        const statusTd=node("td"),
              pill=node("span",row.state==="approved"?"معتمدة":"معلّقة",
                        "status-pill"+(row.state==="approved"?" approved":""));
        statusTd.append(pill);tr.append(statusTd);
        const detailsTd=node("td"),btn=node("button","عرض الأدلة","text-button");
        btn.type="button";btn.addEventListener("click",()=>void loadEvidence(row));
        detailsTd.append(btn);tr.append(detailsTd);area.append(tr);
      }
    }catch(error){
      $("claimsPageLabel").textContent="";
      const tr=node("tr"),td=node("td",error.message);
      td.colSpan=6;tr.append(td);area.append(tr);
      $("prevPage").disabled=true;$("nextPage").disabled=true;
    }
  }
  async function loadEvidence(row){
    const panel=$("evidencePanel");
    const dl=clear($("evidenceInfo"));panel.hidden=false;
    appendLine(dl,"معرّف المطالبة",row.claim_id);
    appendLine(dl,"الحالة",row.state==="approved"?"معتمدة":"معلّقة",true);
    appendLine(dl,"سبب التعليق",reasonLabels[row.hold_reason]||"—",true);
    appendLine(dl,"مبلغ المطالبة",money(row.claimed)+" "+row.currency);
    appendLine(dl,"المستحق المعتمد",money(row.payable)+" "+row.currency);
    appendLine(dl,"بصمة مرجع التدقيق",row.audit_snapshot_id||"غير متاح");
    appendLine(dl,"مرجع الحوكمة",row.governance_case_id||"غير متاح");
    if(row.audit_snapshot_id){
      try {
        const audit=await api("/api/v1/audits/"+encodeURIComponent(row.audit_snapshot_id));
        const statuses=(audit.findings&&audit.findings.agents)||[];
        appendLine(dl,"نتيجة التحقق",audit.verification.status==="verified"?"موثّق":"معلّق",true);
        appendLine(dl,"فحوصات المحرك",statuses.length+" فحوصات");
        appendLine(dl,"عدد التنبيهات",statuses.filter(item=>item.status!=="pass").length);
      }catch(_error){appendLine(dl,"تفاصيل التدقيق","تحتاج صلاحية إضافية",true);}
    }
    if(row.governance_case_id){
      try {
        const gov=await api("/api/v1/governance/cases/"+encodeURIComponent(row.governance_case_id));
        const latest=gov.events.length?gov.events[gov.events.length-1]:null;
        appendLine(dl,"عدد أحداث الحوكمة",gov.events.length);
        appendLine(dl,"آخر إجراء",latest?(actionLabels[latest.kind]||latest.kind):"لا توجد أحداث",true);
      }catch(_error){appendLine(dl,"تفاصيل الحوكمة","تحتاج صلاحية إضافية",true);}
    }
  }
  async function downloadReport(kind) {
    if(!state.current)return;
    const btn=kind==="pdf"?$("pdfButton"):$("excelButton");
    busy(btn,true);
    try {
      const suffix=kind==="pdf"?"/pdf?lang=ar":"/excel?lang=ar";
      const blob=await api("/api/v1/reports/snapshots/"+
        encodeURIComponent(state.current.id)+suffix,{binary:true});
      const objectUrl=URL.createObjectURL(blob);
      const anchor=document.createElement("a");
      anchor.href=objectUrl;anchor.download="MCIAS-G7-v"+state.current.version+
        (kind==="pdf"?".pdf":".xlsx");
      document.body.append(anchor);anchor.click();anchor.remove();
      setTimeout(()=>URL.revokeObjectURL(objectUrl),2000);
      message("اكتمل تجهيز ملف "+(kind==="pdf"?"PDF":"Excel")+" للنسخة المحفوظة.");
    }catch(error){message(error.message,true);}
    finally{busy(btn,false);}
  }
  async function loadStatement(event){
    event.preventDefault();
    if(!state.current){message("افتح نسخة تقرير أولاً.",true);return;}
    const token=$("beneficiaryToken").value.trim();
    if(!token)return;
    const area=clear($("statementResult"));
    try {
      const response=await api("/api/v1/reports/snapshots/"+
        encodeURIComponent(state.current.id)+"/beneficiary-statement",{
          method:"POST",data:{beneficiary_token:token}
        });
      $("beneficiaryToken").value="";
      area.append(node("h4","نتائج الكشف — "+response.items.length+" مطالبة"));
      if(!response.items.length){area.append(node("p","لا توجد مطالبات مطابقة في هذه النسخة."));return;}
      for(const record of response.items){
        const line=node("div",null,"statement-row");
        line.append(node("span","المرجع: "+record.claim_reference),
          node("span",money(record.claimed)+" "+record.currency,"num"),
          node("span",record.state==="approved"?"مستحق: "+money(record.payable)+" "+record.currency:
            "معلّقة — "+(reasonLabels[record.hold_reason]||"تحتاج مراجعة")));
        area.append(line);
      }
    }catch(error){$("beneficiaryToken").value="";area.append(node("p",error.message));}
  }
  async function login(event) {
    event.preventDefault();
    const btn=$("loginButton");busy(btn,true);message("");
    try {
      const payload={username:$("username").value.trim(),password:$("password").value};
      if($("mfaCode").value.trim()) payload.totp_code=$("mfaCode").value.trim();
      const result=await api("/api/v1/auth/login",{method:"POST",data:payload});
      if(!result.access_token) throw new Error("لم يُصدر رمز جلسة.");
      state.token=result.access_token;
      $("password").value="";$("mfaCode").value="";
      $("loginPanel").hidden=true;$("workspace").hidden=false;
      $("logoutButton").hidden=false;
      $("connectionIndicator").classList.add("connected");
      $("connectionIndicator").lastChild.textContent="جلسة نشطة";
      await loadArchive();
      if(state.archiveOffset===0) {
        try {
          const listing=await api("/api/v1/report-explorer/snapshots?limit=1&offset=0");
          if(listing.items.length) await selectReport(listing.items[0].id);
          else message("تم تسجيل الدخول. لا توجد تقارير مجمدة بعد؛ يمكنك إنشاء نسخة من دفعة مستوردة.");
        }catch(_error){message("تم تسجيل الدخول. قد تحتاج صلاحية قراءة التقارير.");}
      }
    }catch(error){message(error.message,true);}
    finally{busy(btn,false);}
  }
  function events() {
    $("loginForm").addEventListener("submit",event=>void login(event));
    $("logoutButton").addEventListener("click",async()=>{
      try{await api("/api/v1/auth/logout",{method:"POST"});}catch(_error){}
      resetAuthentication(true);
    });
    document.querySelectorAll("[data-tab]").forEach(btn=>btn.addEventListener(
      "click",()=>showTab(btn.dataset.tab)));
    $("openReportForm").addEventListener("submit",event=>{
      event.preventDefault();void selectReport($("reportIdInput").value);
    });
    $("freezeForm").addEventListener("submit",async event=>{
      event.preventDefault();
      const id=$("batchIdInput").value.trim();
      if(!id || id.length>36){message("تحقق من معرّف الدفعة.",true);return;}
      try{
        const report=await api("/api/v1/reports/batches/"+
          encodeURIComponent(id)+"/snapshots",{method:"POST"});
        message("تم تجميد التقرير وإسناد الإصدار "+report.version+".");
        await selectReport(report.id);
        state.archiveOffset=0;await loadArchive();
      }catch(error){message(error.message,true);}
    });
    $("refreshButton").addEventListener("click",()=>state.current ?
      void selectReport(state.current.id):void loadArchive());
    $("excelButton").addEventListener("click",()=>void downloadReport("excel"));
    $("pdfButton").addEventListener("click",()=>void downloadReport("pdf"));
    $("claimsFilter").addEventListener("submit",event=>{
      event.preventDefault();state.offset=0;void loadEntries();
    });
    $("prevPage").addEventListener("click",()=>{
      state.offset=Math.max(0,state.offset-50);void loadEntries();
    });
    $("nextPage").addEventListener("click",()=>{state.offset+=50;void loadEntries();});
    $("archiveRefresh").addEventListener("click",()=>void loadArchive());
    $("archivePrev").addEventListener("click",()=>{
      state.archiveOffset=Math.max(0,state.archiveOffset-10);void loadArchive();
    });
    $("archiveNext").addEventListener("click",()=>{state.archiveOffset+=10;void loadArchive();});
    $("statementForm").addEventListener("submit",event=>void loadStatement(event));
  }
  events();
})();