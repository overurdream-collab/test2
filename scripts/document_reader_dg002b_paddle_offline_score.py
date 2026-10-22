#!/usr/bin/env python3
"""Evaluate ONLY a completed and SHA-matched PaddleOCR-VL sample, no model load.
Page-wide VLM bbox NEVER passes field-source evidence threshold.
"""
import argparse,json,re
from pathlib import Path
from scripts.document_reader_dg002_score import evaluate
from scripts.document_reader_dg002b_benchmark import LABELS, make_fixtures

def run(snapshot,gold,output):
    record=json.loads(Path(snapshot).read_text())
    oracle=json.loads(Path(gold).read_text())
    truth={d["id"]:d for d in oracle["documents"]}
    docs=[]
    for raw in record["model_output"]:
        ident=raw["id"]
        if ident not in truth or raw["sha256"]!=truth[ident]["sha256"]:
            raise ValueError("SOURCE_SHA256_MISMATCH_OR_UNEXPECTED_MODEL_DOCUMENT")
        lines=raw["ocr_block_text"].splitlines()
        fields=[]
        for line in lines:
            parts=line.strip().split(None,1)
            if len(parts)<2:continue
            label=parts[0].strip().upper()
            fid=next((name for name,alias in LABELS.items() if alias==label),None)
            if not fid:continue
            fields.append({"field_id":fid,"kind":"VLM_TEXT_ONLY","value":parts[1].strip(),
                "page":raw["page"],"row_id":"main","bbox":raw["page_bbox"],
                "review_required":True,"evidence_scope":"PAGE_ONLY_NOT_VERIFIED_FIELD_CELL"})
        docs.append({"id":ident,"sha256":raw["sha256"],"language":truth[ident]["language"],
          "pages":[{"page":raw["page"],"text":raw["ocr_block_text"]}],"fields":fields})
    pred={"engine":"PaddleOCR-VL-1.6 ACTUAL CPU ONLY COMPLETED SAMPLE",
          "documents":docs,"runtime_seconds":sum(x["elapsed_seconds"] for x in record["model_output"]),
          "peak_rss_mb":None,"peak_vram_mb":None,
          "source_bbox_status":"FULL_PAGE_ONLY_NOT_CELL_EVIDENCE",
          "model_revision":record["model_revision"],"model_weight_sha256":record["model_weight_sha256"]}
    selected={"documents":[truth[x["id"]] for x in docs]}
    report=evaluate(selected,pred)
    report["full_corpus_coverage"]={"executed":len(docs),"expected":len(truth),
         "eligible_for_full_eight_document_comparison":len(docs)==len(truth)}
    report["source_binding_qualification"]="UNQUALIFIED_PAGE_WIDE_BBOX"
    report["note"]="Single English invoice only; no Arabic inference; no individual cell evidence; all decisions HUMAN_REVIEW."
    root=Path(output);root.mkdir(parents=True,exist_ok=True)
    (root/"paddle_partial_prediction.json").write_text(json.dumps(pred,ensure_ascii=False,indent=2))
    (root/"paddle_partial_metrics.json").write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps({"executed":len(docs),"corpus_total":len(truth),
      "fields_exact":report["fields_exact"],"fields_expected_sample":report["fields_expected"],
      "fields_exact_and_aligned":report["fields_exact_and_aligned"],
      "cer":report["cer_whitespace_ignored"],"wer":report["wer_whitespace_tokenized"],
      "source_binding":report["source_binding_qualification"]}))
    return report

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--snapshot",required=True)
    p.add_argument("--gold",required=True);p.add_argument("--out",required=True)
    a=p.parse_args();run(a.snapshot,a.gold,a.out)
