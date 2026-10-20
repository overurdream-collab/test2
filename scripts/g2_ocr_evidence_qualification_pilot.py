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

def examine(db,store,org_id,doc_id,sha,gold,tmpdir):
    """Reopen G2 original for every check. This is synthetic qualification only."""
    pdf,doc,source=reopen(db,store,doc_id,org_id,sha)
    assert hashlib.sha256(pdf).hexdigest()==doc.sha256
    rows=all_candidates(db,org_id,doc.id)
    findings=[]
    if len(rows)!=len(gold["rows"])*len(FIELDS):
        findings.append("MISSING_OR_EXTRA_CANDIDATE")
    # Re-extract evidence from pixels of independently reopened encrypted source.
    transient=Path(tmpdir)/"verification-source.pdf"
    transient.write_bytes(pdf)
    tokens,elapsed=read_pixels_and_words(transient,sha,STYLES[gold["case"]]["lang"])
    parsed=parse_dynamic(tokens,doc.id,sha,STYLES[gold["case"]]["lang"])
    measured=score(gold,parsed)
    original_rows={x["id"]["value"]:x for x in parsed["rows"] if x.get("id")}
    ground_rows={x["id"]:x for x in gold["rows"]}
    original_boxes={x["id"]:box for x,box in zip(gold["rows"],gold["cell_boxes"])}
    seen=set()
    for candidate in rows:
        key=(candidate.row_id,candidate.field_name)
        if key in seen:findings.append("DUPLICATE_CANDIDATE")
        seen.add(key)
        if candidate.status!="UNVERIFIED_OCR_CANDIDATE":
            findings.append("CANDIDATE_STATUS_ESCALATION")
        if candidate.job_id!=source_job_id(db,org_id,doc_id):
            findings.append("JOB_REFERENCE_MISMATCH")
        if candidate.source_sha256!=doc.sha256 or candidate.page!=1:
            findings.append("SOURCE_SHA_OR_PAGE_MISMATCH")
        original=original_rows.get(candidate.row_id,{}).get(candidate.field_name)
        declared=ground_rows.get(candidate.row_id,{}).get(candidate.field_name)
        if original is None or candidate.observed_value!=declared or candidate.observed_value!=original["value"]:
            findings.append("ROW_VALUE_NOT_IN_SOURCE")
            continue
        if candidate.observed_value!=words_text(candidate.ocr_words):
            findings.append("CANDIDATE_NOT_EQUAL_TO_OCR_WORDS")
        if candidate.bbox!=original["bbox_pixels"] or candidate.ocr_words!=original["ocr_word_evidence"]:
            findings.append("LOCATOR_OR_WORD_EVIDENCE_CHANGED")
        authored=original_boxes[candidate.row_id][candidate.field_name]
        x0,y0,x1,y1=authored
        a,v,c,d=candidate.bbox
        if not (x0-12<=a<=c<=x1+15 and y0-20<=v<=d<=y1+18):
            findings.append("WRONG_ORIGINAL_CELL_REGION")
    if measured["exact_values"]!=18 or measured["correct_cell_locations"]!=18:
        findings.append("INDEPENDENT_SYNTHETIC_GOLD_MISMATCH")
    if parsed["issues"]:findings.extend(parsed["issues"])
    return {"issues":sorted(set(findings)),"candidate_count":len(rows),
            "score":{"fields":measured["exact_values"],"locations":measured["correct_cell_locations"]},
            "safe_for_advisory_preview":not findings,
            "trust":"SYNTHETIC_EVIDENCE_CHECK_ONLY_NOT_A1_SOURCE_VERIFICATION",
            "a1_trusted_source_authorized":False,"ocr_seconds":elapsed}

def source_job_id(db,organization_id,document_id):
    jobs=db.scalars(select(IngestionJob).where(
        IngestionJob.document_id==document_id,
        IngestionJob.organization_id==organization_id)).all()
    if len(jobs)!=1:raise ValueError("ambiguous source job")
    return jobs[0].id

def run(outdir,a1_file):
    out=Path(outdir);out.mkdir(parents=True,exist_ok=True)
    os.environ["MCIAS_ENVIRONMENT"]="development"
    os.environ["MCIAS_MALWARE_SCAN"]="disabled"
    os.environ["MCIAS_LOCAL_OCR"]="disabled"
    a1=load_a1(a1_file)
    engine=create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    reports=[];negative={}
    with tempfile.TemporaryDirectory(prefix="mcias-qualified-reader-") as private:
        store=EncryptedStore(str(Path(private)/"sealed"),os.urandom(32))
        with Session(engine) as db:
            org=Organization(name="synthetic qualification")
            other=Organization(name="synthetic unrelated organization")
            actor=User(username="synthetic_ocr_qualification",password_hash="not-real")
            db.add_all([org,other,actor]);db.flush()
            actor.organization_id=org.id;db.commit()
            for case,style in STYLES.items():
                gold=make_fixture(case,out)
                original=Path(gold["pdf_path"]).read_bytes()
                registered=ingest(db,store,org.id,actor.id,case+".pdf",original)
                assert registered["status"]=="review_required"
                original_reopened,doc,src=reopen(db,store,registered["document_id"],org.id,gold["pdf_sha256"])
                assert original_reopened==original
                job=db.get(IngestionJob,registered["job_id"])
                assert job.status=="review_required"
                assert db.scalars(select(ExtractedSourceRecord).where(
                    ExtractedSourceRecord.job_id==job.id)).all()==[]
                pdfpath=Path(private)/(case+"_source.pdf")
                pdfpath.write_bytes(original_reopened)
                tokens,elapsed=read_pixels_and_words(pdfpath,doc.sha256,style["lang"])
                parsed=parse_dynamic(tokens,doc.id,doc.sha256,style["lang"])
                total=create_candidates(db,doc,job,parsed)
                db.commit()
                assert total==18
                baseline=examine(db,store,org.id,doc.id,doc.sha256,gold,private)
                assert baseline["candidate_count"]==18
                assert baseline["score"]=={"fields":18,"locations":18}
                assert all(x.status=="UNVERIFIED_OCR_CANDIDATE" for x in all_candidates(db,org.id,doc.id))
                # Only use existing A1 pure arithmetic preview, never the trusted G4/G2 adapter.
                preview=a1_payload(parsed,case) if baseline["safe_for_advisory_preview"] else None
                findings=a1.analyze(preview) if preview else None
                arithmetic=[f for f in findings["findings"] if f["finding_type"]=="LINE_ARITHMETIC"] if findings else []
                report={"case":case,"document_id":doc.id,"sha256":doc.sha256,
                        "candidate_count":total,"candidate_status":"UNVERIFIED_OCR_CANDIDATE",
                        "independent_synthetic_gold_fields":baseline["score"]["fields"],
                        "independent_synthetic_gold_regions":baseline["score"]["locations"],
                        "qualification":baseline["issues"] or ["SYNTHETIC_MATCH_NOT_AUTHORITY"],
                        "a1_pure_advisory_ran":bool(findings),
                        "a1_arithmetic":len(arithmetic) if findings else None,
                        "g2_status":doc.status,"g2_trusted_rows_created":False,
                        "a1_source_verifications":[],
                        "g2_ocr_evidence_trusted":False,
                        "human_review":"REQUIRED","financial_decision":"NOT_AUTHORIZED"}
                reports.append(report)
                (out/(case+"_candidate_review.json")).write_text(json.dumps(report,ensure_ascii=False,indent=2))
