#!/usr/bin/env python3
"""Real offline Tesseract OCR baseline on generated Arabic/English image fixtures."""
from __future__ import annotations
import io, json, os, resource, sys, time
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from mcias.ingestion.ocr_engine import recognize, OCRUnavailable

SAMPLES=[
 ("english_invoice","eng",["INVOICE SYN 2026 15","CBC 2 x 15.00 = 30.00 USD","XRAY 1 x 45.00 = 45.00 USD"]),
 ("english_laboratory","eng",["LABORATORY SYNTHETIC","Hemoglobin 13.5 g/dL","Reference 12.0 - 16.0"]),
 ("arabic_invoice","ara",["فاتورة طبية اصطناعية","تحليل دم ٢ بسعر ١٥","الإجمالي ٣٠ ريال"]),
 ("arabic_lab","ara",["نتائج مختبر اصطناعية","الهيموجلوبين ١٣٫٥","المجال المرجعي ١٢ إلى ١٦"]),
]

def distance(a,b):
    prev=list(range(len(b)+1))
    for i,x in enumerate(a,1):
        cur=[i]
        for j,y in enumerate(b,1):
            cur.append(min(cur[-1]+1,prev[j]+1,prev[j-1]+(x!=y)))
        prev=cur
    return prev[-1]

def make_image(lines,arabic,variant,fontfile):
    im=Image.new("RGB",(1500,600),"white");d=ImageDraw.Draw(im)
    font=ImageFont.truetype(fontfile,48)
    for i,line in enumerate(lines):
        if arabic:
            d.text((1420,60+145*i),line,font=font,fill="black",anchor="ra",direction="rtl")
        else:
            d.text((65,60+145*i),line,font=font,fill="black")
    if variant=="tilted":im=im.rotate(2,expand=False,fillcolor="white")
    if variant=="blurred":im=im.filter(ImageFilter.GaussianBlur(1.4))
    return im

def main(dest):
    out=Path(dest);out.mkdir(parents=True,exist_ok=True)
    font="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    if not Path(font).is_file():raise RuntimeError("Missing known DejaVu synthetic font")
    os.environ["MCIAS_LOCAL_OCR"]="tesseract"
    rows=[]
    for ident,language,lines in SAMPLES:
        for variant in ("clean","tilted","blurred"):
            im=make_image(lines,language=="ara",variant,font)
            path=out/(ident+"_"+variant+".png");im.save(path)
            buf=io.BytesIO();im.save(buf,format="PNG")
            os.environ["MCIAS_OCR_LANG"]=language
            start=time.perf_counter()
            try:
                predicted=recognize(buf.getvalue())
                error=None
            except OCRUnavailable as exc:
                predicted="";error=str(exc)
            elapsed=time.perf_counter()-start
            # Raw OCR line order and spacing can differ: report strictly normalized CER,
            # never pretend this is field-level accuracy.
            import re
            normalize=lambda s:"".join(s.split())
            truth=normalize("".join(lines)); pred=normalize(predicted)
            rows.append({"fixture":ident,"language":language,"variant":variant,
                         "ground_truth":lines,"prediction":predicted,
                         "normalized_cer":distance(truth,pred)/max(len(truth),1),
                         "seconds":round(elapsed,4),"process_peak_rss_kb":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                         "error":error,"engine":"MCIAS Tesseract local adapter"})
    (out/"offline_ocr_baseline.json").write_text(json.dumps({
        "measurements":rows,"scope":"real synthetic image OCR; no field binding, bounding box, table or clinical performance validation",
        "paddleocr":"NOT_RUN","surya":"NOT_RUN"},ensure_ascii=False,indent=2))
    assert len(rows)==12
    assert all(x["error"] is None for x in rows),[x for x in rows if x["error"]]
    print(json.dumps({"samples":len(rows),"engine":"MCIAS Tesseract local adapter",
                       "arabic_mean_cer":sum(x["normalized_cer"] for x in rows if x["language"]=="ara")/6,
                       "english_mean_cer":sum(x["normalized_cer"] for x in rows if x["language"]=="eng")/6}))

if __name__=="__main__":
    main(sys.argv[1] if len(sys.argv)>1 else "reader-ocr-results")
