"""Build/verify a local release *candidate* with audited SHA-256 inventory.

No secrets, patient data or institutional approvals are copied into the candidate.
This does not sign, publish, upload or mark a release as accepted.
"""
import argparse
import json
import shutil
import subprocess
from pathlib import Path

from mcias.release_g9 import ReleaseBlocked, create_manifest, verify_manifest, encode_receipt

ALLOWED_REPO_FILES = (
    "deploy/Dockerfile",
    "deploy/nginx.conf",
    "deploy/compose.g9.yml",
    "docs/G9_RELEASE.md",
    "docs/G9_OPERATOR_TRAINING_AR.md",
    "docs/G9_DISASTER_RECOVERY_AR.md",
    "docs/G0_G9_ACCEPTANCE_TRACKER.md",
    "docs/FRONTEND_INSTALLATION.md",
    "docs/FRONTEND_ROUTE_API_MATRIX.md",
    "docs/INTEGRATED_CANDIDATE_HANDOFF_AR.md",
    "GATE_STATUS.md",
)

def _copy(source, target):
    if source.is_symlink() or not source.is_file():
        raise ReleaseBlocked("release source file unavailable or symbolic link")
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(source,target)

def build(root: Path, output: Path, wheels: Path, sha: str):
    root=root.resolve()
    if not wheels.is_dir():
        raise ReleaseBlocked("prebuilt reviewed wheelhouse directory required")
    entries=sorted(wheels.glob("*.whl"))
    if not entries or not any(wheel.name.startswith("mcias-") for wheel in entries):
        raise ReleaseBlocked("wheelhouse must contain MCIAS and its approved dependencies")
    if output.exists() and any(output.iterdir()):
        raise ReleaseBlocked("release candidate directory must start empty")
    output.mkdir(parents=True,exist_ok=True)
    paths={}
    for name in ALLOWED_REPO_FILES:
        source=root/name
        target=output/name
        _copy(source,target)
        paths[name]=target
    for entry in entries:
        name="wheels/"+entry.name
        target=output/name
        _copy(entry,target)
        paths[name]=target
    manifest=create_manifest(paths,sha)
    (output/"RECEIPT.json").write_bytes(encode_receipt(manifest))
    verify_manifest(manifest,output)
    return manifest

def verify(directory: Path):
    receipt=directory/"RECEIPT.json"
    if receipt.is_symlink() or not receipt.is_file() or receipt.stat().st_size>1024*1024:
        raise ReleaseBlocked("missing or oversized release receipt")
    manifest=json.loads(receipt.read_text("utf-8"))
    verify_manifest(manifest,directory)
    return manifest

def main(argv=None):
    parser=argparse.ArgumentParser(description="MCIAS G9 offline candidate receipt builder")
    commands=parser.add_subparsers(dest="command",required=True)
    maker=commands.add_parser("build")
    maker.add_argument("--repo",type=Path,default=Path("."))
    maker.add_argument("--wheels",type=Path,required=True)
    maker.add_argument("--output",type=Path,required=True)
    maker.add_argument("--commit",required=True,
                       help="full 40-digit SHA from reviewed Git checkout")
    checker=commands.add_parser("verify")
    checker.add_argument("--directory",type=Path,required=True)
    args=parser.parse_args(argv)
    try:
        if args.command=="build":
            sha=subprocess.check_output(["git","rev-parse","HEAD"],cwd=args.repo,
                                        text=True,stderr=subprocess.DEVNULL).strip()
            if args.commit!=sha:
                raise ReleaseBlocked("declared release SHA does not match current checkout")
            result=build(args.repo,args.output,args.wheels,args.commit)
        else:
            result=verify(args.directory)
        print(json.dumps({"result":"HASH_VERIFIED_NOT_APPROVED",
                          "commit_sha":result["commit_sha"],
                          "artifacts":len(result["artifacts"]),
                          "receipt_sha256":result["sha256"]},sort_keys=True))
        return 0
    except (ReleaseBlocked, OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"result":"BLOCKED","reason":str(exc)}))
        return 2

if __name__=="__main__":
    raise SystemExit(main())
