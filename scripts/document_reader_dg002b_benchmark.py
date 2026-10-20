#!/usr/bin/env python3
"""DG-002B reproducible synthetic medical OCR suite; only Tesseract inference here.
Frozen authored gold is generated independently of engine predictions. No PHI, G2 or A1.
"""
from __future__ import annotations
import argparse, csv, hashlib, io, json, os, platform, re, resource, subprocess, sys, time
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from scripts.document_reader_dg002_score import evaluate

FONT="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
SIZE=(1280,1040)
# Synthetic template values ONLY in creation, never in Tesseract inference.
FIXTURES=(
 ("invoice_en","en","invoice",(("service_name","service","Complete blood count"),("quantity","quantity","2"),("unit_price","amount","15.00"),("line_total","amount","30.00"))),
 ("invoice_ar","ar","invoice",(("service_name","service","تحليل دم شامل"),("quantity","quantity","٢"),("unit_price","amount","١٥٫٠٠"),("line_total","amount","٣٠٫٠٠"))),
 ("lab_en","en","laboratory",(("test_name","lab_test","Hemoglobin"),("test_result","lab_result","13.5"),("unit","lab_unit","g/dL"),("reference","reference_range","12.0-16.0"))),
 ("lab_ar","ar","laboratory",(("test_name","lab_test","الهيموجلوبين"),("test_result","lab_result","١٣٫٥"),("unit","lab_unit","غ/دل"),("reference","reference_range","١٢-١٦"))),
 ("radiology_en","en","radiology",(("site","anatomical_site","Chest"),("finding","radiology_finding","No focal opacity"),("modality","modality","X-ray"))),
 ("radiology_ar","ar","radiology",(("site","anatomical_site","الصدر"),("finding","radiology_finding","لا يوجد ارتشاح"),("modality","modality","أشعة سينية"))),
 ("prescription_en","en","prescription",(("drug","medication_name","Amoxicillin"),("strength","medication_strength","500 mg"),("dose","medication_dose","1 capsule"),("frequency","frequency","twice daily"))),
 ("prescription_ar","ar","prescription",(("drug","medication_name","أموكسيسيلين"),("strength","medication_strength","٥٠٠ ملغ"),("dose","medication_dose","كبسولة واحدة"),("frequency","frequency","مرتان يوميا"))),
)
LABELS={"service_name":"SERVICE","quantity":"QUANTITY","unit_price":"UNITPRICE",
        "line_total":"AMOUNT","test_name":"TEST","test_result":"RESULT",
        "unit":"UNIT","reference":"REFERENCE","site":"SITE",
        "finding":"FINDING","modality":"MODALITY","drug":"DRUG",
        "strength":"STRENGTH","dose":"DOSE","frequency":"FREQUENCY"}
TITLE={"invoice":"MEDICAL INVOICE","laboratory":"LABORATORY REPORT",
       "radiology":"RADIOLOGY REPORT","prescription":"PRESCRIPTION"}
FONT_SIZE=39
def sha(data):return hashlib.sha256(data).hexdigest()
def jsonsave(path,obj):Path(path).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def make_fixtures(root):
    root=Path(root);(root/"assets").mkdir(parents=True,exist_ok=True)
    font=ImageFont.truetype(FONT,FONT_SIZE)
    small=ImageFont.truetype(FONT,36)
    documents=[];manifest=[]
    for ident,lang,category,fields in FIXTURES:
        image=Image.new("RGB",SIZE,"white");d=ImageDraw.Draw(image)
        d.text((65,45),TITLE[category],font=font,fill="black")
        lines=[TITLE[category]];labels=[]
        for i,(field_id,kind,value) in enumerate(fields):
            y=185+i*159;lab=LABELS[field_id]
            d.text((68,y),lab,font=small,fill="black")
            if lang=="ar":
                pos=(1130,y-4)
                bbox=d.textbbox(pos,value,font=font,anchor="ra",direction="rtl")
                d.text(pos,value,font=font,fill="black",anchor="ra",direction="rtl")
            else:
                pos=(435,y-4)
                bbox=d.textbbox(pos,value,font=font)
                d.text(pos,value,font=font,fill="black")
            # Gold bbox is the actual printed text region, not an OCR prediction.
            gold_box=[max(0,bbox[0]-7),max(0,bbox[1]-7),min(SIZE[0],bbox[2]+7),min(SIZE[1],bbox[3]+7)]
            labels.append({"field_id":field_id,"kind":kind,"value":value,"page":1,
                           "row_id":"main","bbox":gold_box})
            lines.append(lab+" "+value)
        im_path=root/"assets"/(ident+".png");image.save(im_path,optimize=False)
        png=im_path.read_bytes()
        # Image-only PDF: visual fixture, not selectable text.
        mem=io.BytesIO();pdf=canvas.Canvas(mem,pagesize=(640,520),invariant=1,pageCompression=0)
        pdf.drawImage(ImageReader(image),0,0,width=640,height=520)
        pdf.showPage();pdf.save()
        pdf_bytes=mem.getvalue();pdf_path=root/"assets"/(ident+".pdf");pdf_path.write_bytes(pdf_bytes)
        documents.append({"id":ident,"sha256":sha(png),"language":lang,
                          "pages":[{"page":1,"text":"\n".join(lines)}],"fields":labels})
        manifest.append({"id":ident,"category":category,"language":lang,
                          "image":"assets/"+im_path.name,"image_sha256":sha(png),
                          "pdf":"assets/"+pdf_path.name,"pdf_sha256":sha(pdf_bytes),
                          "page_count":1,"pixel_width":SIZE[0],"pixel_height":SIZE[1]})
    jsonsave(root/"gold.json",{"documents":documents,"oracle":"AUTHORED_SYNTHETIC_NOT_OCR"})
    jsonsave(root/"manifest.json",{"fixtures":manifest,"schema":"DG002_B_LOCKED_V1",
                                   "generation":"deterministic authored source, independent of predictions"})
    return manifest

def tesseract_run(png,language):
    lang="eng" if language=="en" else "ara+eng"
    start=time.perf_counter()
    run=subprocess.run(["tesseract","stdin","stdout","-l",lang,"--psm","6","tsv"],
                       input=png,capture_output=True,timeout=30)
    if run.returncode:
        raise RuntimeError("TESSERACT_TSV_FAILED: "+run.stderr.decode(errors="replace")[-400:])
    words=[]
    for r in csv.DictReader(io.StringIO(run.stdout.decode()),delimiter="\t"):
        text=r.get("text","").strip().replace("\u200e","").replace("\u200f","")
        if not text:continue
        left,top,w,h=(int(r[z]) for z in ("left","top","width","height"))
        words.append({"text":text,"bbox":[left,top,left+w,top+h],
                      "confidence_uncalibrated":float(r["conf"]) if float(r["conf"])>=0 else None,
                      "line_key":(r["block_num"],r["par_num"],r["line_num"])})
    text_run=subprocess.run(["tesseract","stdin","stdout","-l",lang,"--psm","6"],
                            input=png,capture_output=True,timeout=30)
    if text_run.returncode:raise RuntimeError("TESSERACT_TEXT_FAILED")
    return words,text_run.stdout.decode(errors="replace").strip(),time.perf_counter()-start

def associate_fields(words,language="en"):
    """Label/row matching only from OCR TSV. No gold/fixture field values, no fixed cells."""
    grouped={}
    for w in words:grouped.setdefault(w["line_key"],[]).append(w)
    output=[]
    for line in grouped.values():
        ordered=sorted(line,key=lambda w:w["bbox"][0])
        key=None
        for word in ordered:
            name=re.sub(r"[^A-Z]","",word["text"].upper())
            if name in LABELS.values():
                key=next((k for k,v in LABELS.items() if v==name),None)
                break
        if key is None:continue
        values=[w for w in ordered if w["bbox"][0]>=300]
        if not values:continue
        values.sort(key=lambda w:w["bbox"][0],reverse=language=="ar")
        value=" ".join(w["text"] for w in values)
        box=[min(w["bbox"][0] for w in values),min(w["bbox"][1] for w in values),
             max(w["bbox"][2] for w in values),max(w["bbox"][3] for w in values)]
        output.append({"field_id":key,"kind":"OCR_DETECTED","value":value,
                       "page":1,"row_id":"main","bbox":box,
                       "review_required":True,"confidence_uncalibrated":min(
                          [w["confidence_uncalibrated"] for w in values if w["confidence_uncalibrated"] is not None] or [None])})
    return output

def run_tesseract(root):
    root=Path(root);manifest=json.loads((root/"manifest.json").read_text())["fixtures"]
    docs=[];results=[];total_runtime=0
    for item in manifest:
        f=root/item["image"];png=f.read_bytes()
        if sha(png)!=item["image_sha256"]:raise ValueError("INPUT_SHA_MISMATCH")
        t0=time.perf_counter()
        words,text,secs=tesseract_run(png,item["language"])
        total_runtime+=secs
        fields=associate_fields(words,item["language"])
        docs.append({"id":item["id"],"sha256":item["image_sha256"],
                     "language":item["language"],"pages":[{"page":1,"text":text}],
                     "fields":fields})
        results.append({"id":item["id"],"raw_text":text,"raw_tsv_words":words,
                        "recognized_fields":len(fields),"engine_seconds":round(secs,4)})
    version=subprocess.run(["tesseract","--version"],capture_output=True,text=True).stdout.splitlines()[0]
    language_checksum={}
    for lang in ("ara","eng"):
        t=subprocess.run(["tesseract","--list-langs"],capture_output=True,text=True)
        language_checksum[lang]="INSTALLED" if lang in t.stdout.split() or lang in t.stderr.split() else "MISSING"
    pred={"engine":"Tesseract "+version,"documents":docs,
          "runtime_seconds":round(total_runtime,3),
          "peak_rss_mb":round(max(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                                   resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss)/1024,3),
          "peak_vram_mb":None,
          "machine":platform.platform(),"backend":"CPU",
          "confidence_status":"UNCALIBRATED_HUMAN_REVIEW_ONLY"}
    jsonsave(root/"predictions_tesseract.json",pred)
    jsonsave(root/"raw_tesseract.json",{"pages":results,"engine":version,"languages":language_checksum})
    report=evaluate(json.loads((root/"gold.json").read_text()),pred)
    report["benchmark_notes"]={"model_inference":"ACTUAL_TESSERACT_LOCAL",
       "all_fields_review_required":True,"model_folds":"tiny synthetic fixed evaluation only",
       "bbox_coordinates":"image pixels","automatic_medical_or_financial_decisions":False}
    jsonsave(root/"metrics_tesseract.json",report)
    error_cases=[]
    for detail in report["details"]:
        if not detail["exact_value"] and not detail["correct_page_row_and_iou"]:
            cls="READING_AND_ASSOCIATION_FAILURE"
        elif not detail["exact_value"]:
            cls="OCR_OR_FIELD_READING_FAILURE"
        elif not detail["correct_page_row_and_iou"]:
            cls="EVIDENCE_ASSOCIATION_FAILURE"
        else:
            continue
        error_cases.append({"classification":cls,**detail})
    jsonsave(root/"error_analysis.json",{"errors":error_cases,
        "separate_reading_and_association":True,
        "memory_metric":"maximum parent or child process peak RSS on Linux; not summed concurrent RSS"})
    print(json.dumps({"engine":version,"documents":len(docs),"fields_expected":report["fields_expected"],
      "fields_exact":report["fields_exact"],"source_aligned":report["evidence_source_aligned"],
      "CER":report["cer_whitespace_ignored"],"WER":report["wer_whitespace_tokenized"],
      "runtime_seconds":pred["runtime_seconds"],"peak_rss_mb":pred["peak_rss_mb"]}))
    return report

def main():
    p=argparse.ArgumentParser();p.add_argument("--out",required=True)
    p.add_argument("--generate-only",action="store_true")
    p.add_argument("--use-frozen",action="store_true")
    args=p.parse_args();root=Path(args.out)
    if args.use_frozen:
        if not (root/"gold.json").is_file():raise ValueError("FROZEN_GOLD_MISSING")
    else:make_fixtures(root)
    if not args.generate_only:run_tesseract(root)
if __name__=="__main__":main()
