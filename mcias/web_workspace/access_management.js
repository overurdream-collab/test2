import { L, el, field, button, panel, empty, loading, errorState, openDrawer, toast, link } from './ui.js';

export function accessManagement(ctx) {
  const { root, api, context } = ctx;
  const technical = context.roles.includes('super_admin');
  root.append(panel(L('المستخدمون والصلاحيات','Users and permissions'),
    L('الصلاحيات مجمدة حتى يمنحها السوبر أدمن. الإجراءات الإدارية تتم خارج النظام، ويسجل النظام المنح والسحب.',
      'Access is frozen until explicitly granted by the super-admin. Administrative decisions happen externally; grants and revocations are logged.')));
  const content=el('div');root.append(content);let offset=0;
  if (technical) {
    const tools=el('div',null,'actions');
    tools.append(link(L('إدارة حسابات المستخدمين','Manage user accounts'),'/admin/users','button'),
      link(L('ميزات الجهة','Organization features'),'/admin/features','button'),
      link(L('الأمان والتحقق','Security and MFA'),'/admin/security','button'),
      link(L('صحة النظام','System health'),'/admin/system-health','button'));
    root.append(tools);
  }
  async function edit(user) {
    const body=el('div');body.append(loading());openDrawer(L('صلاحيات المستخدم','User permissions'),body);
    try {
      const [current,catalog]=await Promise.all([api.request(`/api/v1/admin/access/users/${user.id}`),api.request('/api/v1/admin/access/catalog')]);
      if(current.technical_account){body.replaceChildren(empty(L('حساب إدارة تقنية','Technical account'),L('الصلاحيات التشغيلية والمالية لا تُمنح تلقائيًا للحساب التقني.','Functional and financial approval grants are separate from technical administration.')));return;}
      const form=el('form'), selected=new Set(current.codes), groups=new Map();
      form.append(el('h3',user.username),el('p',L('اختر الصلاحيات بناءً على الإجراءات التي اتخذتها خارج النظام.','Select permissions based on the administrative procedures completed outside MCIAS.')));
      for(const item of catalog.items.filter(p=>p.delegable)){
        const category=item.category||'other';if(!groups.has(category)){const box=el('fieldset',null,'permission-group');box.append(el('legend',category));groups.set(category,box);form.append(box);}
        const label=el('label',null,'permission-option'),check=el('input');check.type='checkbox';check.value=item.code;check.checked=selected.has(item.code);
        check.addEventListener('change',()=>check.checked?selected.add(item.code):selected.delete(item.code));
        label.append(check,el('span',L(item.description_ar||item.code,item.description_en||item.code)),el('code',item.code));groups.get(category).append(label);
      }
      const reason=field('access-reason',L('وصف الإجراء الإداري','Administrative action note'),{maxLength:500});
      const feedback=el('div');feedback.setAttribute('aria-live','polite');
      const save=el('button',L('حفظ الصلاحيات','Save permissions'),'button primary');save.type='submit';
      const cancel=button(L('إلغاء','Cancel'),()=>document.getElementById('drawer').close());
      const controls=el('div',null,'actions');controls.append(save,cancel);form.append(reason.wrap,controls,feedback);
      form.addEventListener('submit',async event=>{event.preventDefault();if(save.disabled||!form.reportValidity())return;save.disabled=true;
        try{await api.request(`/api/v1/admin/access/users/${user.id}`,{method:'PUT',body:{codes:[...selected].sort(),expected_revision:current.revision,reason:reason.input.value.trim()}});
          document.getElementById('drawer').close();toast(L('حُفظت الصلاحيات وسُجل الإجراء','Permissions saved and action logged'));await load();
        }catch(error){feedback.replaceChildren(errorState(error));}finally{save.disabled=false;}});
      body.replaceChildren(form);
    }catch(error){body.replaceChildren(errorState(error));}
  }
  async function load(){content.replaceChildren(loading());try{
    const page=await api.request(`/api/v1/users?offset=${offset}&limit=25`),wrap=el('div',null,'table-scroll'),table=el('table'),head=el('tr');
    for(const title of [L('اسم المستخدم','Username'),L('الحالة','Status'),L('الإجراءات','Actions')])head.append(el('th',title));
    const thead=el('thead');thead.append(head);table.append(thead);const tbody=el('tbody');
    for(const user of page.items){const row=el('tr'),actions=el('td');row.append(el('td',user.username),el('td',user.status));
      if(technical)actions.append(button(L('الصلاحيات','Permissions'),()=>void edit(user)));row.append(actions);tbody.append(row);}
    table.append(tbody);wrap.append(table);const pagination=el('div',null,'actions');
    if(offset)pagination.append(button(L('السابق','Previous'),()=>{offset-=25;void load();}));
    if(page.has_more)pagination.append(button(L('التالي','Next'),()=>{offset+=25;void load();}));
    content.replaceChildren(wrap,pagination);
  }catch(error){content.replaceChildren(errorState(error,()=>void load()));}}
  void load();
}
