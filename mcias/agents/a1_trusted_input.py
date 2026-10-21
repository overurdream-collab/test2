"""A1 P0: read-only G4/G2 trusted CSV/XLSX input, original byte evidence and G3 diagnostic.

No client-supplied tenant, document attestation, synthetic flags or unit prices
can create financial authority. PDF/XLSX and ambiguous sources fail closed.
"""
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from typing import Literal
import re
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import select

from mcias.models import SourceFile
from mcias.models_ingestion import IngestionDocument, IngestionJob, ExtractedSourceRecord, QuarantineItem
from mcias.models_claims import ClaimEntry, ClaimBatch, ClaimAttachment
from mcias.models_reference import ContractVersion, ProviderTariff
from mcias.ingestion.parsers import csv_parser
from mcias.policy import has_permission
from mcias.claim_normalization import FIELDS as G4_ORIGINAL_FIELDS, normalize
from mcias.agents.invoice_integrity import digest, RULESET_VERSION

SCHEMA_VERSION="mcias.a1.input.v1"
REQUIRED_LINE=("line_item_id","service_code","unit","quantity","unit_price",
               "line_total","invoice_total","claim_reference","provider_code","currency")
REQUIRED_FIELDS=("claims.read","ingestion.read")
REQUIRED_SENSITIVE=tuple("medical_fields."+f+".read" for f in dict.fromkeys((*REQUIRED_LINE,*G4_ORIGINAL_FIELDS)))

class A1AccessDenied(ValueError):
    pass

class A1SourceBlocked(ValueError):
    pass

def _decimal(value):
    if type(value) not in (str, int, Decimal):
        raise ValueError("number cannot be float, bool or inferred")
    try:
        n=Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError("invalid decimal") from None
    if not n.is_finite() or n<0 or n>=Decimal("100000000000000") or n.as_tuple().exponent < -4:
        raise ValueError("invalid amount, infinity, NaN or precision")
    return format(n,"f")

class Strict(BaseModel):
    model_config=ConfigDict(extra="forbid", strict=True)

class Ref(Strict):
    document_id: str=Field(min_length=1,max_length=128)
    sha256: str=Field(pattern=r"^[0-9a-f]{64}$")
    locator: str=Field(min_length=1,max_length=256)

class Line(Strict):
    id: str=Field(min_length=1,max_length=128)
    kind: Literal["service","fee"]
    code: str=Field(min_length=1,max_length=100)
    unit: str=Field(min_length=1,max_length=80)
    quantity: str
    unit_price: str
    line_total: str
    source: Ref
    @field_validator("quantity","unit_price","line_total")
    @classmethod
    def valid_number(cls,value):
        return _decimal(value)
    @model_validator(mode="after")
    def positive_quantity(self):
        if Decimal(self.quantity)==0:
            raise ValueError("zero invoice quantity")
        return self

class Claim(Strict):
    id: str
    tenant_id: str
    provider_code: str
    service_date: date
    currency: str=Field(pattern=r"^[A-Z]{3}$")
    amount: str
    source: Ref
    @field_validator("amount")
    @classmethod
    def valid_amount(cls,value):
        return _decimal(value)

class Invoice(Strict):
    id: str
    tenant_id: str
    currency: str=Field(pattern=r"^[A-Z]{3}$")
    stated_total: str | None=None
    items: list[Line]=Field(default_factory=list,max_length=1000)
    source: Ref | None=None
    @field_validator("stated_total")
    @classmethod
    def valid_total(cls,value):
        return _decimal(value) if value is not None else None
    @model_validator(mode="after")
    def unique_ids(self):
        ids=[line.id for line in self.items]
        if len(ids)!=len(set(ids)):
            raise ValueError("duplicate invoice item id")
        return self

class SourceVerification(Strict):
    document_id: str
    sha256: str=Field(pattern=r"^[0-9a-f]{64}$")
    original_sha256_verified: Literal[True]
    extracted_rows_equal_original: Literal[True]

class A1Input(Strict):
    schema_version: Literal["mcias.a1.input.v1"]=SCHEMA_VERSION
    tenant_id: str
    run_id: str
    timestamp: datetime
    claim: Claim
    invoice: Invoice
    contracts: list[dict]=Field(default_factory=list)
    documents: list[dict]=Field(default_factory=list)
    source_verifications: list[SourceVerification]=Field(default_factory=list)
    missing_evidence: list[str]=Field(default_factory=list)
    synthetic: bool=False
    @model_validator(mode="after")
    def check_tenant_and_currency(self):
        if self.claim.tenant_id!=self.tenant_id or self.invoice.tenant_id!=self.tenant_id:
            raise ValueError("cross-tenant input")
        if self.claim.currency!=self.invoice.currency:
            raise ValueError("cross-currency input")
        if not self.timestamp.tzinfo or self.timestamp.utcoffset() is None:
            raise ValueError("timestamp must be timezone-aware")
        return self
    def analysis_bundle(self):
        obj=self.model_dump(mode="json")
        return {k:obj[k] for k in ("tenant_id","run_id","claim","invoice","contracts","documents","synthetic")}

def _verify_csv_source(db,store,organization_id,document_id,expected_sha=None):
    doc=db.get(IngestionDocument,document_id)
    if doc is None or doc.organization_id!=organization_id or doc.status!="extracted":
        raise A1SourceBlocked("unavailable_untrusted_tenant_source")
    source=db.get(SourceFile,doc.source_id)
    if source is None or source.sha256!=doc.sha256 or expected_sha not in (None,doc.sha256):
        raise A1SourceBlocked("source_hash_chain_mismatch")
    jobs=db.scalars(select(IngestionJob).where(
        IngestionJob.document_id==doc.id, IngestionJob.organization_id==organization_id)).all()
    if len(jobs)!=1 or jobs[0].status!="extracted" or jobs[0].manifest.get("complete") is not True:
        raise A1SourceBlocked("missing_or_ambiguous_extraction")
    job=jobs[0]
    if db.scalar(select(QuarantineItem.id).where(QuarantineItem.job_id==job.id)):
        raise A1SourceBlocked("quarantined_source")
    try:
        data=store.get(source.storage_key,source.sha256)
    except (OSError,KeyError,ValueError) as exc:
        raise A1SourceBlocked("original_bytes_not_verified") from exc
    if type(data) is not bytes or sha256(data).hexdigest()!=doc.sha256:
        raise A1SourceBlocked("original_bytes_sha256_mismatch")
    from mcias.ingestion.file_scanner import identify, UnsafeDocument
    try:
        kind=identify(data,doc.filename)
        if kind=="csv":
            extraction=csv_parser.parse(data)
        elif kind=="xlsx":
            from mcias.ingestion.isolated_parser import isolated_parse
            extraction=isolated_parse(kind,data)
        else:
            raise A1SourceBlocked("format_not_itemizable")
    except (UnsafeDocument,UnicodeDecodeError,ValueError,OSError,RuntimeError) as exc:
        raise A1SourceBlocked("original_reparse_invalid_or_unsafe") from exc
    if not extraction.complete or extraction.quarantined or not (0<len(extraction.records)<=1000):
        raise A1SourceBlocked("incomplete_original_rows")
    persisted=db.scalars(select(ExtractedSourceRecord).where(
        ExtractedSourceRecord.job_id==job.id)).all()
    if len(persisted)!=len(extraction.records):
        raise A1SourceBlocked("extracted_record_count_changed")
    def coord(locator):
        if isinstance(locator,dict):
            return tuple(locator.get(k) for k in ("kind","index","row","column"))
        return (locator.kind,locator.index,locator.row,locator.column)
    originals={coord(r.locator):r.values for r in extraction.records}
    if len(originals)!=len(extraction.records):
        raise A1SourceBlocked("ambiguous_original_coordinates")
    seen=set()
    for row in persisted:
        point=coord(row.locator)
        if point in seen or point not in originals or originals[point]!=row.values or row.confidence!=100:
            raise A1SourceBlocked("stored_extraction_not_equal_original")
        seen.add(point)
    return {"document":doc,"records":persisted,"job":job}

def _ref(doc,locator):
    if not isinstance(locator,dict) or not isinstance(locator.get("row"),int) or locator["row"]<1:
        raise A1SourceBlocked("invalid_tabular_row_location")
    if locator.get("kind")=="row":
        loc="csv:row:"+str(locator["row"])
    elif locator.get("kind")=="sheet" and isinstance(locator.get("index"),int) and locator["index"]>0:
        loc="xlsx:sheet:"+str(locator["index"])+":row:"+str(locator["row"])
    else:
        raise A1SourceBlocked("unsupported_tabular_locator")
    return {"document_id":doc.id,"sha256":doc.sha256,"locator":loc}

def _claim_lineage(db,actor,claim,batch,checked,record):
    """Recheck additive native G4 lineage instead of discarding its metadata.

    Legacy byte-verified rows retain their exact-coordinate contract. Native
    approved-scope rows must also be in the existing server-verified CLAIMS set.
    """
    try:
        from mcias.claim_batches import source_scope
    except ImportError as exc:
        if claim.source_locator==record.locator:
            return None
        raise A1SourceBlocked("native_claim_source_scope_unverified") from exc
    try:
        scope=source_scope(db,actor,checked["document"].id)
    except ValueError as exc:
        raise A1SourceBlocked("native_claim_source_scope_unverified") from exc
    if (scope.get("job_id")!=checked["job"].id
        or scope.get("source_sha256")!=batch.source_sha256
        or record.id not in scope.get("eligible_record_ids",[])
        or record.id in scope.get("excluded_record_ids",[])):
        raise A1SourceBlocked("native_claim_source_scope_mismatch")
    if not scope.get("approval_id"):
        if claim.source_locator==record.locator and not scope.get("mapping_version"):
            return None
        raise A1SourceBlocked("native_claim_source_scope_mismatch")
    expected=dict(record.locator)
    expected.update(document_id=checked["document"].id,job_id=checked["job"].id,
        source_sha256=checked["document"].sha256,
        source_scope_approval_id=scope.get("approval_id"),
        mapping_version=scope.get("mapping_version"),sheet_type="CLAIMS")
    if (not scope.get("approval_id") or not scope.get("mapping_version")
        or claim.source_locator!=expected):
        raise A1SourceBlocked("native_claim_source_scope_mismatch")
    return {"approval_id":scope["approval_id"],"mapping_version":scope["mapping_version"],
            "sheet_type":"CLAIMS"}

def _row_evidence(checked,row,fields):
    ref=_ref(checked["document"],row.locator)
    return {"source_file_id":checked["document"].source_id,"source_record_id":row.id,
            "source":ref,"field_sources":{
                name:{**ref,"source_file_id":checked["document"].source_id,"source_record_id":row.id,
                      "locator":ref["locator"]+":field:"+name}
                for name in fields if name in row.values}}

def _g3_historical_reference(db,claim):
    contracts=db.scalars(select(ContractVersion).where(
        ContractVersion.organization_id==claim.organization_id,
        ContractVersion.provider_code==claim.provider_code,
        ContractVersion.status=="approved",
        ContractVersion.effective_from<=claim.service_date,
        ContractVersion.effective_until>claim.service_date)).all()
    if len(contracts)!=1:
        return {"status":"HELD" if contracts else "MISSING","reason":"overlap_or_no_approved_contract"}
    c=contracts[0]
    tariffs=db.scalars(select(ProviderTariff).where(
        ProviderTariff.contract_id==c.id,ProviderTariff.service_code==claim.service_code)).all()
    if len(tariffs)!=1 or tariffs[0].currency!=claim.currency:
        return {"status":"HELD","reason":"tariff_ambiguous_or_wrong_currency",
                "contract_version_id":c.id}
    t=tariffs[0]
    return {"status":"REFERENCE_ONLY_UNIT_UNPROVEN","contract_version_id":c.id,
            "contract_version":c.version,"tariff_id":t.id,"provider_code":claim.provider_code,
            "service_code":claim.service_code,"currency":claim.currency,
            "reference_amount":str(t.amount),"effective_from":c.effective_from.isoformat(),
            "effective_until":c.effective_until.isoformat(),"policy_fingerprint":None,
            "reason":"G3_has_no_approved_unit_mapping_or_verified_G5_policy"}

def build_a1_snapshot(db,actor,claim_id,store,*,run_id):
    """Server-derived tenant and permissions; return typed input and nonauthoritative G3."""
    org=getattr(actor,"organization_id",None)
    if not org or not getattr(actor,"active",False) or not all(
        has_permission(db,actor,p) for p in (*REQUIRED_FIELDS,*REQUIRED_SENSITIVE)):
        raise A1AccessDenied("organization and individual field permissions required")
    claim=db.scalar(select(ClaimEntry).where(
        ClaimEntry.id==claim_id,ClaimEntry.organization_id==org))
    if claim is None:
        raise A1AccessDenied("claim not accessible")
    batch=db.scalar(select(ClaimBatch).where(
        ClaimBatch.id==claim.batch_id,ClaimBatch.organization_id==org))
    if batch is None:
        raise A1SourceBlocked("claim_batch_missing")
    source=_verify_csv_source(db,store,org,batch.ingestion_document_id,batch.source_sha256)
    record=[r for r in source["records"] if r.id==claim.extracted_record_id]
    if len(record)!=1 or record[0].values!=claim.source_values:
        raise A1SourceBlocked("claim_not_equal_original_record")
    native_scope=_claim_lineage(db,actor,claim,batch,source,record[0])
    try:
        original=normalize(record[0].values)
    except ValueError as exc:
        raise A1SourceBlocked("original_claim_normalization_invalid") from exc
    for field in G4_ORIGINAL_FIELDS:
        if getattr(claim,field)!=original[field]:
            raise A1SourceBlocked("normalized_G4_claim_field_changed")
    claim_ptr=_ref(source["document"],record[0].locator)
    attachments=db.scalars(select(ClaimAttachment).where(
        ClaimAttachment.organization_id==org,ClaimAttachment.claim_id==claim.id)).all()
    candidates=[];missing=[]
    for link in attachments:
        try:
            checked=_verify_csv_source(db,store,org,link.ingestion_document_id,link.document_sha256)
            if not all(isinstance(r.values,dict) and all(k in r.values for k in REQUIRED_LINE)
                       for r in checked["records"]):
                missing.append("attachment_missing_itemized_fields")
                continue
            if any(r.values["claim_reference"]!=claim.claim_reference
                   or r.values["provider_code"]!=claim.provider_code
                   or r.values["currency"]!=claim.currency for r in checked["records"]):
                missing.append("attachment_claim_identity_mismatch")
                continue
            candidates.append(checked)
        except A1SourceBlocked as exc:
            missing.append(str(exc))
    if len(candidates)!=1:
        missing.append("no_unique_verified_itemized_invoice")
    items=[];total=None;invoice_source=None;invoice_id="missing-invoice"
    if len(candidates)==1:
        checked=candidates[0]
        invoice_id=checked["document"].id
        try:
            for row in checked["records"]:
                v=row.values
                # Optional source-declared kind; legacy invoice rows remain service.
                # Fee classification is NEVER inferred from code or price.
                kind=v.get("item_kind","service")
                if kind not in ("service","fee"):
                    raise ValueError("invalid item_kind")
                items.append(Line.model_validate({"id":v["line_item_id"],"kind":kind,
                              "code":v["service_code"],"unit":v["unit"],
                              "quantity":v["quantity"],"unit_price":v["unit_price"],
                              "line_total":v["line_total"],
                              "source":_ref(checked["document"],row.locator)}).model_dump(mode="json"))
            totals={r.values["invoice_total"] for r in checked["records"]}
            if len(totals)!=1:
                raise ValueError("inconsistent stated totals")
            total=_decimal(next(iter(totals)))
            invoice_source=_ref(checked["document"],checked["records"][0].locator)
        except (ValueError,KeyError):
            items=[];total=None;invoice_source=None
            missing.append("invalid_invoice_row")
    try:
        snapshot=A1Input.model_validate({
            "schema_version":SCHEMA_VERSION,"tenant_id":org,"run_id":run_id,
            "timestamp":datetime.now(timezone.utc),"synthetic":False,
            "claim":{"id":claim.id,"tenant_id":org,"provider_code":claim.provider_code,
                     "service_date":claim.service_date,"currency":claim.currency,
                     "amount":str(claim.claimed_amount),"source":claim_ptr},
            "invoice":{"id":invoice_id,"tenant_id":org,"currency":claim.currency,
                       "stated_total":total,"items":items,"source":invoice_source},
            "source_verifications":[{"document_id":x["document"].id,
                "sha256":x["document"].sha256,
                "original_sha256_verified":True,"extracted_rows_equal_original":True}
                for x in [source]+(candidates if len(candidates)==1 else [])],
            "missing_evidence":["approved_unit_mapping","verified_signed_G5_policy",
                                "attested_performed_service_quantity",
                                *(["approved_contract_fee_clause"] if any(item["kind"]=="fee" for item in items) else []),
                                *sorted(set(missing))],
            "contracts":[],"documents":[]
        })
    except ValueError as exc:
        raise A1SourceBlocked("invalid_unverified_invoice_fields") from exc
    g3_reference=_g3_historical_reference(db,claim)
    if any(line.kind=="fee" for line in snapshot.invoice.items):
        # G3 ProviderTariff has no fee-kind, contractual fee-clause or unit
        # authorization. Even a valid historical service tariff is NOT a fee grant.
        g3_reference["additional_fee_authority"]="NOT_ESTABLISHED"
        g3_reference["additional_fee_reason"]="G3_provider_tariff_is_not_approved_fee_clause"
    # This projection carries original field evidence, not financial authority.
    # In particular a source row does not establish gross/net, discount, tax or
    # rounding semantics. G5 must independently verify its rule and those facts.
    claim_evidence=_row_evidence(source,record[0],G4_ORIGINAL_FIELDS)
    claim_evidence.update(provider_code=claim.provider_code,service_code=claim.service_code,
        service_date=claim.service_date.isoformat(),currency=claim.currency,source_scope=native_scope)
    invoice_lines=[]
    if len(candidates)==1:
        checked=candidates[0]
        for row in checked["records"]:
            v=row.values
            invoice_lines.append({"line_item_id":v["line_item_id"],"kind":v.get("item_kind","service"),
                "code":v["service_code"],"unit":v["unit"],"currency":v["currency"],
                "quantity":v["quantity"],"unit_price":v["unit_price"],"line_total":v["line_total"],
                **_row_evidence(checked,row,REQUIRED_LINE)})
    source_evidence={"claim":claim_evidence,
        "invoice":{"document_id":invoice_id,"stated_total":total,"source":invoice_source},
        "invoice_lines":invoice_lines,
        "arithmetic_qualification":{"source_qualified":bool(snapshot.invoice.items),
            "qualified":False,"ruleset_version":RULESET_VERSION,
            "gaps":["explicit_adjustment_context","approved_arithmetic_rule",
                    *(["valid_itemized_invoice"] if not snapshot.invoice.items else [])]},
        "unit_price_authority":"NOT_ESTABLISHED"}
    return {"snapshot":snapshot,"g3_reference":g3_reference,"source_evidence":source_evidence,
            "source_evidence_fingerprint":digest(source_evidence),
            "status":"READ_ONLY_VERIFIED_CSV_NO_UNIT_AUTHORITY"}

def preview_a1_from_g4(db,actor,claim_id,store,*,run_id):
    data=build_a1_snapshot(db,actor,claim_id,store,run_id=run_id)
    # Real on-prem medical data is never sent to an AI inference backend here.
    from mcias.agents.invoice_integrity import analyze
    result=analyze(data["snapshot"].analysis_bundle())
    from mcias.agents.a1_review_packet import packet_from_preview
    preview={"a1":result,"missing_evidence":data["snapshot"].missing_evidence,
            "g3_historical_diagnostic":data["g3_reference"],
            "status":data["status"],"financial_decision":"NOT_AUTHORIZED",
            "source_evidence":data["source_evidence"],
            "source_evidence_fingerprint":data["source_evidence_fingerprint"],
            "source_verifications":[v.model_dump() for v in data["snapshot"].source_verifications]}
    preview["review_packet"]=packet_from_preview(preview)
    return preview
