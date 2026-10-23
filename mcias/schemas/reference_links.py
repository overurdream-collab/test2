"""Typed, tenant-validated links for the existing encrypted reference registry.

These are application-enforced record relationships, not new SQL tables or FKs.
Historical unlinked intake remains readable and is never silently approved.
"""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


PROVIDERS = tuple('providers.'+kind for kind in ('hospitals','clinics','labs','radiology','pharmacies'))
RELATIONS = {
    'inputs.contracts': {'provider': PROVIDERS},
    'inputs.regulations': {'contract': ('inputs.contracts',)},
    'beneficiaries.names': {'category': ('beneficiaries.categories',)},
    'beneficiaries.cost_sharing': {'category': ('beneficiaries.categories',), 'contract': ('inputs.contracts',)},
    'providers.prices': {'provider': PROVIDERS, 'service': ('providers.services',), 'contract': ('inputs.contracts',)},
}


class ReferenceTerms(BaseModel):
    model_config = ConfigDict(extra='forbid')
    currency: str | None = Field(default=None, pattern=r'^[A-Z]{3}$')
    rounding: Literal['HALF_UP','HALF_EVEN'] | None = None
    precision: Literal[0,2,4] | None = None
    network: Literal['in_network','out_of_network'] | None = None
    service_type: Literal['visit','procedure','medication','lab','radiology','other'] | None = None
    amount_basis: Literal['NET'] | None = None
    unit_basis: Literal['ONE_SERVICE_PER_ROW'] | None = None
    require_beneficiary_name: Literal[True] | None = None


TERM_FIELDS = {
    'inputs.contracts': ('currency','rounding','precision','network'),
    'inputs.regulations': ('amount_basis','unit_basis','require_beneficiary_name'),
    'beneficiaries.cost_sharing': ('service_type','network'),
    'providers.services': ('service_type',),
}


def validate_structure(feature, links, terms):
    """Empty legacy metadata is allowed; partially specified linked rules are not."""
    if not links and not terms:
        return
    if set(links) != set(RELATIONS.get(feature, {})):
        raise ValueError('Supply all reference links for this section')
    if set(terms) != set(TERM_FIELDS.get(feature, ())):
        raise ValueError('Supply exactly the typed reference terms for this section')


TERM_LABELS = {
    'currency': ('العملة','Currency'), 'rounding': ('سياسة التقريب','Rounding policy'),
    'precision': ('الخانات العشرية','Decimal places'), 'network': ('الشبكة','Network'),
    'service_type': ('نوع الخدمة','Service type'), 'amount_basis': ('أساس مبلغ المطالبة','Claim amount basis'),
    'unit_basis': ('وحدة الصف','Row unit basis'), 'require_beneficiary_name': ('اشتراط مطابقة الاسم','Require name matching'),
}
TERM_OPTIONS = {
    'rounding': [('HALF_UP','تقريب النصف للأعلى','Half up'),('HALF_EVEN','تقريب النصف للزوجي','Half even')],
    'precision': [('0','0','0'),('2','2','2'),('4','4','4')],
    'network': [('in_network','داخل الشبكة','In network'),('out_of_network','خارج الشبكة','Out of network')],
    'service_type': [('visit','زيارة طبيب','Doctor visit'),('procedure','إجراء','Procedure'),('medication','دواء','Medication'),
                     ('lab','فحص مخبري','Lab test'),('radiology','أشعة','Radiology'),('other','أخرى','Other')],
    'amount_basis': [('NET','صافي بعد التحمل','Net after copay')],
    'unit_basis': [('ONE_SERVICE_PER_ROW','بند خدمة واحد لكل صف','One service per row')],
    'require_beneficiary_name': [('true','نعم','Yes')],
}
