#!/usr/bin/env python3
"""G2 encrypted-source original replay for synthetic scanned invoices only."""
from __future__ import annotations
import argparse, hashlib, json, os, tempfile
from pathlib import Path
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from mcias.models import Base, Organization, User, SourceFile
from mcias.models_ingestion import IngestionDocument, IngestionJob, QuarantineItem, ExtractedSourceRecord
from mcias.ingestion.orchestrator import ingest
from mcias.storage import EncryptedStore
from document_reader_dynamic_layout_pilot import (
    STYLES, make_fixture, read_pixels_and_words, parse_dynamic, score,
    a1_payload, load_a1
)

def reopen(db,store,doc_id,tenant,sha):
    doc=db.scalar(select(IngestionDocument).where(
        IngestionDocument.id==doc_id,IngestionDocument.organization_id==tenant))
    if doc is None:raise ValueError("unauthorized source")
    source=db.get(SourceFile,doc.source_id)
    if source is None or source.sha256!=doc.sha256 or sha!=doc.sha256:
        raise ValueError("metadata mismatch")
    data=store.get(source.storage_key,doc.sha256)
    if hashlib.sha256(data).hexdigest()!=doc.sha256:
        raise ValueError("plaintext mismatch")
    return data,doc,source

def must_reject(call):
    try:call()
    except ValueError:return
    raise AssertionError("invalid source accepted")

def run(outdir,a1_file):
    out=Path(outdir);out.mkdir(parents=True,exist_ok=True)
    os.environ["MCIAS_ENVIRONMENT"]="development"
    os.environ["MCIAS_MALWARE_SCAN"]="disabled"
    os.environ["MCIAS_LOCAL_OCR"]="disabled"
    agent=load_a1(a1_file)
    engine=create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    reports=[];negative=0
    with tempfile.TemporaryDirectory() as folder:
        store=EncryptedStore(str(Path(folder)/"objects"),os.urandom(32))
        with Session(engine) as db:
            org=Organization(name="synthetic")
            other=Organization(name="synthetic other")
            actor=User(username="synthetic-reader",password_hash="fixture")
            db.add_all([org,other,actor]);db.flush()
            actor.organization_id=org.id;db.commit()

            for case,style in STYLES.items():
                gold=make_fixture(case,out)
                original=Path(gold["pdf_path"]).read_bytes()
                saved=ingest(db,store,org.id,actor.id,case+".pdf",original)
                assert saved["status"]=="review_required",saved
                pdf,doc,src=reopen(db,store,saved["document_id"],org.id,gold["pdf_sha256"])
                assert pdf==original
                job=db.get(IngestionJob,saved["job_id"])
                quarantine=db.scalars(select(QuarantineItem).where(
                    QuarantineItem.job_id==job.id)).all()
                assert len(quarantine)==1
                assert db.scalars(select(ExtractedSourceRecord).where(
                    ExtractedSourceRecord.job_id==job.id)).all()==[]
                disk=(store.root/src.storage_key).read_bytes()
                assert disk.startswith(b"MCIAS1") and disk!=pdf
                must_reject(lambda:reopen(db,store,doc.id,other.id,gold["pdf_sha256"]))
                must_reject(lambda:reopen(db,store,doc.id,org.id,"0"*64))
                negative+=2
