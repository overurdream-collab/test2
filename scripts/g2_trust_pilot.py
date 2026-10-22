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

                restored=out/(case+'_source.pdf')
                restored.write_bytes(pdf)

                words,secs=read_pixels_and_words(restored,doc.sha256,style["lang"])
                parsed=parse_dynamic(words,doc.id,doc.sha256,style["lang"])
                measured=score(gold,parsed)
                valid=not parsed["issues"] and measured["exact_values"]==18 and measured["correct_cell_locations"]==18

                for row in parsed["rows"]:
                    for field in row.values():
                        if field:
                            assert field["source"]["document_id"]==doc.id
                            assert field["source"]["sha256"]==doc.sha256
                            assert field["value"]==" ".join(w["text"] for w in field["ocr_word_evidence"])
                payload=a1_payload(parsed,case) if valid else None
                analysis=agent.analyze(payload) if payload else None
                findings=[x for x in analysis["findings"] if x["finding_type"]=="LINE_ARITHMETIC"] if analysis else []

                report={"case":case,"g2_document_id":doc.id,"g2_sha256":doc.sha256,
                        "g2_ingestion_status":doc.status,"encrypted_roundtrip":True,
                        "local_pdf_bytes_verified":True,"g2_native_cell_rows_verified":False,
                        "extracted_values":measured["exact_values"],
                        "cell_positions":measured["correct_cell_locations"],
                        "reader_issues":parsed["issues"],"a1_ran":bool(analysis),
                        "a1_arithmetic_findings":len(findings) if analysis else None,
                        "ocr_seconds":secs,"outcome":"HUMAN_REVIEW",
                        "financial_decision":"NOT_AUTHORIZED"}
                reports.append(report)
                (out/(case+"_review.json")).write_text(json.dumps(report,indent=2))

    engine.dispose()
    by={r["case"]:r for r in reports}
    for case,n in (("english_columnar",0),("english_reordered",2)):
        r=by[case]
        assert r["extracted_values"]==18 and r["cell_positions"]==18
        assert r["a1_ran"] and r["a1_arithmetic_findings"]==n
        assert r["g2_ingestion_status"]=="review_required"
    assert by["arabic_rtl"]["a1_ran"] is False
    assert negative==6

    summary={"status":"PASS_G2_ENCRYPTED_SOURCE_CUSTODY_SYNTHETIC",
             "negative_source_checks":negative,"cases":reports,
             "g2_original_bytes_verified":True,"g2_ocr_cell_rows_verified":False,
             "a1_trusted_input_used":False,
             "warning":"G2 quarantines scanned pages with OCR off; synthetic gold matching does not establish native G2 row evidence."}
    (out/"g2_source_results.json").write_text(json.dumps(summary,indent=2))
    print(json.dumps({"gate":summary["status"],"cases":len(reports),"negative":negative}))

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--out",required=True);p.add_argument("--a1",required=True)
    a=p.parse_args();run(a.out,a.a1)
