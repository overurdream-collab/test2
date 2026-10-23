"""Bounded reference-intake contracts, not an automatic financial policy."""
from datetime import date
from decimal import Decimal, InvalidOperation
from uuid import UUID
from pydantic import Field, model_validator
from mcias.schemas.common import Input, Reason
from mcias.schemas.reference_links import ReferenceTerms

# key -> Arabic label, English label, browser input type
FIELDS = {
    "record_code": ("رمز السجل", "Record code", "text"),
    "provider_code": ("رمز مقدم الخدمة", "Provider code", "text"),
    "contract_number": ("رقم العقد", "Contract number", "text"),
    "insurer_code": ("رمز شركة التأمين", "Insurance company code", "text"),
    "beneficiary_token": ("معرّف المستفيد", "Beneficiary token", "text"),
    "category_code": ("رمز الفئة", "Category code", "text"),
    "service_code": ("رمز الخدمة", "Service code", "text"),
    "coding_system": ("نظام الترميز", "Coding system", "text"),
    "currency": ("العملة", "Currency", "text"),
    "amount": ("المبلغ المرجعي", "Reference amount", "text"),
    "percent": ("النسبة المرجعية", "Reference percentage", "text"),
    "scope": ("النطاق", "Scope", "text"),
    "document_number": ("رقم المستند", "Document number", "text"),
}
SCHEMAS = {
    "inputs.contracts": ("record_code", "provider_code", "contract_number"),
    "inputs.insurers": ("record_code", "insurer_code", "contract_number"),
    "inputs.regulations": ("record_code", "document_number"),
    "inputs.exceptions": ("record_code", "scope"),
    "inputs.approvals": ("record_code", "document_number"),
    "inputs.caps": ("record_code", "amount", "currency", "scope"),
    "inputs.coverage": ("record_code", "scope"),
    "beneficiaries.names": ("record_code", "beneficiary_token", "category_code"),
    "beneficiaries.categories": ("record_code", "category_code"),
    "beneficiaries.cost_sharing": ("record_code", "category_code", "percent"),
    **{f"providers.{kind}": ("record_code", "provider_code") for kind in ("hospitals", "clinics", "labs", "radiology", "pharmacies")},
    "providers.services": ("record_code", "service_code", "coding_system"),
    "providers.prices": ("record_code", "provider_code", "service_code", "amount", "currency"),
}
FIELD_LIMITS = {"record_code":80,"provider_code":80,"contract_number":120,"beneficiary_token":128,
    "insurer_code":80,
    "category_code":80,"service_code":100,"currency":3,"document_number":120}

class RecordCreate(Input):
    title: str = Field(min_length=1, max_length=200)
    effective_from: date
    effective_to: date | None = None
    values: dict[str, str] = Field(max_length=12)
    evidence_document_id: UUID | None = None
    parent_id: UUID | None = None
    clause_number: str | None = Field(default=None, pattern=r"^[1-9][0-9]*(\.[1-9][0-9]*)*$", max_length=60)
    body: str = Field(default="", max_length=20000)
    links: dict[str, UUID] = Field(default_factory=dict, max_length=3)
    terms: ReferenceTerms = Field(default_factory=ReferenceTerms)

    @model_validator(mode="after")
    def dates(self):
        if not self.title.strip(): raise ValueError("title required")
        if bool(self.parent_id) != bool(self.clause_number):
            raise ValueError("parent_id and clause_number must be supplied together")
        if self.effective_to is not None and self.effective_to <= self.effective_from:
            raise ValueError("effective_to must be after effective_from")
        return self

class RecordVersion(RecordCreate):
    expected_version: int = Field(ge=1)

class RecordReplace(RecordVersion):
    reason: Reason

class RecordClose(Input):
    reason: Reason
    expected_version: int = Field(ge=1)

class ImportCommit(Input):
    record_ids: list[UUID] = Field(default_factory=list, max_length=100)
    manual_record: RecordCreate | None = None

def validate_values(feature, values):
    if feature not in SCHEMAS: raise ValueError("unsupported intake feature")
    expected = set(SCHEMAS[feature])
    if set(values) != expected: raise ValueError("fields must match the intake schema")
    result = {}
    for key, raw in values.items():
        if not isinstance(raw, str) or not raw.strip() or len(raw) > FIELD_LIMITS.get(key,200) or any(ord(c) < 32 for c in raw):
            raise ValueError("invalid field: " + key)
        value = raw.strip()
        if key in ("amount", "percent"):
            try: number = Decimal(value)
            except InvalidOperation: raise ValueError("invalid numeric field: " + key) from None
            if not number.is_finite() or number < 0 or number >= Decimal("100000000000000") or number.as_tuple().exponent < -4:
                raise ValueError("invalid numeric precision or range")
            if key == "percent" and number > 100: raise ValueError("percentage exceeds 100")
            value = format(number, "f")
        if key == "currency" and (len(value) != 3 or not value.isascii() or not value.isalpha() or not value.isupper()):
            raise ValueError("currency must be three uppercase ASCII letters")
        if key == "coding_system" and value not in ("LOCAL", "ICD", "CPT", "LOINC", "SNOMED"):
            raise ValueError("unsupported coding system")
        result[key] = value
    return result
