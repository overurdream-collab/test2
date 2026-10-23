"""A linked, explicitly synthetic contract/category/copay/provider fixture.

Uses the current encrypted registry without altering prior input or approval.
The numerical examples below are fixture data, never institutional policy.
"""
from datetime import date
from decimal import Decimal
from io import BytesIO
import os
from openpyxl import Workbook
from mcias.models import Organization
from mcias.schemas.registry import RecordCreate
from mcias.services import registry_service as registry, feature_service as features


def seed_linked_references(db, actor):
    organization=db.get(Organization,actor.organization_id)
    if (os.getenv('MCIAS_ENVIRONMENT')!='development'
            or os.getenv('MCIAS_LAPTOP_TEST_MODE')!='synthetic_localhost'
            or not organization or not organization.name.startswith('SYN-')
            or not features.is_super_admin(db,actor)):
        raise ValueError('Explicit synthetic organization and MFA super-admin required')
    created=0;start=date(date.today().year,1,1);records={}
    def add(key,section,title,values,links=None,terms=None,parent=None,clause=None,body=None):
        nonlocal created
        if not features.check_feature(db,actor.organization_id,section):
            features.grant_feature(db,actor.organization_id,section,actor.id)
        code='SYN-LINKED-'+key
        existing=registry.list_records(db,actor,section,limit=10000)['items']
        row=next((r for r in existing if r['values']['record_code']==code),None)
        if row is None:
            row=registry.create_record(db,actor,section,RecordCreate(title=title,effective_from=start,
                values={'record_code':code,**values},links=links or {},terms=terms or {},
                parent_id=parent['id'] if parent else None,clause_number=clause,
                body=body or 'SYNTHETIC linked reference example; not a financial approval.'))
            created+=1
        records[key]=row
        return row
    categories={code:add('CATEGORY-'+code,'beneficiaries.categories','SYN الفئة '+code,{'category_code':code}) for code in ('B','C')}
    for suffix,name,category in (('EMPLOYEE','SYN موظف تجريبي','B'),('SPOUSE','SYN زوجة تجريبية','B'),
                                  ('CHILD','SYN ابن تجريبي','B'),('PARENT','SYN والد تجريبي','C')):
        add('BEN-'+suffix,'beneficiaries.names',name,
            {'beneficiary_token':'SYN-INS-'+suffix,'category_code':category},links={'category':categories[category]['id']})
    services={}
    for kind,name in (('visit','SYN زيارة طبيب'),('medication','SYN دواء'),('lab','SYN فحص مخبري'),('radiology','SYN أشعة')):
        services[kind]=add('SERVICE-'+kind,'providers.services',name,
            {'service_code':'SYN-'+kind.upper(),'coding_system':'LOCAL'},terms={'service_type':kind})
    for suffix,title,section,network in (
            ('HOSPITAL','SYN مستشفى النور','providers.hospitals','in_network'),
            ('CLINIC','SYN عيادة الشفاء','providers.clinics','out_of_network')):
        provider=add(suffix,section,title,{'provider_code':'SYN-LINKED-'+suffix})
        contract=add('CONTRACT-'+suffix,'inputs.contracts','SYN عقد '+title,
            {'provider_code':provider['values']['provider_code'],'contract_number':'SYN-CONTRACT-'+suffix},
            links={'provider':provider['id']},terms={'currency':'LYD','rounding':'HALF_UP','precision':2,'network':network})
        regulation=add('REGULATION-'+suffix,'inputs.regulations','SYN لائحة '+title,{'document_number':'SYN-REG-'+suffix},
            links={'contract':contract['id']},terms={'amount_basis':'NET','unit_basis':'ONE_SERVICE_PER_ROW','require_beneficiary_name':True})
        for number,text in enumerate(('ربط المستفيد بفئته واشتراكه الساري بتاريخ الخدمة.',
                'تسعيرة مستقلة لكل مقدم وخدمة بحسب الإصدار الساري.',
                'نسبة تحمل المستفيد بحسب الفئة ونوع الخدمة والشبكة؛ يمنع خصمها مرتين.'),1):
            add('CONTRACT-'+suffix+'-CLAUSE-'+str(number),'inputs.contracts','SYN شرط '+str(number),
                {k:v for k,v in contract['values'].items() if k!='record_code'},links=contract['links'],terms=contract['terms'],
                parent=contract,clause=str(number),body='مثال اصطناعي فقط: '+text)
        for number,text in enumerate(('المطلوب قبل التحمل؛ الصافي هو المبلغ المطلوب من الجهة.',
                'نقص المرجع أو غموض المطابقة يعلّق البند للمراجعة ولا يثبت مخالفة مالية.'),1):
            add('REGULATION-'+suffix+'-CLAUSE-'+str(number),'inputs.regulations','SYN بند لائحة '+str(number),
                {k:v for k,v in regulation['values'].items() if k!='record_code'},links=regulation['links'],terms=regulation['terms'],
                parent=regulation,clause=str(number),body='مثال اصطناعي فقط: '+text)
        for kind,service in services.items():
            # Different providers intentionally have different unit prices.
            price={'visit':'1000','medication':'100','lab':'200','radiology':'400'}[kind]
            if suffix=='CLINIC':price=str(Decimal(price)*Decimal('1.2'))
            add('PRICE-'+suffix+'-'+kind,'providers.prices','SYN تسعيرة '+service['title']+' / '+title,
                {'provider_code':provider['values']['provider_code'],'service_code':service['values']['service_code'],'amount':price,'currency':'LYD'},
                links={'provider':provider['id'],'service':service['id'],'contract':contract['id']})
            for category in ('B','C'):
                rates={'B':{'visit':'10' if network=='in_network' else '30','medication':'50','lab':'30','radiology':'30'},
                       'C':{'visit':'50' if network=='in_network' else '60','medication':'60','lab':'40','radiology':'40'}}
                add('COPAY-'+suffix+'-'+category+'-'+kind,'beneficiaries.cost_sharing',
                    f'SYN تحمل {category} / {service["title"]} / {title}',
                    {'category_code':category,'percent':rates[category][kind]},
                    links={'category':categories[category]['id'],'contract':contract['id']},
                    terms={'service_type':kind,'network':network})
    return {'synthetic':True,'records_created':created,'records':records,'financially_active':False}


def sample_workbook(at=None):
    """Four correctly priced rows covering B/C, two service types and networks."""
    at=at or date.today()
    book=Workbook();sheet=book.active;sheet.title='مطالبات اصطناعية';sheet.sheet_view.rightToLeft=True
    sheet.append(['رقم الفاتورة','الرقم التأميني','اسم المستفيد','الدرجة','مقدم الخدمة','الخدمة',
        'تاريخ الخدمة','السعر','المطلوب','نسبة التحمل','إجمالي التحمل','الصافي'])
    for invoice,token,name,category,provider,service,gross,percent in (
        ('SYN-INVOICE-1','SYN-INS-EMPLOYEE','SYN موظف تجريبي','B','SYN مستشفى النور','SYN زيارة طبيب','1000','10'),
        ('SYN-INVOICE-1','SYN-INS-EMPLOYEE','SYN موظف تجريبي','B','SYN مستشفى النور','SYN فحص مخبري','200','30'),
        ('SYN-INVOICE-2','SYN-INS-PARENT','SYN والد تجريبي','C','SYN مستشفى النور','SYN زيارة طبيب','1000','50'),
        ('SYN-INVOICE-3','SYN-INS-SPOUSE','SYN زوجة تجريبية','B','SYN عيادة الشفاء','SYN زيارة طبيب','1200','30')):
        copay=Decimal(gross)*Decimal(percent)/100;net=Decimal(gross)-copay
        sheet.append([invoice,token,name,category,provider,service,at.strftime('%d/%m/%Y'),gross,gross,percent,str(copay),str(net)])
    output=BytesIO();book.save(output);return output.getvalue()
