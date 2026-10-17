"""Run REAL offline open-weight inference on synthetic A1 records only.

Not a mock. Requires a locally installed llama_cpp backend and GGUF weights.
Optional download is explicit, exclusively for public MODEL weights; no patient data
or claim payloads are transmitted. Output records actual inference provenance.
"""
import argparse
from hashlib import sha256
import json
import os
import resource
from time import perf_counter
from pathlib import Path

from mcias.agents.invoice_integrity import analyze
from tests.a1.synthetic_cases import case


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model-file", default="")
    ap.add_argument("--download-public-model", action="store_true")
    ap.add_argument("--output", default="a1-real-model-evidence.json")
    args = ap.parse_args()
    repo, revision, filename = None, None, None
    path = Path(args.model_file) if args.model_file else None
    if args.download_public_model:
        from huggingface_hub import HfApi, hf_hub_download
        repo = "Qwen/Qwen3-0.6B-GGUF"
        api = HfApi()
        info = api.model_info(repo, files_metadata=False)
        revision = info.sha
        filenames = sorted(p.rfilename for p in info.siblings
                           if p.rfilename.lower().endswith(".gguf"))
        preferred = [p for p in filenames if "q4_k_m" in p.lower()]
        if not preferred:
            preferred = [p for p in filenames if "q8_0" in p.lower()]
        if len(preferred) != 1:
            raise RuntimeError("Could not resolve a unique official Qwen GGUF: " + repr(filenames))
        filename = preferred[0]
        path = Path(hf_hub_download(repo_id=repo, filename=filename, revision=revision))
    if not path or not path.is_file():
        raise RuntimeError("No downloaded/local GGUF model available; cannot claim AI inference.")
    from llama_cpp import Llama
    model_sha = sha256(path.read_bytes()).hexdigest()
    model_id = (repo + "@" + revision + "/" + filename) if repo else path.name + "@sha256:" + model_sha
    llm = Llama(model_path=str(path), n_ctx=2048, n_threads=2, n_gpu_layers=0,
                verbose=False)
    generated = []
    def local_model(system, input_text):
        result = llm.create_chat_completion(
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": "/no_think\n" + input_text}],
            max_tokens=220, temperature=0.0, response_format={"type": "json_object"})
        text = result["choices"][0]["message"].get("content") or ""
        usage = result.get("usage", {})
        generated.append({"response": text[:3000], "usage": usage,
                          "finish_reason": result["choices"][0].get("finish_reason")})
        return text

    records = []
    for kind in ["clean", "prompt_injection", "contradiction_text"]:
        bundle = case("ocr_unverified" if kind == "contradiction_text" else kind)
        if kind == "contradiction_text":
            bundle["documents"][0]["text"] = "Signed report: only ONE LAB-A test was performed. The invoice lists TWO LAB-A tests."
        if bundle.get("synthetic") is not True:
            raise RuntimeError("Model probe only accepts declared synthetic fixtures")
        start = perf_counter()
        output = analyze(bundle, model=local_model, model_id=model_id)
        records.append({"case": kind, "latency_seconds": round(perf_counter()-start, 4),
                        "model_status": output["model_status"],
                        "model_finding_types": [x["finding_type"] for x in output["findings"] if x["engine"] == "model"],
                        "result_fingerprint": output["output_fingerprint"]})
    model_gold = {"clean": False, "prompt_injection": False, "contradiction_text": True}
    for rec in records:
        rec["expert_synthetic_label_discrepancy"] = model_gold[rec["case"]]
        rec["proposed_discrepancy"] = bool(rec["model_finding_types"])
    report = {"synthetic_only": True, "actual_model_invocations": len(generated),
              "model_id": model_id, "model_sha256": model_sha,
              "model_file_size_bytes": path.stat().st_size, "inferences": generated,
              "cases": records, "peak_rss_kib_os": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
              "note": "A real small model smoke test, NOT evidence of production accuracy or 8B quality."}
    Path(args.output).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    if len(generated) != 3 or any(not g["response"] for g in generated):
        raise RuntimeError("Real inference was not proven")
    if any(r["model_status"] != "INFERRED_VALIDATED" for r in records):
        raise RuntimeError("Real model output could not be evidence-validated; probe FAIL CLOSED")
    print(json.dumps({k: v for k, v in report.items() if k != "inferences"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
