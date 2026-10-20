#!/usr/bin/env python3
"""Preflight large VLM benchmark: refuse expensive weights under unsafe free limits.
No model download or inference occurs on insufficient resources.
"""
import argparse, json, os, platform, shutil, subprocess
from pathlib import Path

PIN={
 "model":"PaddlePaddle/PaddleOCR-VL-1.6",
 "revision":"676e2aad67375fec9c7dcc9740babec7a0d0d110",
 "model_card_license":"apache-2.0",
 "upstream_usage":"PaddleOCRVL(pipeline_version='v1.6')",
 "weight_repository_reported_gb":1.93,
 "model_weight_SHA256":"NOT_VERIFIED_NO_DOWNLOAD",
 "pipeline_dependency_note":"Official pipeline also requires PP-DocLayoutV3 and PaddlePaddle; not just OCR-VL safetensors",
 "paddleocr_package_version":"NOT_INSTALLED",
 "paddlepaddle_package_version":"NOT_INSTALLED"
}
def resource_probe():
    memtotal=memavail=None
    p=Path("/proc/meminfo")
    if p.exists():
        table={}
        for l in p.read_text().splitlines():
            k,_,v=l.partition(":")
            try:table[k]=int(v.strip().split()[0])/1024**2
            except (ValueError,IndexError):pass
        memtotal=round(table.get("MemTotal",0),3)
        memavail=round(table.get("MemAvailable",0),3)
    gpu=shutil.which("nvidia-smi")
    gpu_info=None
    if gpu:
        z=subprocess.run([gpu,"--query-gpu=name,memory.free","--format=csv,noheader,nounits"],
                         capture_output=True,text=True,timeout=5)
        if z.returncode==0:gpu_info=z.stdout.strip()
    return {"memory_total_gib":memtotal,"memory_available_gib":memavail,
            "gpu_visible":bool(gpu_info),"gpu_inventory":gpu_info,
            "python":platform.python_version(),"host":platform.platform(),
            "free_disk_gib":round(shutil.disk_usage(".").free/1024**3,3)}
def main():
    p=argparse.ArgumentParser();p.add_argument("--output",required=True)
    a=p.parse_args();resources=resource_probe()
    # A conservative project policy, NOT an experimentally demonstrated hard model minimum.
    # Never download 1.92GB weights to an unqualified low-memory CPU GitHub runner.
    cpu_ok=(resources["memory_available_gib"] or 0)>=12 and resources["free_disk_gib"]>=10
    gpu_ok=resources["gpu_visible"] and resources["free_disk_gib"]>=10
    can_run=cpu_ok or gpu_ok
    result={"engine":"PaddleOCR-VL-1.6","model":PIN,"resources":resources,
            "resource_policy":{"cpu_min_available_gib":12,"min_disk_gib":10,
               "threshold_type":"conservative_self_imposed_budget_not_official_model_minimum"},
            "execution_performed":False,
            "weights_downloaded":False,
            "predictions":None,"metrics":None,
            "status":"NOT_RUN_MODEL_RUNTIME_UNQUALIFIED" if can_run else "NOT_RUN_RESOURCE_PRECHECK",
            "reason":"Preflight only: no pinned installed PaddlePaddle runtime or independently verified weight checksum"
              if can_run else "This free CPU runner lacks the conservative memory/disk budget for a 1.92 GB VL checkpoint plus layout detector and runtime.",
            "cross_engine_comparison_eligible":False}
    Path(a.output).write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({"engine":result["engine"],"status":result["status"],
                      "resources":resources},indent=2))
if __name__=="__main__":main()
