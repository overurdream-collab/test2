#!/usr/bin/env python3
"""Isolated synthetic Reader benchmark; no network, database, or patient data."""
from __future__ import annotations
import io, json, time, re, pathlib, tempfile
from reportlab.pdfgen import canvas
from pypdf import PdfReader

CASES = {
 "invoice": ["INV-2026-001","CBC","2","15.00","30.00","USD"],
 "laboratory": ["LAB-2026-001","Hemoglobin","13.5","g/dL","12.0-16.0"],
 "radiology": ["RAD-2026-001","Chest X-ray","No acute findings"],
 "prescription": ["RX-2026-001","Amoxicillin","500 mg","twice daily"],
 "mixed": ["MED-2026-001","Diagnosis: Synthetic example","Total 45.00 USD"],
}
def make_pdf(lines, image_only=False):
    from reportlab.lib.utils import ImageReader
    from PIL import Image, ImageDraw
    buf=io.BytesIO(); c=canvas.Canvas(buf,pagesize=(595,842))
    if image_only:
        im=Image.new("RGB",(1200,1000),"white"); d=ImageDraw.Draw(im)
        for i,line in enumerate(lines): d.text((50,40+i*45),line,fill="black")
        c.drawImage(ImageReader(im),36,300,width=520,height=435)
    else:
        for i,line in enumerate(lines): c.drawString(45,790-i*35,line)
    c.showPage(); c.save()
    return buf.getvalue()
def baseline(pdf_bytes):
    t0=time.perf_counter()
    reader=PdfReader(io.BytesIO(pdf_bytes),strict=True)
    pages=[]; review=[]
    for idx,page in enumerate(reader.pages,1):
        text=page.extract_text() or ""
        pages.append({"page":idx,"text":text,"locator":{"kind":"page","index":idx}})
        if not text.strip(): review.append(idx)
    return pages,review,time.perf_counter()-t0
def run(out):
    out=pathlib.Path(out);out.mkdir(parents=True,exist_ok=True)
    measurements=[]; ground=[]
    for name,values in CASES.items():
        pdf=make_pdf(values)
        (out/(name+".pdf")).write_bytes(pdf)
        pages,review,secs=baseline(pdf)
        combined="\n".join(p["text"] for p in pages)
        supported=sum(v in combined for v in values)
        measurements.append({"case":name,"mode":"text_pdf","ground_truth_fields":len(values),"exact_values_found":supported,"recall":supported/len(values),"review_required":bool(review),"elapsed_seconds":round(secs,6),"engine":"MCIAS pypdf baseline-compatible text extraction","limitation":"string-level presence, NOT structured field/link accuracy"})
        ground.append({"case":name,"fields":[{"value":v,"evidence":{"page":1,"text":v}} for v in values]})
    scan=make_pdf(CASES["laboratory"],image_only=True)
    (out/"laboratory_scanned.pdf").write_bytes(scan)
    pages,review,secs=baseline(scan)
    measurements.append({"case":"laboratory_scanned","mode":"image_only_pdf","ground_truth_fields":len(CASES["laboratory"]),"exact_values_found":0,"recall":0.0,"review_required":bool(review),"elapsed_seconds":round(secs,6),"engine":"MCIAS pypdf baseline-compatible text extraction","limitation":"OCR is not enabled; scanned pages require HUMAN_REVIEW"})
    ground.append({"case":"laboratory_scanned","fields":[{"value":v,"evidence":{"page":1,"text":v}} for v in CASES["laboratory"]]})
    (out/"ground_truth.json").write_text(json.dumps(ground,ensure_ascii=False,indent=2),encoding="utf8")
    (out/"baseline_results.json").write_text(json.dumps({"measurements":measurements,"status":"baseline_only","field_level_benchmark":"NOT_RUN","paddleocr":"NOT_RUN","surya":"NOT_RUN"},indent=2),encoding="utf8")
    print(json.dumps(measurements,indent=2))
if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser();p.add_argument("--out",default="reader-pilot-results")
    run(p.parse_args().out)
