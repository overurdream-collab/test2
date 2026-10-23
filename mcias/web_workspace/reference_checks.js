import { L, el, button, panel, empty, loading, errorState, openDrawer } from './ui.js';

const labels={invoice:['فاتورة الخدمة — نقصها يعلّق البند','Service invoice — missing invoice holds the line'],beneficiary_enrollment:['وجود المستفيد وسريان الاشتراك','Beneficiary and enrollment validity'],beneficiary_name:['مطابقة الاسم','Name matching'],
  category:['الفئة','Category'],source_category:['الفئة الواردة','Source category'],provider:['المزود','Provider'],service:['الخدمة','Service'],
  provider_tariff:['تسعيرة المزود','Provider tariff'],contract:['العقد','Contract'],regulation:['اللائحة','Regulation'],copay_rule:['قاعدة التحمل للفئة والخدمة والشبكة','Category, service and network copay rule'],
  financial_basis:['أساس الحساب والتقريب','Calculation and rounding basis'],currency:['العملة','Currency'],price:['السعر','Price'],
  gross_total:['إجمالي السعر والكمية','Price and quantity total'],copay_percent:['نسبة التحمل','Copay percentage'],copay_amount:['مبلغ التحمل','Copay amount'],
  implied_copay:['التحمل المستنتج من الأصل','Copay implied by source'],source_arithmetic:['اتساق أرقام الشركة','Source arithmetic'],
  source_net_total:['الإجمالي الصافي','Net total'],net_amount:['الصافي بعد التحمل','Net after copay'],gross_amount:['السعر قبل التحمل','Gross before copay'],source_numbers:['سلامة الأرقام','Valid source amounts']};
const state=value=>({MATCHED:L('مطابق للفحص الأولي','Pre-check matched'),REVIEW_REQUIRED:L('اختلاف يحتاج مراجعة','Difference requiring review'),BLOCKED:L('مراجع أو بيانات ناقصة','Missing references or data'),pass:L('مطابق','Match'),difference:L('اختلاف','Difference'),hold:L('يتطلب استكمالًا','Requires completion')})[value]||value;

export async function referenceChecks(ctx,batchId,target,refresh){
  const canReview=ctx.context.permissions.includes('claims.review');
  const box=panel(L('فحص المطالبة مقابل المدخلات','Claim reference validation'),L('التحقق بتاريخ الخدمة: العقد واللائحة والمستفيد واشتراكه وفئته والخدمة والمزود والتسعيرة والتحمل. هذه مطابقة أولية وليست اعتمادًا ماليًا.','Service-date validation of contract, regulation, enrollment, category, service, provider, tariff and copay. This is a pre-check, not financial approval.'));
  target.append(box);if(!canReview){box.append(empty(L('صلاحية الفحص غير ممنوحة','Validation permission not granted'),L('يمنحها السوبر أدمن صراحة.','The super-admin must explicitly grant it.')));return;}
  const content=el('div');content.append(loading());box.append(content);
  box.append(button(L('فحص / إعادة فحص المدخلات','Validate / revalidate references'),async()=>{
    try{content.replaceChildren(loading());await ctx.api.request(`/api/v1/claims/batches/${batchId}/reference-checks`,{method:'POST'});await refresh();}
    catch(error){content.replaceChildren(errorState(error));}}));
  try{
    const result=await ctx.api.request(`/api/v1/claims/batches/${batchId}/reference-checks?limit=100`);
    const summary=el('p',`${L('مطابق','Matched')}: ${result.summary.MATCHED} · ${L('اختلاف','Difference')}: ${result.summary.REVIEW_REQUIRED} · ${L('ناقص','Incomplete')}: ${result.summary.BLOCKED}`);
    const wrap=el('div',null,'table-scroll'),table=el('table'),head=el('tr');
    for(const label of [L('البند','Line'),L('الحالة','Status'),L('الفئة','Category'),L('نوع الخدمة','Service type'),L('تحمل المستفيد','Beneficiary copay'),L('الصافي الأصلي','Source net'),L('الصافي المتوقع','Expected net'),L('الأدلة','Evidence')])head.append(el('th',label));
    const thead=el('thead');thead.append(head);table.append(thead);const body=el('tbody');
    for(const row of result.rows){const calc=row.calculation,tr=el('tr');
      for(const value of [row.line_id.slice(0,8),state(row.status),calc?.category_code||'—',calc?.service_type||'—',calc?calc.beneficiary_copay_percent+'%':'—',calc?.source_net||'—',calc?.expected_net||'—'])tr.append(el('td',value));
      const action=el('td');action.append(button(L('تفاصيل الفحص','Check details'),()=>{
        const details=el('div');for(const check of row.checks){const item=panel(L(...(labels[check.code]||[check.code,check.code])),state(check.status));
          for(const key of ['expected','source','source_gross','tariff_total','reason'])if(check[key]!==undefined)item.append(el('p',check[key]==='missing_invoice'?L('نقص المرفقات — فاتورة الخدمة غير متوفرة','Missing attachments — service invoice unavailable'):`${key}: ${check[key]}`));details.append(item);}
        details.append(el('h3',L('إصدارات المراجع المستخدمة','Reference versions used')));
        for(const [role,ref] of Object.entries(row.references))details.append(el('p',`${L(...(labels[role]||[role,role]))}: ${ref.id} · v${ref.version} · ${ref.effective_from} → ${ref.effective_to||'—'}`));
        openDrawer(L('فحص أولي — دون خصم تحمل ثانٍ','Pre-check — no second copay deduction'),details);
      }));tr.append(action);body.append(tr);}
    table.append(body);wrap.append(table);content.replaceChildren(summary,wrap);
    if(result.has_more)content.append(el('p',L('تظهر أول 100 نتيجة؛ بقية البنود محفوظة ويمكن طلبها من API بالترقيم.','Showing the first 100 results; remaining rows are preserved and paginated through the API.')));
  }catch(error){content.replaceChildren(error.status===404?empty(L('لم يُنفذ الفحص بعد','Not validated yet'),L('أكمل الاستيراد ثم افحص المدخلات.','Complete the import, then validate references.')):errorState(error));}
}
