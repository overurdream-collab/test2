#!/usr/bin/env python3
"""ONE-TIME CPU PaddleOCR-VL-1.6 smoke on the same locked DG-002B images.
Never synthesize field evidence from model text or oracle. No PHI or G2 access.
"""
import argparse, hashlib, json, os, platform, resource, time, traceback
from pathlib import Path

REVISION="676e2aad67375fec9c7dcc9740babec7a0d0d110"
MODEL="PaddlePaddle/PaddleOCR-VL-1.6"
def save(p,obj):Path(p).write_text(json.dumps(obj,ensure_ascii=False,indent=2,default=str)+"\n")
def main():
    arg=argparse.ArgumentParser();arg.add_argument("--dataset",required=True);arg.add_argument("--output",required=True)
    a=arg.parse_args();o=Path(a.output);o.mkdir(parents=True,exist_ok=True)
    ds=Path(a.dataset);manifest=json.loads((ds/"manifest.json").read_text())["fixtures"]
    report={"model":MODEL,"revision":REVISION,"run_type":"ONE_WEIGHT_DOWNLOAD_ONE_CPU_TRIAL",
      "engine":"PaddleOCRVL native pipeline v1.6, use_layout_detection=False",
      "status":"STARTED","inference_executed":False,"results":[],
      "scope":"tiny eight synthetic images, no oracle used by inference",
      "source_attestation":"NOT_TRUSTED","financial_decision":"NOT_AUTHORIZED"}
    save(o/"paddle_attempt.json",report)
    try:
        import importlib.metadata
        import huggingface_hub
        import paddle
        from huggingface_hub import snapshot_download
        from paddleocr import PaddleOCRVL
        report["dependency_versions"]={
          p:importlib.metadata.version(p) for p in ("paddlepaddle","paddleocr","huggingface-hub")}
        root=o/"model_cache"
        root.mkdir(exist_ok=True)
        before=time.monotonic()
        loc=snapshot_download(repo_id=MODEL,revision=REVISION,local_dir=str(root),
          allow_patterns=["*.json","*.py","*.jinja","*.model","*.txt","*.yml","*.yaml","*.safetensors"],
          max_workers=1)
        weight=Path(loc)/"model.safetensors"
        if not weight.exists():raise RuntimeError("PINNED_WEIGHTS_MISSING")
        h=hashlib.sha256()
        with weight.open("rb") as f:
            while chunk:=f.read(8*1024*1024):h.update(chunk)
        report["weight_sha256_actual"]=h.hexdigest()
        report["weight_bytes_actual"]=weight.stat().st_size
        report["download_seconds"]=round(time.monotonic()-before,3)
        save(o/"paddle_attempt.json",report)
        model=PaddleOCRVL(pipeline_version="v1.6",use_layout_detection=False,
                           vl_rec_model_dir=str(root),device="cpu")
        report["model_initialized"]=True
        # Test the same PNGs, independently checked against the locked manifest.
        for doc in manifest:
            file=ds/doc["image"];data=file.read_bytes()
            if hashlib.sha256(data).hexdigest()!=doc["image_sha256"]:
                raise RuntimeError("SAME_ASSET_SHA_MISMATCH")
            t=time.monotonic()
            output=model.predict(input=str(file))
            serialized=[]
            for res in output:
                try:
                    raw=res.json
                    if callable(raw):raw=raw()
                except Exception as exc:raw={"serialization_failure":repr(exc)}
                serialized.append(raw)
            elapsed=round(time.monotonic()-t,3)
            report["inference_executed"]=True
            report["results"].append({"id":doc["id"],"original_sha256":doc["image_sha256"],
                                      "runtime_seconds":elapsed,"raw":serialized,
                                      "field_values":None,"evidence_bboxes":None,
                                      "reason":"No independently qualified field and cell association adapter for VL output"})
            save(o/"paddle_attempt.json",report)
        report["status"]="INFERENCE_RUN_UNSTRUCTURED_OUTPUT_NEEDS_FIELD_PROVENANCE"
    except BaseException as exc:
        report["status"]="FAILED_OR_ABORTED_NO_QUALIFIED_COMPARISON"
        report["error_type"]=type(exc).__name__
        report["error_message"]=str(exc)[-1000:]
        report["traceback"]=traceback.format_exc()[-3500:]
    finally:
        report["peak_rss_mb"]=round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,2)
        report["peak_gpu_vram_mb"]=None
        report["python"]=platform.python_version()
        save(o/"paddle_attempt.json",report)
        print(json.dumps({"status":report["status"],"executed":report["inference_executed"],
                          "sample_count":len(report["results"]),"failure":report.get("error_type")}))
if __name__=="__main__":main()
