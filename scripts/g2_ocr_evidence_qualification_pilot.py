#!/usr/bin/env python3
"""Synthetic G2 OCR candidates: isolated DB table, never trusted A1 authority."""
from __future__ import annotations
import argparse, hashlib, json, os, tempfile
from pathlib import Path
from sqlalchemy import create_engine, select, ForeignKey, String, Integer, JSON, UniqueConstraint
from sqlalchemy.orm import Session, Mapped, mapped_column
from mcias.models import Base, Organization, User, SourceFile, uid
from mcias.models_ingestion import IngestionDocument, IngestionJob, ExtractedSourceRecord
from mcias.ingestion.orchestrator import ingest
from mcias.storage import EncryptedStore
from document_reader_dynamic_layout_pilot import (
    STYLES, make_fixture, read_pixels_and_words, parse_dynamic, score,
    a1_payload, load_a1
)
from g2_trust_pilot import reopen

class Candidate(Base):
    """Isolated synthetic-only table; not G2 ExtractedSourceRecord or trusted A1 input."""
    __tablename__="reader_ocr_candidate_isolated"
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    organization_id: Mapped[str]=mapped_column(ForeignKey("organizations.id"),nullable=False)
    document_id: Mapped[str]=mapped_column(ForeignKey("ingestion_documents.id"),nullable=False)
    job_id: Mapped[str]=mapped_column(ForeignKey("ingestion_jobs.id"),nullable=False)
    source_sha256: Mapped[str]=mapped_column(String(64),nullable=False)
    page: Mapped[int]=mapped_column(Integer,nullable=False)
    row_id: Mapped[str]=mapped_column(String(100),nullable=False)
    field_name: Mapped[str]=mapped_column(String(100),nullable=False)
    observed_value: Mapped[str]=mapped_column(String(300),nullable=False)
    bbox: Mapped[list]=mapped_column(JSON,nullable=False)
    ocr_words: Mapped[list]=mapped_column(JSON,nullable=False)
    ocr_confidence: Mapped[int]=mapped_column(Integer,nullable=False)
    status: Mapped[str]=mapped_column(String(45),nullable=False,default="UNVERIFIED_OCR_CANDIDATE")
    __table_args__=(UniqueConstraint("organization_id","document_id","row_id","field_name"),)

FIELDS=("id","code","unit","qty","price","total")
def words_text(words):
    return " ".join(w["text"] for w in words)

def all_candidates(db,org,doc):
    return db.scalars(select(Candidate).where(Candidate.organization_id==org,
                Candidate.document_id==doc).order_by(Candidate.row_id,Candidate.field_name)).all()

def create_candidates(db,doc,job,parsed):
    count=0
    for row in parsed["rows"]:
        if row.get("id") is None:continue
        rid=row["id"]["value"]
        for k in FIELDS:
            f=row.get(k)
            if f is None:continue
            db.add(Candidate(organization_id=doc.organization_id,document_id=doc.id,
                  job_id=job.id,source_sha256=doc.sha256,page=f["page"],row_id=rid,
                  field_name=k,observed_value=f["value"],bbox=f["bbox_pixels"],
                  ocr_words=f["ocr_word_evidence"],
                  ocr_confidence=int(f["ocr_confidence_uncalibrated"]*100)))
            count+=1
    db.flush()
    return count
