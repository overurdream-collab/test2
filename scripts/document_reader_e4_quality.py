#!/usr/bin/env python3
"""Small new source-role holdout; existing OCR, mapper and A1 envelope only.
No Gold is passed to OCR or parsing. No G2, database, model download or decision.
"""
from __future__ import annotations
import argparse,hashlib,io,json,resource,time
from pathlib import Path
import fitz
from PIL import Image,ImageDraw,ImageFont
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from scripts.document_reader_dg002b_benchmark import tesseract_run,record_runtime
from scripts.document_reader_dg002_score import bbox_iou,canonical,edit_distance
from scripts.document_reader_dynamic_layout_pilot import parse_dynamic,score,a1_payload,a1_block_reasons

FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
SIZE=(1700,1500)
def sha(data):return hashlib.sha256(data).hexdigest()
def save(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')


def create_holdout(root):
    """Author source pixels and truth once, before any engine call."""
    cases=[]
    for name,arabic,ambiguous in [('shifted_invoice',False,False),('reordered_arabic',True,False),('conflicting_dates',False,True)]:
        image=Image.new('RGB',SIZE,'white');draw=ImageDraw.Draw(image)
        font=ImageFont.truetype(FONT,31);small=ImageFont.truetype(FONT,29)
        draw.text((120,30),'SYNTHETIC INVOICE HOLDOUT',font=font,fill='black')
        rows=[dict(id='QX',code='LAB-X' if not arabic else 'أشعة',unit='EA',qty='2',price='42.00',total='84.00'),
              dict(id='QY',code='RX-Y' if not arabic else 'دواء',unit='EA',qty='1',price='84.00',total='84.00')]
        provider='SYN-HOSPITAL-73' if arabic else 'SYN-HOSPITAL-42'
        service='2026-05-07' if arabic else '2026-04-09'
        metadata=[('effective_from','EFFECTIVE FROM','2026-02-01' if arabic else '2025-12-01'),
                  ('document_date','INVOICE_DATE','2026-05-09' if arabic else '2026-04-10'),
                  ('provider','PROVIDER',provider),('service_date','SERVICE DATE',service),
                  ('effective_until','EFFECTIVE UNTIL','2026-12-31'),
                  ('invoice_number','INVOICE','INV-2026-842' if arabic else 'INV-2026-731'),
                  ('currency','CURRENCY','USD'),('stated_total','GRANDTOTAL','168.00')]
        if arabic:metadata=[metadata[i] for i in (4,2,0,5,1,6,3,7)]
        if ambiguous:metadata.insert(4,('service_date','SERVICE DATE','2026-04-11'))
        gold={};truth=['SYNTHETIC INVOICE HOLDOUT']
        for i,(role,label,value) in enumerate(metadata):
            y=100+i*62;draw.text((120,y),label,font=small,fill='black')
            draw.text((900,y),value,font=small,fill='black')
            box=list(draw.textbbox((900,y),value,font=small));box=[box[0]-5,box[1]-5,box[2]+5,box[3]+5]
            gold.setdefault(role,[]).append({'value':value,'label':label,'source_line':i+2,'bbox':box})
            truth.append(label+' '+value)
        order=['total','code','qty','id','price','unit'] if arabic else ['id','code','unit','qty','price','total']
        xs=[110,390,680,930,1160,1430] if arabic else [110,360,650,900,1140,1410]
        labels={'id':'ID','code':'CODE','unit':'UNIT','qty':'QTY','price':'PRICE','total':'TOTAL'}
        for x,key in zip(xs,order):draw.text((x,840),labels[key],font=font,fill='black')
        truth.append(' '.join(labels[k] for k in order));boxes=[]
        for ri,row in enumerate(rows):
            y=930+ri*140;cells={}
            for x,key in zip(xs,order):
                value=row[key];draw.text((x,y),value,font=font,fill='black')
                b=draw.textbbox((x,y),value,font=font);cells[key]=[b[0]-7,b[1]-7,b[2]+7,b[3]+7]
            boxes.append(cells);truth.append(' '.join(row[k] for k in order))
        png=root/(name+'.png');image.save(png)
        stream=io.BytesIO();pdf=canvas.Canvas(stream,pagesize=(850,750),invariant=1)
        pdf.drawImage(ImageReader(image),0,0,width=850,height=750);pdf.showPage();pdf.save()
        original=stream.getvalue();(root/(name+'.pdf')).write_bytes(original)
        cases.append({'id':name,'language':'ar' if arabic else 'en','engine_language':'ara+eng' if arabic else 'eng',
            'pdf':name+'.pdf','pdf_sha256':sha(original),'image':png.name,'image_sha256':sha(png.read_bytes()),
            'ambiguous':ambiguous,'metadata':gold,'rows':rows,'cell_boxes':boxes,'text':'\n'.join(truth)})
    save(root/'holdout_gold.json',{'oracle':'AUTHORED_BEFORE_OCR_NOT_USED_FOR_PREDICTION','cases':cases})
    return cases


def source_pixels(original,expected_sha):
    if sha(original)!=expected_sha:raise ValueError('ORIGINAL_PDF_SHA256_MISMATCH')
    with fitz.open(stream=original,filetype='pdf') as pdf:
        if len(pdf)!=1 or pdf[0].get_text().strip():raise ValueError('NOT_IMAGE_ONLY_HOLDOUT')
        pixels=pdf[0].get_pixmap(matrix=fitz.Matrix(2,2),alpha=False)
        image=Image.frombytes('RGB',(pixels.width,pixels.height),pixels.samples)
    buffer=io.BytesIO();image.save(buffer,format='PNG')
    return buffer.getvalue()


def run(root):
    root.mkdir(parents=True,exist_ok=True);cases=create_holdout(root)
    frozen=sha((root/'holdout_gold.json').read_bytes());record_runtime(root)
    predictions=[];raw=[];elapsed=0
    # Predictor receives only source bytes, ID/hash and chosen installed language.
    for case in cases:
        original=(root/case['pdf']).read_bytes();pixels=source_pixels(original,case['pdf_sha256'])
        words,text,seconds=tesseract_run(pixels,case['language']);elapsed+=seconds
        words=[{**w,'confidence_uncalibrated':w['confidence_uncalibrated']/100 if w['confidence_uncalibrated'] is not None else 0} for w in words]
        parsed=parse_dynamic(words,case['id'],case['pdf_sha256'],case['engine_language'])
        packet={'document_id':case['id'],'original_sha256':case['pdf_sha256'],'rendered_page_sha256':sha(pixels),
            'parsed':parsed,'a1_advisory_envelope':a1_payload(parsed,case['id']),
            'a1_blocked_reasons':a1_block_reasons(parsed),'human_review_required':True,
            'financial_decision':'NOT_AUTHORIZED','g2_native_rows_verified':False,
            'a1_trusted_input_eligible':False,'qualified_financial_evidence':False}
        predictions.append(packet);raw.append({'id':case['id'],'words':words,'text':text,'engine_seconds':seconds})
    save(root/'predictions.json',{'packets':predictions});save(root/'raw.json',{'documents':raw})
    # Scoring begins after predictions are saved; it never selects an OCR region.
    actual={p['document_id']:p for p in predictions};texts={p['id']:p['text'] for p in raw}
    details=[];exact=bound=expected=cd=cc=wd=wc=0;negative=[];tables=[]
    for case in cases:
        packet=actual[case['id']];parsed=packet['parsed']
        if case['ambiguous']:
            negative.append({'id':case['id'],'service_date_abstained':'service_date' not in parsed['fields'],
                'a1_blocked':packet['a1_advisory_envelope'] is None,'reasons':packet['a1_blocked_reasons']})
            assert negative[-1]['service_date_abstained'] and negative[-1]['a1_blocked']
        else:
            for role,truths in case['metadata'].items():
                truth=truths[0];field=parsed['fields'].get(role)
                value_ok=bool(field and field['value']==truth['value'])
                binding_ok=bool(field and field.get('source_line')==truth['source_line'] and bbox_iou(field['bbox_pixels'],truth['bbox'])>=0.5)
                expected+=1;exact+=value_ok;bound+=binding_ok
                details.append({'document_id':case['id'],'field':role,'expected':truth,'actual':field,
                    'value_exact':value_ok,'field_binding_correct':binding_ok})
        truth=canonical(case['text']);observed=canonical(texts[case['id']]);a,b=''.join(truth.split()),''.join(observed.split())
        cd+=edit_distance(a,b);cc+=len(a);wd+=edit_distance(truth.split(),observed.split());wc+=len(truth.split())
        tables.append({'document_id':case['id'],**score(case,parsed)})
    assert frozen==sha((root/'holdout_gold.json').read_bytes())
    try:source_pixels((root/cases[0]['pdf']).read_bytes()+b'changed',cases[0]['pdf_sha256'])
    except ValueError:tamper=True
    else:raise AssertionError('ALTERED_SOURCE_ACCEPTED')
    result={'status':'ISOLATED_SOURCE_ROLE_HOLDOUT_NOT_MODEL_QUALIFICATION','documents':len(cases),
        'positive_metadata_fields':expected,'metadata_values_exact':exact,'metadata_field_bindings_correct':bound,
        'metadata_value_accuracy':exact/expected,'metadata_binding_accuracy':bound/expected,
        'page_CER':cd/cc,'page_WER':wd/wc,'runtime_seconds':round(elapsed,4),
        'peak_individual_process_rss_mib':max(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss)/1024,
        'negative_cases':negative,'original_byte_tamper_rejected':tamper,'qualified_financial_fields':0,
        'all_human_review':True,'details':details,'table_scores':tables,'gold_sha256':frozen}
    save(root/'metrics.json',result)
    print(json.dumps({k:v for k,v in result.items() if k not in ('details','table_scores')},ensure_ascii=False))
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--out',required=True)
    run(Path(parser.parse_args().out))
