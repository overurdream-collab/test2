#!/usr/bin/env python3
"""Isolated PG16 contract verification against pinned PR29 writer and PR20 A1.

The contract event rows belong to a disposable test fixture; no Alembic/production
schema, no substitute audit service, no real claims, no medical/financial action.
"""
from __future__ import annotations
import argparse, hashlib, importlib.util, json, os, sys, tempfile, threading, uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit
from pydantic import BaseModel as Schema, ConfigDict, Field, ValidationError
from sqlalchemy import create_engine, select, inspect, text, String, Integer, JSON, ForeignKey, UniqueConstraint
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, Mapped, mapped_column
from mcias.models import Base, Organization, User, SessionToken, SourceFile, AuditLog, Role, Permission, RolePermission, UserRole, uid
from mcias.policy import has_permission
from mcias.models_ingestion import IngestionDocument, IngestionJob
from mcias.storage import EncryptedStore
from g2_trust_pilot import reopen
from g2_ocr_evidence_qualification_pilot import Candidate, create_candidates, all_candidates
from document_reader_dynamic_layout_pilot import (
    STYLES, make_fixture, read_pixels_and_words, parse_dynamic, a1_payload, load_a1)
from reader_reviewed_ocr_contract import ReviewedOCREvidence, CellLocator, VersionRecord

class ReviewVersion(Base):
    """Business review version, NOT an audit writer or production table."""
    __tablename__="reader_review_version_test_only"
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    organization_id: Mapped[str]=mapped_column(ForeignKey("organizations.id"),nullable=False)
    document_id: Mapped[str]=mapped_column(ForeignKey("ingestion_documents.id"),nullable=False)
    candidate_id: Mapped[str]=mapped_column(ForeignKey("reader_ocr_candidate_isolated.id"),nullable=False)
    reviewer_id: Mapped[str]=mapped_column(ForeignKey("users.id"),nullable=False)
    original_sha256: Mapped[str]=mapped_column(String(64),nullable=False)
    operation_id: Mapped[str]=mapped_column(String(96),nullable=False)
    request_digest: Mapped[str]=mapped_column(String(64),nullable=False)
    version: Mapped[int]=mapped_column(Integer,nullable=False)
    prior_state: Mapped[str]=mapped_column(String(48),nullable=False)
    state: Mapped[str]=mapped_column(String(48),nullable=False)
    corrected: Mapped[str|None]=mapped_column(String(300))
    reason_code: Mapped[str]=mapped_column(String(64),nullable=False)
    audit_event_id: Mapped[str]=mapped_column(ForeignKey("audit_log.id"),nullable=False)
    __table_args__=(UniqueConstraint("candidate_id","version"),
                    UniqueConstraint("candidate_id","operation_id"))

class Decision(Schema):
    model_config=ConfigDict(extra="forbid",strict=True)
    candidate_id: str
    expected_version: int=Field(ge=0)
    operation_id: str=Field(min_length=8,max_length=96)
    action: str
    corrected_value: str|None=None
    reason_code: str="none"

ACTIONS={"accept":"TRANSCRIPTION_ACCEPTED","correct":"TRANSCRIPTION_CORRECTED",
         "reject":"REJECTED","pending":"PENDING_HUMAN_REVIEW","unresolved":"UNRESOLVED"}
class ContractRejected(Exception):
    pass

def digest(obj):
    return hashlib.sha256(json.dumps(obj,sort_keys=True,ensure_ascii=False,separators=(",",":")).encode()).hexdigest()

def pinned_writer(source):
    # Read-only imports from exact pinned PR29 directory. Its original code is executed.
    location=Path(source)
    for name,file in (("mcias.audit_contract","mcias/audit_contract.py"),
                      ("mcias.audit_writer","mcias/audit_writer.py")):
        spec=importlib.util.spec_from_file_location(name,location/file)
        module=importlib.util.module_from_spec(spec)
        sys.modules[name]=module
        spec.loader.exec_module(module)
    return sys.modules["mcias.audit_writer"]

def session_actor(db,token):
    hashed=hashlib.sha256(token.encode()).hexdigest()
    now=datetime.now(timezone.utc)
    active=db.scalar(select(SessionToken).where(SessionToken.token_hash==hashed,
        SessionToken.revoked_at.is_(None)))
    if active is None or active.expires_at.replace(tzinfo=timezone.utc)<now:
        raise ContractRejected("SESSION_NOT_AUTHORIZED")
    actor=db.get(User,active.user_id)
    if actor is None or not actor.active or not actor.organization_id:
        raise ContractRejected("REVIEWER_NOT_ACTIVE_IN_TENANT")
    if not has_permission(db,actor,"ingestion.review"):
        raise ContractRejected("REVIEWER_ROLE_PERMISSION_MISSING")
    return actor

def versions(db,cid):
    return db.scalars(select(ReviewVersion).where(ReviewVersion.candidate_id==cid)
        .order_by(ReviewVersion.version)).all()

def source_candidate(db,store,actor,cid,expected_sha):
    c=db.scalar(select(Candidate).where(Candidate.id==cid,Candidate.organization_id==actor.organization_id))
    if not c:raise ContractRejected("CROSS_TENANT_OR_MISSING_CANDIDATE")
    try:
        data,doc,src=reopen(db,store,c.document_id,actor.organization_id,expected_sha)
    except Exception as exc:raise ContractRejected("ORIGINAL_G2_SOURCE_INVALID") from exc
    if (c.source_sha256!=doc.sha256 or c.status!="UNVERIFIED_OCR_CANDIDATE"
        or c.page!=1 or len(c.bbox)!=4 or not c.ocr_words
        or c.observed_value!=" ".join(w["text"] for w in c.ocr_words)):
        raise ContractRejected("UNVERIFIED_CANDIDATE_CHANGED")
    a,b,x,y=c.bbox
    if not(0<=a<x<=1650 and 0<=b<y<=1900):
        raise ContractRejected("OCR_SOURCE_REGION_INVALID")
    return c,doc

def submit(engine,store,writer,token,req,source_hash,*,reject_audit=True):
    if isinstance(req,dict):req=Decision.model_validate(req)
    if req.action not in ACTIONS:raise ContractRejected("INVALID_TRANSCRIPTION_ACTION")
    event_digest=digest(req.model_dump())
    with Session(engine) as db:
        actor=session_actor(db,token)
        actor_id,own_org=actor.id,actor.organization_id
        try:
            # Lock the G2 document row for transaction-scoped review serialization.
            c0=db.scalar(select(Candidate).where(Candidate.id==req.candidate_id,
                Candidate.organization_id==own_org))
            if c0 is None:raise ContractRejected("CROSS_TENANT_OR_MISSING_CANDIDATE")
            doc=db.scalar(select(IngestionDocument).where(
                IngestionDocument.id==c0.document_id,
                IngestionDocument.organization_id==own_org).with_for_update())
            if doc is None:raise ContractRejected("SOURCE_TENANT_MISMATCH")
            c,doc=source_candidate(db,store,actor,req.candidate_id,source_hash)
            existing=versions(db,c.id)
            for event in existing:
                if event.operation_id==req.operation_id:
                    if event.request_digest==event_digest and event.reviewer_id==actor_id:
                        return {"version":event.version,"audit_event_id":event.audit_event_id,"replay":True}
                    raise ContractRejected("OPERATION_REUSE_CONFLICT")
            if req.expected_version!=len(existing):raise ContractRejected("STALE_REVIEW_VERSION")
            if req.action=="correct":
                if (not req.corrected_value or req.corrected_value==c.observed_value
                    or len(req.reason_code)<4):
                    raise ContractRejected("CORRECTION_NEEDS_VALUE_AND_REASON")
            elif req.corrected_value is not None:
                raise ContractRejected("UNAUTHORIZED_FIELD_VALUE")
            previous=existing[-1].state if existing else "UNVERIFIED_OCR_CANDIDATE"
            current=ACTIONS[req.action]
            audit=writer.write_event(db,actor=actor,organization_id=own_org,
                action="ocr_transcription_"+req.action,resource_type="ocr_candidate",
                resource_id=c.id,outcome="success",
                details={"version":len(existing)+1,"status":"pending",
                         "patient_name":"SYNTHETIC_NEVER_LOG",
                         "amount":"999999","source_sha256":source_hash})
            ev=ReviewVersion(organization_id=own_org,document_id=c.document_id,
                candidate_id=c.id,reviewer_id=actor_id,original_sha256=c.source_sha256,
                operation_id=req.operation_id,request_digest=event_digest,
                version=len(existing)+1,prior_state=previous,state=current,
                corrected=req.corrected_value,reason_code=req.reason_code,
                audit_event_id=audit.id)
            db.add(ev);db.commit()
            return {"version":ev.version,"audit_event_id":audit.id,"replay":False}
        except ContractRejected as err:
            db.rollback()
            if reject_audit and err.args and err.args[0] not in ("OPERATION_REUSE_CONFLICT","STALE_REVIEW_VERSION"):
                writer.record_outcome_independent(engine,actor_id=actor_id,
                    organization_id=own_org,action="ocr_transcription_denied",
                    resource_type="ocr_candidate",resource_id=None,outcome="denied",
                    details={"reason_code":"permission_denied"})
            raise
