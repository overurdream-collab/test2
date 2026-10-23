"""Encrypted versioned intake using existing source storage and append-only events.

Names, amounts and document content never enter audit metadata. Entries are
reference proposals; they do not activate G3/G5 rules or alter approved snapshots.
No new schema, existing-model mutation, or synthetic catalog is required.
"""
from datetime import date
from hashlib import sha256
import json
import os
from uuid import uuid4
from pathlib import PurePath
from sqlalchemy import select, text
from mcias.models import AuditLog, SourceFile
from mcias.models_ingestion import IngestionDocument, IngestionJob, ExtractedSourceRecord
from mcias.schemas.registry import RecordCreate, validate_values, SCHEMAS
from mcias.services import feature_service as f, rbac_service as rbac
from mcias.services import authorization_service as authority
from mcias.storage import EncryptedStore
from mcias.schemas.reference_links import RELATIONS, validate_structure

class RegistryForbidden(ValueError): pass
class RegistryMissing(ValueError): pass

def store():
    try:
        return EncryptedStore(os.environ["MCIAS_STORAGE_DIR"], bytes.fromhex(os.environ["MCIAS_STORAGE_KEY"]))
    except (KeyError, ValueError): raise RuntimeError("encrypted intake storage unavailable") from None

def authorize(db, actor, feature, operation="read"):
    if feature not in SCHEMAS: raise RegistryMissing("intake section not found")
    if not rbac._live_user(actor, date.today()) or not actor.organization_id:
        raise RegistryForbidden("active institutional user required")
    if not f.is_super_admin(db, actor) and not f.check_feature(db, actor.organization_id, feature):
        raise RegistryForbidden("organization feature is not enabled")
    if authority.authority_mode() == 'super_admin':
        operation = 'update' if operation == 'close' else operation
        if not authority.check_permission_unified(db,actor,f"registry.{feature}.{operation}"):
            raise RegistryForbidden("intake permission denied")
        return
    reads = f.READ_PERMISSIONS[feature]
    codes = reads if operation == "read" else tuple(c[:-5] + "." + operation for c in reads if c.endswith(".read")) + ("reference.write",)
    if not f.permitted(db, actor, *codes): raise RegistryForbidden("intake permission denied")

def _lock(db, key):
    if db.get_bind().dialect.name == "postgresql":
        db.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"), {"key": key})

def _events(db, actor, feature):
    return list(db.scalars(select(AuditLog).where(AuditLog.organization_id == actor.organization_id,
        AuditLog.resource_type == "reference_intake", AuditLog.details["feature_code"].as_string() == feature)
        .order_by(AuditLog.created_at, AuditLog.id).limit(10001)))

def _latest(db, actor, feature):
    events = _events(db, actor, feature)
    if len(events) > 10000: raise ValueError("intake event limit exceeded; paged storage adapter required")
    latest = {}
    for event in events:
        if event.resource_id not in latest or event.details["version"] > latest[event.resource_id].details["version"]:
            latest[event.resource_id] = event
    return latest

def effective_records(db, actor, feature, at):
    """Resolve retained versions at service date, independently of admin closure.

    A future replacement does not disable today's reference. Once a later
    version starts, an expired later version must not resurrect its predecessor.
    """
    events=_events(db,actor,feature)
    if len(events)>10000:raise ValueError('intake event limit exceeded; paged storage adapter required')
    histories={}
    for event in events:histories.setdefault(event.resource_id,[]).append(event)
    result=[]
    for history in histories.values():
        candidates=[]
        for event in history:
            if event.details['status']!='open':continue
            record=_decode(db,actor,feature,event)
            if date.fromisoformat(record['effective_from'])>at:continue
            for closure in history:
                if (closure.details['status']=='closed' and closure.details['version']==record['version']+1
                        and closure.details.get('effective_to')):
                    record['effective_to']=closure.details['effective_to']
            candidates.append(record)
        if not candidates:continue
        chosen=max(candidates,key=lambda r:r['version'])
        if chosen['effective_to'] and date.fromisoformat(chosen['effective_to'])<=at:continue
        result.append(chosen)
    return result

def _reference_metadata(db, actor, feature, data, previous_id=None):
    links={key:str(value) for key,value in data.links.items()}
    terms=data.terms.model_dump(exclude_none=True)
    validate_structure(feature,links,terms)
    targets={}
    for role,record_id in links.items():
        found=[]
        for target_feature in RELATIONS[feature][role]:
            event=_latest(db,actor,target_feature).get(record_id)
            if event is not None and event.details['status']=='open':
                found.append(_decode(db,actor,target_feature,event))
        if len(found)!=1:raise ValueError('Linked reference must exist, be open and belong to this organization')
        targets[role]=found[0]
    for role,field in (('provider','provider_code'),('category','category_code'),('service','service_code')):
        if role in targets and data.values[field].strip()!=targets[role]['values'][field]:
            raise ValueError('Linked reference code does not match '+field)
    if feature=='providers.prices' and links:
        contract=targets['contract']
        if contract.get('links',{}).get('provider')!=links['provider']:
            raise ValueError('Price, provider and contract must be linked to the same provider')
        if contract.get('terms',{}).get('currency')!=data.values['currency'].strip():
            raise ValueError('Price currency must match the linked contract')
    if feature=='beneficiaries.cost_sharing' and links:
        if targets['contract'].get('terms',{}).get('network')!=terms['network']:
            raise ValueError('Copay network must match the linked contract')
    if links and feature in ('providers.prices','beneficiaries.cost_sharing','beneficiaries.names'):
        for event in _latest(db,actor,feature).values():
            if event.resource_id==previous_id or event.details['status']!='open':continue
            prior=_decode(db,actor,feature,event)
            same=(prior.get('links')==links and prior.get('terms',{})==terms)
            if feature=='beneficiaries.names':same=prior['values']['beneficiary_token']==data.values['beneficiary_token'].strip()
            end=data.effective_to or date.max;other_end=date.fromisoformat(prior['effective_to']) if prior['effective_to'] else date.max
            if same and data.effective_from<other_end and date.fromisoformat(prior['effective_from'])<end:
                raise ValueError('Overlapping linked reference; replace the existing record atomically')
    return links,terms

def relationship_options(db, actor, feature):
    options={}
    for role,sections in RELATIONS.get(feature,{}).items():
        options[role]=[]
        for section in sections:
            try:authorize(db,actor,section)
            except RegistryForbidden:continue
            for event in _latest(db,actor,section).values():
                if event.details['status']!='open':continue
                row=_decode(db,actor,section,event)
                options[role].append({'id':row['id'],'title':row['title'],'feature':section,'values':row['values']})
    return options

def _decode(db, actor, feature, event):
    source = db.get(SourceFile, event.details["source_id"])
    if source is None: raise ValueError("intake source missing")
    payload = json.loads(store().get(source.storage_key, source.sha256))
    if payload["organization_id"] != actor.organization_id or payload["feature_code"] != feature:
        raise RegistryForbidden("intake source scope mismatch")
    return {**payload, "id": event.resource_id, "version": event.details["version"],
        "status": event.details["status"], "effective_to": event.details.get("effective_to", payload.get("effective_to")),
        "source_sha256": source.sha256, "source_id": source.id, "approval_status": "pending_institutional_review",
        "financially_active": False, "created_at": event.created_at,
        "created_by":event.actor_id,
        "close_reason": payload.get("close_reason"), "event_id": event.id,
        "closed_at":event.details.get('closed_at'),
        "previous_event_id":payload.get('previous_event_id')}

def read_record(db, actor, feature, record_id):
    authorize(db, actor, feature)
    event = _latest(db, actor, feature).get(record_id)
    if event is None: raise RegistryMissing("record not found")
    return _decode(db, actor, feature, event)

def list_records(db, actor, feature, query="", status=None, offset=0, limit=25, provider_code=None):
    authorize(db, actor, feature)
    results = []
    for event in sorted(_latest(db, actor, feature).values(), key=lambda e: (e.created_at, e.id), reverse=True):
        if status and event.details["status"] != status: continue
        record = _decode(db, actor, feature, event)
        if provider_code and record['values'].get('provider_code')!=provider_code:continue
        if query and query.casefold() not in (record["title"] + " " + " ".join(record["values"].values())).casefold(): continue
        results.append(record)
    return {"items": results[offset:offset+limit], "offset":offset, "limit":limit,
        "has_more":len(results)>offset+limit, "total":len(results)}

def provider_options(db,actor,feature):
    if feature!='providers.prices':raise RegistryMissing('Provider selection is for price lists')
    authorize(db,actor,feature)
    codes={_decode(db,actor,feature,e)['values']['provider_code'] for e in _latest(db,actor,feature).values()}
    names={code:code for code in codes}
    for kind in ('hospitals','clinics','labs','radiology','pharmacies'):
        section='providers.'+kind
        try:authorize(db,actor,section)
        except RegistryForbidden:continue
        for event in _latest(db,actor,section).values():
            record=_decode(db,actor,section,event);code=record['values']['provider_code']
            if record['status']=='open':names[code]=record['title']
    return [{'code':code,'name':name} for code,name in sorted(names.items())]

def _event(db, actor, feature, record_id, version, source_id, status, **extra):
    row = AuditLog(actor_id=actor.id, organization_id=actor.organization_id, category="reference_intake",
        action="intake." + status, resource_type="reference_intake", resource_id=record_id,
        details={"feature_code":feature,"version":version,"source_id":source_id,"status":status,**extra})
    db.add(row);db.flush();return row

def _evidence(db, actor, document_id):
    if not document_id: return None
    doc = db.get(IngestionDocument, str(document_id))
    if doc is None or doc.organization_id != actor.organization_id or doc.status != "extracted":
        raise ValueError("evidence must be an extracted document from the same organization")
    return {"document_id":doc.id,"sha256":doc.sha256,"format":PurePath(doc.filename).suffix.lower().lstrip('.')}

def create_record(db, actor, feature, data: RecordCreate, previous_id=None, expected_version=None, source_record_id=None):
    authorize(db, actor, feature, "create")
    if previous_id and authority.authority_mode()=='super_admin':
        authorize(db,actor,feature,'update')
    values = validate_values(feature, data.values)
    key = sha256(values["record_code"].encode()).hexdigest()
    with rbac._atomic(db):
        _lock(db, actor.organization_id + ":intake:" + feature)
        links,terms=_reference_metadata(db,actor,feature,data,previous_id)
        latest = _latest(db, actor, feature)
        if previous_id:
            old = latest.get(previous_id)
            if old is None: raise RegistryMissing("previous record not found")
            if old.details["status"] != "closed" or old.details["version"] != expected_version:
                raise ValueError("only the current closed version can be replaced")
            prior = _decode(db, actor, feature, old)
            if (prior.get('links') or prior.get('terms')) and not (links or terms):
                raise ValueError('A new linked version must preserve typed relationships and terms')
            if prior["values"]["record_code"] != values["record_code"]:
                raise ValueError("new version must preserve record code")
            if data.effective_from < date.fromisoformat(prior["effective_to"]):
                raise ValueError("new version cannot precede prior closure")
            record_id, version = previous_id, old.details["version"] + 1
        else:
            if any(e.details.get("code_digest") == key for e in latest.values()):
                raise ValueError("record code exists; create a new version of its closed record")
            record_id, version = str(uuid4()), 1
        evidence = _evidence(db, actor, data.evidence_document_id)
        if data.parent_id:
            parent = latest.get(str(data.parent_id))
            if feature not in ('inputs.contracts','inputs.regulations','inputs.exceptions','inputs.caps','inputs.coverage','inputs.approvals') or parent is None or parent.details['status']!='open':
                raise ValueError('An open parent in the same section is required')
            if any(e.resource_id!=previous_id and _decode(db,actor,feature,e).get('parent_id')==str(data.parent_id) and _decode(db,actor,feature,e).get('clause_number')==data.clause_number for e in latest.values()):
                raise ValueError('Clause number already exists under this parent')
        payload = {"organization_id":actor.organization_id,"feature_code":feature,"title":data.title.strip(),
            "effective_from":data.effective_from.isoformat(),"effective_to":data.effective_to.isoformat() if data.effective_to else None,
            "values":values,"evidence":evidence,"source_record_id":source_record_id,
            "parent_id":str(data.parent_id) if data.parent_id else None,"clause_number":data.clause_number,"body":data.body,
            "links":links,"terms":terms}
        object_id, digest = store().put(json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(",", ":")).encode())
        source = SourceFile(sha256=digest,original_filename="reference-intake.json",storage_key=object_id)
        db.add(source);db.flush()
        event = _event(db, actor, feature, record_id, version, source.id, "open", code_digest=key)
        return _decode(db, actor, feature, event)

def close_record(db, actor, feature, record_id, expected_version, reason):
    authorize(db, actor, feature, "close")
    with rbac._atomic(db):
        _lock(db, actor.organization_id + ":intake:" + feature)
        latest = _latest(db, actor, feature).get(record_id)
        if latest is None: raise RegistryMissing("record not found")
        record = _decode(db, actor, feature, latest)
        if record["status"] != "open" or record["version"] != expected_version:
            raise ValueError("record already closed or editor is stale")
        if date.fromisoformat(record["effective_from"]) > date.today(): raise ValueError("cannot close a future record")
        if not reason.strip(): raise ValueError("closing reason required")
        # Reason stays encrypted as well; audit stores only the fact of closure.
        payload = {k:v for k,v in record.items() if k in ("organization_id","feature_code","title","effective_from","effective_to","values","evidence","source_record_id","parent_id","clause_number","body","previous_event_id","links","terms")}
        payload["close_reason"] = reason.strip()
        object_id,digest=store().put(json.dumps(payload,ensure_ascii=False,sort_keys=True).encode())
        source=SourceFile(sha256=digest,original_filename="reference-intake-closure.json",storage_key=object_id);db.add(source);db.flush()
        event=_event(db,actor,feature,record_id,record["version"]+1,source.id,"closed",effective_to=date.today().isoformat(),code_digest=latest.details["code_digest"])
        result=_decode(db,actor,feature,event);result["close_reason"]=reason.strip();return result

def record_history(db, actor, feature, record_id):
    read_record(db,actor,feature,record_id)
    return [_decode(db,actor,feature,e) for e in _events(db,actor,feature) if e.resource_id==record_id]

def replace_record(db, actor, feature, record_id, data):
    """Atomic administrative closure + immutable replacement; validity is preserved.

    Closing an editor version never overwrites its effective dates or source.
    Future replacements can therefore coexist with the reference valid today.
    """
    from datetime import datetime, timezone
    authorize(db,actor,feature,'update')
    values=validate_values(feature,data.values)
    with rbac._atomic(db):
        _lock(db,actor.organization_id+':intake:'+feature)
        links,terms=_reference_metadata(db,actor,feature,data,record_id)
        latest=_latest(db,actor,feature).get(record_id)
        if latest is None:raise RegistryMissing('record not found')
        old=_decode(db,actor,feature,latest)
        if (old.get('links') or old.get('terms')) and not (links or terms):
            raise ValueError('Linked references cannot be silently detached; preserve their typed metadata')
        if old['status']!='open' or old['version']!=data.expected_version:
            raise ValueError('Record changed; reload before editing')
        if values['record_code']!=old['values']['record_code']:
            raise ValueError('Replacement must preserve record code')
        if (str(data.parent_id) if data.parent_id else None)!=old.get('parent_id') or data.clause_number!=old.get('clause_number'):
            raise ValueError('Replacement must preserve clause identity')
        if data.effective_from.isoformat()<old['effective_from']:
            raise ValueError('Retroactive date changes need a separately approved impact review')
        evidence=_evidence(db,actor,data.evidence_document_id) if data.evidence_document_id else old.get('evidence')
        closed_at=datetime.now(timezone.utc).isoformat()
        _event(db,actor,feature,record_id,old['version'],old['source_id'],'closed',
            code_digest=latest.details['code_digest'],closed_at=closed_at)
        payload={'organization_id':actor.organization_id,'feature_code':feature,'title':data.title.strip(),
            'effective_from':data.effective_from.isoformat(),'effective_to':data.effective_to.isoformat() if data.effective_to else None,
            'values':values,'evidence':evidence,'source_record_id':old.get('source_record_id'),
            'parent_id':old.get('parent_id'),'clause_number':old.get('clause_number'),'body':data.body,
            'previous_event_id':latest.id,'close_reason':data.reason,'links':links,'terms':terms}
        object_id,digest=store().put(json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode())
        source=SourceFile(sha256=digest,original_filename='reference-intake-version.json',storage_key=object_id)
        db.add(source);db.flush()
        event=_event(db,actor,feature,record_id,old['version']+1,source.id,'open',
            code_digest=latest.details['code_digest'],previous_event_id=latest.id)
        return _decode(db,actor,feature,event)

def preview_import(db, actor, feature, document_id):
    authorize(db,actor,feature,"create")
    doc=_evidence(db,actor,document_id)
    job=db.scalar(select(IngestionJob).where(IngestionJob.document_id==document_id,IngestionJob.organization_id==actor.organization_id)
        .order_by(IngestionJob.created_at.desc(),IngestionJob.id.desc()).limit(1))
    if not job or job.status!="extracted" or not job.manifest.get("complete"):
        raise ValueError("quarantined or incomplete extraction cannot be imported")
    rows=list(db.scalars(select(ExtractedSourceRecord).where(ExtractedSourceRecord.job_id==job.id).order_by(ExtractedSourceRecord.id).limit(101)))
    if len(rows)>100: raise ValueError("select an import file of at most 100 records")
    preview=[]
    for row in rows:
        if set(row.values)=={"text"}:
            # PDF is evidence; structured fields must be supplied by a human.
            preview.append({"id":row.id,"locator":row.locator,"manual_required":True,"valid":False,
                "text_excerpt":row.values["text"][:3000]});continue
        try:
            values={key:row.values.get(key,"") for key in SCHEMAS[feature]}
            data=RecordCreate(title=row.values.get("title",""),effective_from=row.values.get("effective_from",""),
                effective_to=row.values.get("effective_to") or None,values=values,evidence_document_id=document_id)
            data.values=validate_values(feature,data.values)
            preview.append({"id":row.id,"locator":row.locator,"valid":True,"record":data.model_dump(mode="json")})
        except ValueError:
            preview.append({"id":row.id,"locator":row.locator,"valid":False,"error":"required fields, dates or values do not match the schema"})
    return {"document_id":document_id,"source_sha256":doc["sha256"],"items":preview,"job_id":job.id}

def commit_import(db,actor,feature,document_id,record_ids,manual_record=None):
    authorize(db,actor,feature,"create")
    preview=preview_import(db,actor,feature,document_id)
    chosen=[str(i) for i in record_ids]
    if len(chosen)!=len(set(chosen)): raise ValueError("duplicate selected source record")
    if bool(chosen)==bool(manual_record): raise ValueError("select rows or supply one manual PDF record")
    with rbac._atomic(db):
        _lock(db,actor.organization_id+":intake:"+feature)
        if manual_record:
            if not any(r.get("manual_required") for r in preview["items"]): raise ValueError("manual mapping is for PDF evidence only")
            manual_record.evidence_document_id=document_id
            return [create_record(db,actor,feature,manual_record)]
        by_id={r["id"]:r for r in preview["items"]}
        results=[]
        for record_id in chosen:
            item=by_id.get(record_id)
            if not item or not item["valid"]: raise ValueError("invalid or foreign import row")
            # Persist source-row identity for idempotency, never silently duplicate.
            if any(_decode(db,actor,feature,e).get("source_record_id")==record_id for e in _latest(db,actor,feature).values()):
                raise ValueError("source row already imported")
            results.append(create_record(db,actor,feature,RecordCreate(**item["record"]),source_record_id=record_id))
        return results
