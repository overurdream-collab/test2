"""Execute real, local open-weight Qwen3-8B inference on synthetic A1 fixtures.

No paid inference endpoints or external claim payloads. Model WEIGHTS alone
are downloaded from official Qwen repository. Ground truth is authored by
humans in separate tests/a1/model_cases.py and never sent to the model.
"""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import resource
from time import perf_counter
from statistics import mean

from mcias.agents.invoice_integrity import analyze
from tests.a1.model_cases import CASES, model_case
from tests.a1.holdout_cases import HOLDOUT, holdout_case


def stream_sha256(path):
    checksum = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            checksum.update(block)
    return checksum.hexdigest()


def download_official_weights(repo):
    from huggingface_hub import HfApi, hf_hub_download
    if repo not in {"Qwen/Qwen3-8B-GGUF", "Qwen/Qwen3-4B-GGUF"}:
        raise ValueError("Only approved official public Qwen repos accepted")
    info = HfApi().model_info(repo, files_metadata=False)
    revision = info.sha
    filenames = [p.rfilename for p in info.siblings if p.rfilename.lower().endswith(".gguf")]
    preferred = sorted(p for p in filenames if p.lower().endswith("-q4_k_m.gguf"))
    if len(preferred) != 1:
        raise RuntimeError("Cannot resolve a single Q4_K_M official model file: " + repr(preferred))
    path = Path(hf_hub_download(repo_id=repo, filename=preferred[0], revision=revision))
    return path, f"{repo}@{revision}/{preferred[0]}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model-file", default="", help="Use independently obtained GGUF")
    ap.add_argument("--download-public-model", action="store_true")
    ap.add_argument("--repo", default="Qwen/Qwen3-8B-GGUF")
    ap.add_argument("--output", default="a1-real-model-evidence.json")
    args = ap.parse_args()
    if bool(args.model_file) == bool(args.download_public_model):
        raise ValueError("Specify one of --model-file and --download-public-model")
    path, model_id = (download_official_weights(args.repo)
                      if args.download_public_model else (Path(args.model_file), args.model_file))
    if not path.is_file():
        raise RuntimeError("Model weights unavailable: no claim of AI success")
    from llama_cpp import Llama
    model_sha = stream_sha256(path)
    print(f"LOCAL_MODEL_LOADED repo={model_id} sha256={model_sha} size_bytes={path.stat().st_size}", flush=True)
    model = Llama(model_path=str(path), n_ctx=4096, n_threads=4, n_batch=256,
                  n_gpu_layers=0, use_mmap=True, verbose=False, seed=42)
    generated = []
    def call_model(system, input_text):
        start = perf_counter()
        response = model.create_chat_completion(
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": "/no_think\n" + input_text}],
            max_tokens=320, temperature=0.0, response_format={"type": "json_object"})
        raw = response["choices"][0]["message"].get("content") or ""
        generated.append({"raw_response": raw[:6000], "usage": response.get("usage", {}),
                          "finish_reason": response["choices"][0].get("finish_reason"),
                          "generation_seconds": round(perf_counter() - start, 4)})
        return raw

    rows = []
    for cohort, name, truth, bundle_factory in (
        [("development", item[0], item[1], model_case) for item in CASES] +
        [("holdout", item[0], item[1], holdout_case) for item in HOLDOUT]
    ):
        bundle, expected = bundle_factory(name)
        assert expected == truth and bundle.get("synthetic") is True
        start = perf_counter()
        output = analyze(bundle, model=call_model, model_id=f"{model_id}@sha256:{model_sha}")
        findings = [x for x in output["findings"] if x["engine"] == "model"]
        predicted = bool(findings)
        row = {"cohort": cohort, "case": name, "human_synthetic_gold_conflict": truth,
               "predicted_conflict": predicted, "model_status": output["model_status"],
               "model_findings": findings, "input_fingerprint": output["input_fingerprint"],
               "output_fingerprint": output["output_fingerprint"],
               "elapsed_seconds": round(perf_counter()-start, 4)}
        rows.append(row)
        print(json.dumps({"cohort": cohort, "case": name, "truth": truth, "predicted": predicted,
                          "status": output["model_status"], "elapsed_seconds": row["elapsed_seconds"]}), flush=True)
    tp = sum(x["human_synthetic_gold_conflict"] and x["predicted_conflict"] for x in rows)
    tn = sum(not x["human_synthetic_gold_conflict"] and not x["predicted_conflict"] for x in rows)
    fp = sum(not x["human_synthetic_gold_conflict"] and x["predicted_conflict"] for x in rows)
    fn = sum(x["human_synthetic_gold_conflict"] and not x["predicted_conflict"] for x in rows)
    p = tp/(tp+fp) if tp+fp else 0
    recall = tp/(tp+fn) if tp+fn else 0
    def metrics(dataset):
        tp_n = sum(x["human_synthetic_gold_conflict"] and x["predicted_conflict"] for x in dataset)
        tn_n = sum(not x["human_synthetic_gold_conflict"] and not x["predicted_conflict"] for x in dataset)
        fp_n = sum(not x["human_synthetic_gold_conflict"] and x["predicted_conflict"] for x in dataset)
        fn_n = sum(x["human_synthetic_gold_conflict"] and not x["predicted_conflict"] for x in dataset)
        return {"TP": tp_n, "TN": tn_n, "FP": fp_n, "FN": fn_n,
                "precision": tp_n/(tp_n+fp_n) if tp_n+fp_n else 0,
                "recall": tp_n/(tp_n+fn_n) if tp_n+fn_n else 0,
                "cases": len(dataset)}
    holdout = metrics([x for x in rows if x["cohort"] == "holdout"])
    development = metrics([x for x in rows if x["cohort"] == "development"])
    report = {"status": "EXPERIMENTAL_NOT_PRODUCTION_ACCEPTED", "model_id": model_id,
              "model_sha256": model_sha, "model_bytes": path.stat().st_size,
              "ground_truth_file": ["tests/a1/model_cases.py::CASES", "tests/a1/holdout_cases.py::HOLDOUT"],
              "model_real_inferences": len(generated), "metrics": {"TP":tp,"FP":fp,"FN":fn,"TN":tn,
                 "precision":p,"recall":recall, "case_count":len(rows),
                 "mean_claim_seconds":mean(x["elapsed_seconds"] for x in rows),
                 "peak_process_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss},
              "development_metrics": development, "holdout_metrics": holdout,
              "rows": rows, "raw_model_generations": generated,
              "note": "Tiny manually labeled synthetic corpus; independent institutional accuracy gate remains OPEN"}
    Path(args.output).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"model_id": model_id, "metrics": report["metrics"], "holdout_metrics": holdout,
                      "development_metrics": development, "report_file": args.output}), flush=True)
    if len(generated) != len(CASES) + len(HOLDOUT) or any(x["model_status"] != "INFERRED_VALIDATED" for x in rows):
        raise RuntimeError("AI evidence-validated inference gate FAILED")
    if holdout["precision"] < .9 or holdout["recall"] < .9:
        raise RuntimeError("HOLDOUT AI detection quality gate FAILED; do not mark as successful")


if __name__ == "__main__":
    main()
