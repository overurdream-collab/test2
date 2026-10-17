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
                           if p.rfilename.lower().endswith(".gguf") and "q4_k_m" in p.rfilename.lower())
        if len(filenames) != 1:
            raise RuntimeError("Expected exactly one Q4_K_M GGUF from official Qwen repo: " + repr(filenames))
        filename = filenames[0]
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
            max_tokens=220, temperature=0.0)
        text = result["choices"][0]["message"].get("content") or ""
        usage = result.get("usage", {})
        generated.append({"response": text[:3000], "usage": usage,
                          "finish_reason": result["choices"][0].get("finish_reason")})
        return text

    records = []
    for kind in ["clean", "prompt_injection"]:
        bundle = case(kind)
        if bundle.get("synthetic") is not True:
            raise RuntimeError("Model probe only accepts declared synthetic fixtures")
        start = perf_counter()
        output = analyze(bundle, model=local_model, model_id=model_id)
        records.append({"case": kind, "latency_seconds": round(perf_counter()-start, 4),
                        "model_status": output["model_status"],
                        "model_finding_types": [x["finding_type"] for x in output["findings"] if x["engine"] == "model"],
                        "result_fingerprint": output["output_fingerprint"]})
    report = {"synthetic_only": True, "actual_model_invocations": len(generated),
              "model_id": model_id, "model_sha256": model_sha,
              "model_file_size_bytes": path.stat().st_size, "inferences": generated,
              "cases": records, "peak_rss_kib_os": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
              "note": "A real small model smoke test, NOT evidence of production accuracy or 8B quality."}
    if len(generated) != 2 or any(not g["response"] for g in generated):
        raise RuntimeError("Real inference was not proven")
    Path(args.output).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "inferences"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
