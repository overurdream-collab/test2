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
def record_runtime(root):
    """Capture actual installed engine/data identity, without downloading models."""
    version=subprocess.run(["tesseract","--version"],capture_output=True,text=True,check=True)
    langs=subprocess.run(["tesseract","--list-langs"],capture_output=True,text=True,check=True)
    listing=langs.stdout+langs.stderr
    match=re.search(r'in "([^"]+)"',listing)
    data_root=Path(match.group(1)) if match else None
    data_hashes={lang:sha((data_root/(lang+".traineddata")).read_bytes())
                 for lang in ("ara","eng") if data_root and (data_root/(lang+".traineddata")).is_file()}
    result={"engine":version.stdout.splitlines()[0],"engine_version_output":version.stdout,
        "language_listing":listing,"traineddata_sha256":data_hashes,
        "OMP_THREAD_LIMIT":os.environ.get("OMP_THREAD_LIMIT"),"backend":"CPU",
        "confidence":"UNCALIBRATED_HUMAN_REVIEW_ONLY","new_vlm_inference":False}
    jsonsave(Path(root)/"runtime_tesseract_identity.json",result)
    return result

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

def tesseract_run(png,language,*,psm=6,engine_language=None):
    lang=engine_language or ("eng" if language=="en" else "ara+eng")
    if type(psm) is not int or psm not in range(1,14) or not re.fullmatch(r"[A-Za-z0-9+_]+",lang):
        raise ValueError("INVALID_OCR_PROFILE")
    start=time.perf_counter()
    # An isolated TESSDATA_PREFIX need not contain the distro's configs/tsv.
    # Set the output mode explicitly and reject a text response rather than
    # silently scoring an empty field list after a successful process exit.
    run=subprocess.run(["tesseract","stdin","stdout","-l",lang,"--psm",str(psm),
                        "-c","tessedit_create_tsv=1"],
                       input=png,capture_output=True,timeout=30)
    if run.returncode:
        raise RuntimeError("TESSERACT_TSV_FAILED: "+run.stderr.decode(errors="replace")[-400:])
    rows=csv.DictReader(io.StringIO(run.stdout.decode()),delimiter="\t")
    if not rows.fieldnames or not {"text","left","top","width","height","conf",
            "block_num","par_num","line_num"}.issubset(rows.fieldnames):
        raise RuntimeError("TESSERACT_TSV_FORMAT_INVALID")
    words=[]
    for r in rows:
        text=r.get("text","").strip().replace("\u200e","").replace("\u200f","")
        if not text:continue
        left,top,w,h=(int(r[z]) for z in ("left","top","width","height"))
        words.append({"text":text,"bbox":[left,top,left+w,top+h],
                      "confidence_uncalibrated":float(r["conf"]) if float(r["conf"])>=0 else None,
                      "line_key":(r["block_num"],r["par_num"],r["line_num"])})
    text_run=subprocess.run(["tesseract","stdin","stdout","-l",lang,"--psm",str(psm)],
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


def associate_source_regions(words,language,*,source_sha256,page_size):
    """Resolve one OCR label to value glyphs using observed geometry, never gold.

    A small glyph-height-derived context margin includes the entire visible
    character region. It does not turn a table/page box into field evidence.
    Ambiguous repeated labels remain in the issue ledger rather than guessing.
    """
    if not isinstance(source_sha256,str) or not re.fullmatch(r"[0-9a-f]{64}",source_sha256):
        raise ValueError("SOURCE_SHA_INVALID")
    if (len(page_size)!=2 or not all(type(v) is int and v>0 for v in page_size)):
        raise ValueError("SOURCE_PAGE_SIZE_INVALID")
    width,height=page_size
    grouped={}
    for word in words:
        box=word.get("bbox",[])
        if (len(box)!=4 or not all(type(v) is int for v in box)
                or not (0<=box[0]<box[2]<=width and 0<=box[1]<box[3]<=height)):
            raise ValueError("SOURCE_BOX_INVALID")
        grouped.setdefault(tuple(word["line_key"]),[]).append(word)
    fields=[];issues=[]
    for row_key,line in grouped.items():
        labels=[]
        for word in line:
            name=re.sub(r"[^A-Z]","",word["text"].upper())
            if name in LABELS.values():
                labels.append((next(k for k,v in LABELS.items() if v==name),word))
        if not labels:continue
        if len(labels)!=1:
            issues.append({"reason_code":"AMBIGUOUS_LABEL_ROW","source_row_key":list(row_key)})
            continue
        key,label=labels[0]
        values=[word for word in line if word is not label
                and word["bbox"][0]>label["bbox"][2]]
        if not values:
            issues.append({"reason_code":"VALUE_REGION_MISSING","field_id":key})
            continue
        values.sort(key=lambda word:word["bbox"][0],reverse=language=="ar")
        glyph_box=[min(w["bbox"][0] for w in values),min(w["bbox"][1] for w in values),
                   max(w["bbox"][2] for w in values),max(w["bbox"][3] for w in values)]
        pad=max(2,min(8,round((glyph_box[3]-glyph_box[1])*0.2)))
        box=[max(label["bbox"][2]+1,glyph_box[0]-pad),max(0,glyph_box[1]-pad),
             min(width,glyph_box[2]+pad),min(height,glyph_box[3]+pad)]
        if (box[2]-box[0])*(box[3]-box[1])>=width*height*0.5:
            issues.append({"reason_code":"REGION_NOT_FIELD_SPECIFIC","field_id":key})
            continue
        value=" ".join(word["text"] for word in values)
        fields.append({"field_id":key,"kind":"OCR_DETECTED","value":value,
            "ocr_value_original":value,"value_normalized":None,"page":1,"row_id":"main",
            "source_row_key":list(row_key),"bbox":box,"glyph_bbox":glyph_box,
            "source_sha256":source_sha256,"rendered_page_sha256":source_sha256,
            "coordinate_system":"SOURCE_IMAGE_PIXELS","image_size":[width,height],
            "locator_method":"TESSERACT_TSV_GLYPHS_WITH_CONTEXT",
            "locator_version":"dg002-field-regions-v1","evidence_profile":"DG002_E2_COMPARISON_ONLY",
            "confidence_uncalibrated":min([w["confidence_uncalibrated"] for w in values
                if w.get("confidence_uncalibrated") is not None] or [None]),
            "review_required":True,"review_reasons":["OCR_UNCALIBRATED","SOURCE_AUTHORITY_NOT_ATTESTED"],
            "g2_native_rows_verified":False,"financial_decision":"NOT_AUTHORIZED"})
    duplicate_ids={f["field_id"] for f in fields if sum(
        other["field_id"]==f["field_id"] for other in fields)>1}
    if duplicate_ids:
        fields=[f for f in fields if f["field_id"] not in duplicate_ids]
        issues.extend({"field_id":key,"reason_code":"MULTIPLE_FIELD_REGIONS"} for key in sorted(duplicate_ids))
    return fields,issues


def compare_source_regions(root):
    """One real baseline, a geometry projection, and bounded Arabic crop OCR.

    Gold is loaded only after all predictions exist. Page CER/WER is retained
    from baseline: per-field crop OCR is not a new full-page transcription.
    """
    root=Path(root)
    frozen={name:sha((root/name).read_bytes()) for name in ("gold.json","manifest.json")}
    manifest=json.loads((root/"manifest.json").read_text())["fixtures"]
    baseline=json.loads((root/"predictions_tesseract.json").read_text())
    raw={p["id"]:p for p in json.loads((root/"raw_tesseract.json").read_text())["pages"]}
    base_docs={p["id"]:p for p in baseline["documents"]}
    geometry_docs=[];crop_docs=[];issues=[];crop_trace=[];crop_seconds=0;association_seconds=0
    for item in manifest:
        png=(root/item["image"]).read_bytes()
        if sha(png)!=item["image_sha256"]:raise ValueError("INPUT_SHA_MISMATCH")
        with Image.open(io.BytesIO(png)) as image:
            association_start=time.perf_counter()
            fields,problems=associate_source_regions(raw[item["id"]]["raw_tsv_words"],item["language"],
                source_sha256=item["image_sha256"],page_size=image.size)
            association_seconds+=time.perf_counter()-association_start
            for field in fields:
                field["engine"]=baseline["engine"]
            geometry_docs.append({**base_docs[item["id"]],"fields":fields})
            crop_fields=[]
            for field in fields:
                candidate=dict(field)
                if item["language"]=="ar":
                    box=field["bbox"]
                    buffer=io.BytesIO();image.crop(tuple(box)).save(buffer,format="PNG")
                    crop_words,text,seconds=tesseract_run(buffer.getvalue(),"ar",psm=7,engine_language="ara")
                    crop_seconds+=seconds
                    ordered=sorted(crop_words,key=lambda word:word["bbox"][0],reverse=True)
                    if ordered:
                        candidate["value"]=" ".join(word["text"] for word in ordered)
                        candidate["locator_method"]="SOURCE_REGION_ARABIC_OCR_RECHECK"
                        candidate["ocr_profile"]={"language":"ara","psm":7,"crop_source_bbox":box}
                        candidate["confidence_uncalibrated"]=min([w["confidence_uncalibrated"] for w in ordered
                            if w.get("confidence_uncalibrated") is not None] or [None])
                        if candidate["value"]!=field["value"]:
                            candidate["review_reasons"]=field["review_reasons"]+["OCR_PASSES_DISAGREE"]
                    else:
                        candidate["review_reasons"]=field["review_reasons"]+["REGION_OCR_EMPTY"]
                    crop_trace.append({"document_id":item["id"],"field_id":field["field_id"],
                        "source_sha256":item["image_sha256"],"crop_source_bbox":box,
                        "text":text,"words":crop_words,"seconds":round(seconds,4)})
                crop_fields.append(candidate)
            crop_docs.append({**base_docs[item["id"]],"fields":crop_fields})
        issues.extend({"document_id":item["id"],**issue} for issue in problems)
    common={key:value for key,value in baseline.items() if key!="documents"}
    geometry={**common,"documents":geometry_docs,"association":"SOURCE_REGIONS_V1",
        "runtime_seconds":round(baseline["runtime_seconds"]+association_seconds,3),
        "incremental_association_seconds":round(association_seconds,6)}
    crop={**common,"documents":crop_docs,"association":"SOURCE_REGIONS_ARABIC_RECHECK_V1",
        "runtime_seconds":round(baseline["runtime_seconds"]+association_seconds+crop_seconds,3),
        "incremental_region_runtime_seconds":round(crop_seconds,3),
        "peak_rss_mb":round(max(baseline["peak_rss_mb"],
            resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,
            resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss/1024),3)}
    gold=json.loads((root/"gold.json").read_text())
    reports={name:evaluate(gold,pred) for name,pred in
        (("baseline",baseline),("source_regions",geometry),("arabic_region_recheck",crop))}
    for name,pred in (("source_regions",geometry),("arabic_region_recheck",crop)):
        jsonsave(root/("predictions_"+name+".json"),pred)
    jsonsave(root/"source_region_ocr_trace.json",{"regions":crop_trace,"issues":issues})
    if frozen!={name:sha((root/name).read_bytes()) for name in frozen}:
        raise ValueError("FROZEN_ORACLE_CHANGED")
    summary={"source_frozen_sha256":frozen,"fixture_count":len(manifest),"reports":reports,
        "page_text_metrics":"Baseline pages retained; crop OCR modifies fields only",
        "comparison_scope":"Same image SHA corpus and same actual baseline words; no model or production qualification",
        "all_fields_human_review":True,"financial_decisions":False}
    jsonsave(root/"comparison_source_regions.json",summary)
    print(json.dumps({key:{name:report[name] for name in ("fields_expected","fields_exact",
        "fields_exact_and_aligned","evidence_source_aligned","unsafe_accepted_fields",
        "review_or_missing_fields","cer_whitespace_ignored","wer_whitespace_tokenized")}
        for key,report in reports.items()}))
    return summary

def run_tesseract(root):
    root=Path(root);manifest=json.loads((root/"manifest.json").read_text())["fixtures"]
    record_runtime(root)
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
    # Per-language CER/WER on exactly the same page text. Mixed English labels
    # remain part of Arabic pages: these rates are for bilingual documents, not
    # an isolated Arabic-script test. No change to DG-002A scorer or gold.
    from scripts.document_reader_dg002_score import canonical,edit_distance
    gs={d["id"]:d for d in json.loads((root/"gold.json").read_text())["documents"]}
    language_dist={}
    for lang in ("en","ar"):
        cdist=clen=wdist=wlen=0
        for doc in docs:
            if doc["language"]!=lang:continue
            truth=canonical(gs[doc["id"]]["pages"][0]["text"])
            observed=canonical(doc["pages"][0]["text"])
            a,b="".join(truth.split()),"".join(observed.split())
            cdist+=edit_distance(a,b);clen+=len(a)
            ta,tb=truth.split(),observed.split()
            wdist+=edit_distance(ta,tb);wlen+=len(ta)
        language_dist[lang]={"cer_whitespace_ignored":round(cdist/clen,6) if clen else None,
          "wer_whitespace_tokenized":round(wdist/wlen,6) if wlen else None,
          "page_text_contains_english_labels":True}
    report["text_metrics_by_document_language"]=language_dist
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
    p.add_argument("--compare-source-regions",action="store_true")
    args=p.parse_args();root=Path(args.out)
    if args.use_frozen:
        if not (root/"gold.json").is_file():raise ValueError("FROZEN_GOLD_MISSING")
    else:make_fixtures(root)
    if not args.generate_only:
        run_tesseract(root)
        if args.compare_source_regions:compare_source_regions(root)
if __name__=="__main__":main()
