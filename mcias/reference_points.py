"""Governed temporal clause register. No automatic G5 financial policy activation."""
from datetime import date
from decimal import Decimal, InvalidOperation
import os
import re
from sqlalchemy import select, func
from mcias.models import AuditLog, WrittenAuthorization, now_utc
from mcias.models_ingestion import IngestionDocument
from mcias.models_reference_points import ReferencePoint, ReferencePointClosure

SECTIONS = frozenset({
    "contracts", "providers", "beneficiaries", "cost_sharing",
    "categories", "exclusions", "approvals", "tariffs"
})
RULE_TYPES = frozenset({"text", "amount", "percentage", "count", "exclusion", "approval", "duration"})
MAX_DATE = date(9999, 12, 31)


class PointConflict(ValueError):
    pass


def _lock(db, org, section, key):
    # Ensure concurrent initial creation and approvals serialize on PostgreSQL.
    if db.bind.dialect.name == "postgresql":
        from sqlalchemy import text
        db.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
                   {"key": org + ":point:" + section + ":" + key})


def _end(db, point):
    closed = db.get(ReferencePointClosure, point.id)
    return closed.effective_until if closed else point.effective_until


def _validate(data):
    if data["section"] not in SECTIONS or data["rule_type"] not in RULE_TYPES:
        raise PointConflict("unsupported reference section or rule type")
    if not re.fullmatch(r"[A-Za-z0-9_.:-]{1,120}", data["logical_key"]):
        raise PointConflict("logical key must be a stable code")
    if not data["title"].strip() or not data["clause_text"].strip():
        raise PointConflict("clause text and title required")
    if data["effective_from"] >= data["effective_until"]:
        raise PointConflict("invalid effective period")
    if data["section"] == "tariffs":
        if not all((data["provider_code"], data["service_code"], data["currency"])):
            raise PointConflict("tariff must specify provider, service and currency")
        if data["rule_type"] != "amount" or data["amount"] is None:
            raise PointConflict("tariff amount required")
    if data["rule_type"] in {"amount", "percentage", "count"} and data["amount"] is None:
        raise PointConflict("numeric rule requires a typed value")
    if data["amount"] is not None:
        try:
            amount = Decimal(str(data["amount"]))
        except (InvalidOperation, TypeError):
            raise PointConflict("invalid numeric value") from None
        if (not amount.is_finite() or amount < 0
            or amount.as_tuple().exponent < -4 or amount >= Decimal("100000000000000")):
            raise PointConflict("invalid numeric precision or range")
        if data["rule_type"] == "percentage" and amount > 100:
            raise PointConflict("percentage exceeds 100")
        if data["rule_type"] == "count" and amount != amount.to_integral_value():
            raise PointConflict("count must be an integer")
    if data["currency"] is not None and not re.fullmatch(r"[A-Z]{3}", data["currency"]):
        raise PointConflict("invalid currency")
    if data["section"] == "tariffs" and data["logical_key"] != data["provider_code"] + ":" + data["service_code"]:
        raise PointConflict("tariff key must be provider_code:service_code")


def _source(db, org, document_id):
    if not document_id:
        return None
    doc = db.get(IngestionDocument, document_id)
    if not doc or doc.organization_id != org or doc.status in {"quarantined", "rejected"}:
        raise PointConflict("source document not accessible or quarantined")
    return doc


def create_draft(db, actor, data):
    _validate(data)
    org = actor.organization_id
    section, key = data["section"], data["logical_key"]
    _lock(db, org, section, key)
    version = db.scalar(select(func.max(ReferencePoint.version)).where(
        ReferencePoint.organization_id == org,
        ReferencePoint.section == section, ReferencePoint.logical_key == key)) or 0
    parent = None
    if version:
        parent = db.scalar(select(ReferencePoint).where(
            ReferencePoint.organization_id == org, ReferencePoint.section == section,
            ReferencePoint.logical_key == key, ReferencePoint.version == version).with_for_update())
        if (not parent or parent.status != "approved" or db.get(ReferencePointClosure, parent.id)
            or data["supersedes_id"] != parent.id):
            raise PointConflict("existing point requires approved latest-version supersession")
        if not (parent.effective_from < data["effective_from"] < _end(db, parent)):
            raise PointConflict("replacement must start inside the active predecessor period")
        if data["effective_from"] < date.today():
            raise PointConflict("retroactive replacement requires separate impact-review workflow")
        if data["effective_until"] != _end(db, parent):
            raise PointConflict("replacement end must match predecessor end")
        if data["provider_code"] != parent.provider_code or data["service_code"] != parent.service_code:
            raise PointConflict("provider/service identity cannot change during amendment")
    elif data.get("supersedes_id"):
        raise PointConflict("cannot supersede a missing point")
    doc = _source(db, org, data.get("source_document_id"))
    point = ReferencePoint(
        organization_id=org, section=section, logical_key=key,
        version=version + 1, title=data["title"].strip(), clause_text=data["clause_text"].strip(),
        rule_type=data["rule_type"], provider_code=data["provider_code"],
        service_code=data["service_code"], amount=data["amount"], currency=data["currency"],
        effective_from=data["effective_from"], effective_until=data["effective_until"],
        status="draft", supersedes_id=parent.id if parent else None,
        source_document_id=doc.id if doc else None,
        source_sha256=doc.sha256 if doc else None,
        source_locator=data.get("source_locator") if doc else None, created_by=actor.id)
    db.add(point)
    db.flush()
    db.add(AuditLog(actor_id=actor.id, action="reference_point_draft_created",
        resource_type="reference_point", resource_id=point.id,
        details={"section":section,"logical_key":key,"version":point.version,
                 "supersedes_id":point.supersedes_id,"source_sha256":point.source_sha256}))
    db.commit()
    return point


def approve(db, actor, point_id, authorization_id, reason):
    point = db.get(ReferencePoint, point_id, with_for_update=True)
    if not point or point.organization_id != actor.organization_id:
        raise PointConflict("reference point unavailable")
    if point.status != "draft" or point.created_by == actor.id:
        raise PointConflict("only independent approval of a draft is allowed")
    if not reason or len(reason.strip()) < 20:
        raise PointConflict("substantive reason is required")
    authorization = db.get(WrittenAuthorization, authorization_id)
    if (not authorization or authorization.organization_id != point.organization_id
        or authorization.approved_by in {actor.id, point.created_by}):
        raise PointConflict("independent written institutional authorization required")
    # Generic approval records are not bound cryptographically to a specific
    # clause. Never treat them as trusted approval in production.
    if os.getenv("MCIAS_ENVIRONMENT", "development") == "production":
        raise PointConflict("production rule activation requires institution-bound signed approval")
    _lock(db, point.organization_id, point.section, point.logical_key)
    existing = db.scalars(select(ReferencePoint).where(
        ReferencePoint.organization_id == point.organization_id,
        ReferencePoint.section == point.section,
        ReferencePoint.logical_key == point.logical_key,
        ReferencePoint.status == "approved").with_for_update()).all()
    parent = None
    if point.supersedes_id:
        parent = db.get(ReferencePoint, point.supersedes_id, with_for_update=True)
        if (not parent or parent not in existing or db.get(ReferencePointClosure, parent.id)
            or parent.version + 1 != point.version):
            raise PointConflict("predecessor is invalid or already closed")
        if not (parent.effective_from < point.effective_from < parent.effective_until
                and point.effective_until == parent.effective_until):
            raise PointConflict("invalid replacement effective period")
        if point.effective_from < date.today():
            raise PointConflict("retroactive replacement requires impact approval")
    for other in existing:
        if other.id == (parent.id if parent else None):
            continue
        if other.effective_from < point.effective_until and _end(db, other) > point.effective_from:
            raise PointConflict("approved reference period overlaps existing rule")
    if parent:
        db.add(ReferencePointClosure(point_id=parent.id, organization_id=point.organization_id,
            effective_until=point.effective_from, replaced_by_id=point.id,
            reason=reason.strip(), approved_by=actor.id))
    point.status = "approved"
    point.approved_by = actor.id
    point.approved_at = now_utc()
    db.add(AuditLog(actor_id=actor.id, action="reference_point_approved",
        resource_type="reference_point", resource_id=point.id,
        details={"authorization_id":authorization.id,"reason":reason.strip(),
                 "replaced_point_id":point.supersedes_id}))
    db.commit()
    return point


def list_points(db, org, section, at=None, limit=100, offset=0):
    if section not in SECTIONS:
        raise PointConflict("unsupported reference section")
    query = select(ReferencePoint).outerjoin(
        ReferencePointClosure, ReferencePointClosure.point_id == ReferencePoint.id
    ).where(
        ReferencePoint.organization_id == org, ReferencePoint.section == section
    )
    # Filter by historical service date BEFORE pagination, not after.
    # This avoids hiding older active versions behind >100 newer versions.
    if at is not None:
        query = query.where(
            ReferencePoint.status == "approved",
            ReferencePoint.effective_from <= at,
            func.coalesce(ReferencePointClosure.effective_until, ReferencePoint.effective_until) > at
        )
    rows = db.scalars(query.order_by(
        ReferencePoint.logical_key, ReferencePoint.version.desc()
    ).limit(limit + 1).offset(offset)).all()
    return [as_dict(point, _end(db, point)) for point in rows]


def as_dict(point, effective_until=None):
    end = effective_until or point.effective_until
    return {"id":point.id, "section":point.section,"logical_key":point.logical_key,
        "version":point.version,"title":point.title,"clause_text":point.clause_text,
        "rule_type":point.rule_type,"provider_code":point.provider_code,
        "service_code":point.service_code,
        "amount":format(point.amount, ".4f") if point.amount is not None else None,
        "currency":point.currency, "effective_from":point.effective_from.isoformat(),
        "effective_until":end.isoformat(),"status":point.status,
        "source_document_id":point.source_document_id,"source_sha256":point.source_sha256,
        "source_locator":point.source_locator,"supersedes_id":point.supersedes_id,
        "created_at":point.created_at.isoformat() if point.created_at else None,
        "approved_at":point.approved_at.isoformat() if point.approved_at else None}
