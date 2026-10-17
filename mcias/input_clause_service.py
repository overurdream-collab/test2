"""Governed temporal input points; no clause is a live financial policy by itself.

Existing G3 contract/tariff approval remains the executable source for G5.
This register is a separately approved, immutable explanation/source catalog
until a later, independently tested G3 binding is explicitly activated.
"""
from datetime import date
from decimal import Decimal, InvalidOperation
import json
import re
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from mcias.models import AuditLog, User, WrittenAuthorization
from mcias.models_ingestion import IngestionDocument
from mcias.models_input_clauses import InputClause, InputClauseEvent, SECTIONS
from mcias.policy import has_permission

class InputClauseError(ValueError):
    pass

def _actor(db, actor):
    if not actor or not actor.active or not actor.organization_id:
        raise InputClauseError("active institutional actor required")

def _validate(section, logical_key, provider_code, insurer_code, clause_text,
              structured_value, effective_from, effective_until):
    if section not in SECTIONS:
        raise InputClauseError("unknown input section")
    if not re.fullmatch(r"[A-Za-z0-9_.:-]{1,100}", logical_key or ""):
        raise InputClauseError("invalid logical rule key")
    for identifier in (provider_code, insurer_code):
        if len(identifier) > 80 or not re.fullmatch(r"[A-Za-z0-9_.:-]*", identifier):
            raise InputClauseError("invalid provider/insurer code")
    if section == "tariffs" and not provider_code:
        raise InputClauseError("tariff requires provider-specific scope")
    if not clause_text or not 3 <= len(clause_text.strip()) <= 2000:
        raise InputClauseError("contract clause text required")
    if effective_until is not None and effective_until <= effective_from:
        raise InputClauseError("end must follow start")
    if type(structured_value) is not dict or len(json.dumps(structured_value, ensure_ascii=False)) > 3000:
        raise InputClauseError("bounded structured value required")
    if section == "tariffs":
        if set(structured_value) != {"service_code", "amount", "currency"}:
            raise InputClauseError("tariff needs service_code, amount and currency")
        if not re.fullmatch(r"[A-Za-z0-9_.:-]{1,100}", str(structured_value["service_code"])):
            raise InputClauseError("invalid service code")
        if not re.fullmatch(r"[A-Z]{3}", str(structured_value["currency"])):
            raise InputClauseError("invalid currency")
        try:
            amount = Decimal(str(structured_value["amount"]))
        except (InvalidOperation, ValueError):
            raise InputClauseError("invalid monetary amount")
        if not amount.is_finite() or amount < 0 or amount.as_tuple().exponent < -4:
            raise InputClauseError("invalid monetary precision")
        if logical_key != str(structured_value["service_code"]):
            raise InputClauseError("tariff logical key must match service code")

def _events(db, ids):
    if not ids:
        return {}
    all_events = db.scalars(select(InputClauseEvent).where(InputClauseEvent.clause_id.in_(ids))).all()
    result = {item: {} for item in ids}
    for event in all_events:
        result[event.clause_id][event.kind] = event
    return result

def _scope_query(org, section, key, provider, insurer):
    return select(InputClause).where(
        InputClause.organization_id == org, InputClause.section == section,
        InputClause.logical_key == key, InputClause.provider_code == provider,
        InputClause.insurer_code == insurer)

def _advisory_lock(db, scope):
    if db.bind.dialect.name == "postgresql":
        from sqlalchemy import text
        db.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:scope, 0))"), {"scope": scope})

def _scope_lock(db, clause):
    _advisory_lock(db, ":".join((clause.organization_id, clause.section,
                                clause.logical_key, clause.provider_code, clause.insurer_code)))

def _end(point, actions):
    close = actions.get("close")
    return close.effective_on if close is not None else point.effective_until

def _activated(actions):
    return "activate" in actions

def public_point(point, actions, at=None):
    at = at or date.today()
    end = _end(point, actions)
    if not _activated(actions):
        status = "draft"
    elif end and at >= end:
        status = "closed"
    elif at < point.effective_from:
        status = "scheduled"
    else:
        status = "active"
    return {
        "id": point.id, "section": point.section, "logical_key": point.logical_key,
        "provider_code": point.provider_code, "insurer_code": point.insurer_code,
        "version": point.version, "clause_text": point.clause_text,
        "structured_value": point.structured_value, "effective_from": point.effective_from,
        "effective_until": end, "source_document_id": point.source_document_id,
        "source_locator": point.source_locator, "replaces_id": point.replaces_id,
        "status": status, "created_at": point.created_at,
    }

def create_draft(db, actor, *, section, logical_key, provider_code="", insurer_code="",
                 clause_text, structured_value, effective_from, effective_until=None,
                 source_document_id=None, source_locator=None, replaces_id=None):
    _actor(db, actor)
    provider_code, insurer_code = provider_code or "", insurer_code or ""
    _validate(section, logical_key, provider_code, insurer_code, clause_text,
              structured_value, effective_from, effective_until)
    locator = source_locator or {}
    if type(locator) is not dict or len(json.dumps(locator)) > 500:
        raise InputClauseError("invalid source locator")
    if source_document_id is not None:
        source = db.get(IngestionDocument, source_document_id)
        if source is None or source.organization_id != actor.organization_id or source.status == "quarantined":
            raise InputClauseError("same-organization valid source document required")
    scope = (actor.organization_id, section, logical_key, provider_code, insurer_code)
    _advisory_lock(db, ":".join(scope))
    old = None
    if replaces_id:
        old = db.get(InputClause, replaces_id)
        if old is None or (old.organization_id, old.section, old.logical_key,
                           old.provider_code, old.insurer_code) != scope:
            raise InputClauseError("replacement must use same section and scope")
        if effective_from <= old.effective_from:
            raise InputClauseError("replacement must start after prior version")
        if effective_from < date.today():
            raise InputClauseError("retroactive changes require separate signed impact process")
    current = db.scalar(select(func.max(InputClause.version)).where(
        InputClause.organization_id == scope[0], InputClause.section == section,
        InputClause.logical_key == logical_key, InputClause.provider_code == provider_code,
        InputClause.insurer_code == insurer_code)) or 0
    item = InputClause(organization_id=actor.organization_id, section=section,
        logical_key=logical_key, provider_code=provider_code, insurer_code=insurer_code,
        version=current + 1, clause_text=clause_text.strip(), structured_value=structured_value,
        effective_from=effective_from, effective_until=effective_until,
        source_document_id=source_document_id, source_locator=locator,
        replaces_id=old.id if old else None, created_by=actor.id)
    db.add(item); db.flush()
    db.add(AuditLog(actor_id=actor.id, action="input_clause_draft_created",
        resource_type="input_clause", resource_id=item.id,
        details={"section": section, "version": item.version,
                 "replaces_id": replaces_id, "source_document_id": source_document_id}))
    db.commit()
    return item

def list_points(db, actor, section, *, limit=50, offset=0, at=None, provider_code=None):
    _actor(db, actor)
    if section not in SECTIONS:
        raise InputClauseError("unknown section")
    stmt = select(InputClause).where(InputClause.organization_id == actor.organization_id,
                                     InputClause.section == section)
    if provider_code is not None:
        stmt = stmt.where(InputClause.provider_code == provider_code)
    rows = db.scalars(stmt.order_by(InputClause.logical_key, InputClause.version.desc())
                      .limit(limit).offset(offset)).all()
    actions = _events(db, [r.id for r in rows])
    return [public_point(r, actions.get(r.id, {}), at) for r in rows]

def authorize_draft(db, actor, point_id, authorization_id):
    """The author, written approver and activating reviewer are distinct."""
    _actor(db, actor)
    point = db.get(InputClause, point_id)
    if point is None or point.organization_id != actor.organization_id:
        raise InputClauseError("input clause not accessible")
    _scope_lock(db, point)
    db.refresh(point)
    if actor.id == point.created_by:
        raise InputClauseError("the clause author may not activate their own version")
    written = db.get(WrittenAuthorization, authorization_id)
    approver = db.get(User, written.approved_by) if written else None
    if (written is None or written.organization_id != point.organization_id
        or not written.source_id or approver is None or not approver.active
        or approver.organization_id != point.organization_id
        or written.approved_by in (point.created_by, actor.id)):
        raise InputClauseError("independent institutional written authorization required")
    # Production use requires the institution's existing verified trust/approval chain.
    # This point registry is explicitly NOT a live G3/G5 financial policy.
    if __import__("os").getenv("MCIAS_ENVIRONMENT") == "production":
        raise InputClauseError("new input-point activation is not institutionally accepted for production")
    rows = db.scalars(_scope_query(point.organization_id, point.section, point.logical_key,
                                   point.provider_code, point.insurer_code)).all()
    actions = _events(db, [r.id for r in rows])
    if _activated(actions.get(point.id, {})):
        raise InputClauseError("already activated")
    others = [r for r in rows if r.id != point.id and _activated(actions.get(r.id, {}))]
    previous = next((r for r in others if r.id == point.replaces_id), None)
    if point.replaces_id and previous is None:
        raise InputClauseError("replacement source must be activated")
    if previous and ("close" in actions[previous.id] or point.effective_from <= previous.effective_from
                     or (previous.effective_until and point.effective_from > previous.effective_until)):
        raise InputClauseError("invalid closing boundary")
    for row in others:
        closing = actions[row.id].get("close")
        row_end = closing.effective_on if closing else row.effective_until
        if row.id == point.replaces_id:
            row_end = point.effective_from
        if row.effective_from < (point.effective_until or date.max) and point.effective_from < (row_end or date.max):
            raise InputClauseError("overlapping active rule periods")
    if previous:
        db.add(InputClauseEvent(organization_id=point.organization_id, clause_id=previous.id,
            kind="close", effective_on=point.effective_from, authorization_id=authorization_id,
            actor_id=actor.id))
    db.add(InputClauseEvent(organization_id=point.organization_id, clause_id=point.id,
        kind="activate", effective_on=point.effective_from, authorization_id=authorization_id,
        actor_id=actor.id))
    db.add(AuditLog(actor_id=actor.id, action="input_clause_version_activated",
        resource_type="input_clause", resource_id=point.id,
        details={"replaces_id": point.replaces_id, "authorization_id": written.id,
                 "effective_from": point.effective_from.isoformat()}))
    db.commit()
    return public_point(point, _events(db, [point.id])[point.id])

def at_date(db, actor, *, section, logical_key, provider_code="", insurer_code="", on):
    """Read-only temporal resolver; never silently fall back to newer pricing."""
    _actor(db, actor)
    rows = db.scalars(_scope_query(actor.organization_id, section, logical_key,
                                    provider_code, insurer_code)).all()
    actions = _events(db, [r.id for r in rows])
    matches = [r for r in rows if _activated(actions.get(r.id, {})) and r.effective_from <= on
               and on < (_end(r, actions[r.id]) or date.max)]
    if len(matches) > 1:
        raise InputClauseError("ambiguous approved temporal clauses")
    return public_point(matches[0], actions[matches[0].id], on) if matches else None
