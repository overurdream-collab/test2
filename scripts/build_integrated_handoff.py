"""Package a clean reviewed checkout and prebuilt wheels for external synthetic tests.

No workspace/private files are copied. Git archive reads only the committed tree.
Checksums require an independently trusted copy; this grants no acceptance.
"""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.g9_release import build, verify
from mcias.release_g9 import ReleaseBlocked


def digest(path):
    result = hashlib.sha256()
    with path.open('rb') as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()


PUBLIC_SYNTHETIC_FIXTURES = {"mcias/seed/data/workspace-v1.json": "f1275a62d82a2e8cc19c3c1d0185fa47f415f91784c5e338f4ebb94236cce510"}


def package(root, wheels, output):
    root = root.resolve()
    if subprocess.check_output(['git','status','--porcelain'],cwd=root,text=True).strip():
        raise ReleaseBlocked('Commit reviewed changes before packaging; checkout must be clean')
    sha = subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
    names = subprocess.check_output(['git','ls-tree','-r','--name-only',sha],cwd=root,text=True).splitlines()
    for name in names:
        if name in PUBLIC_SYNTHETIC_FIXTURES:
            content = subprocess.check_output(["git", "show", sha + ":" + name], cwd=root)
            if hashlib.sha256(content).hexdigest() != PUBLIC_SYNTHETIC_FIXTURES[name]:
                raise ReleaseBlocked("Public synthetic fixture changed without hash review")
            continue
        path = Path(name.lower())
        if (name.lower().endswith(('.key','.pem','.p12','.pfx'))
            or any(part in {'private','uploads','backups','data','.e2e-output','node_modules'} for part in path.parts)
            or any(part.startswith('.env') and part != '.env.example' for part in path.parts)):
            raise ReleaseBlocked('Committed tree contains a forbidden private/data path')
    if output.exists():
        raise ReleaseBlocked('Handoff output must be a new directory')
    output.mkdir(parents=True)
    receipt = build(root,output/'candidate',wheels,sha)
    archive = output/'mcias-source.tar.gz'
    subprocess.run(['git','archive','--format=tar.gz','--prefix=mcias/','--output',str(archive.resolve()),sha],cwd=root,check=True)
    inventory = [archive] + sorted(p for p in (output/'candidate').rglob('*') if p.is_file())
    manifest = {'schema':'mcias-integrated-test-handoff-v1','commit_sha':sha,
                'acceptance':'OPEN_NOT_AUTHORIZED_FOR_PRODUCTION',
                'wheel_target':'Python 3.12 / Linux x86_64; validate compatibility on target',
                'candidate_receipt_sha256':receipt['sha256'],
                'sha256':{p.relative_to(output).as_posix():digest(p) for p in inventory}}
    (output/'HANDOFF.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (output/'SHA256SUMS').write_text(''.join(value+'  '+name+'\n' for name,value in manifest['sha256'].items()))
    verify(output/'candidate')
    print(json.dumps({'commit_sha':sha,'artifact_count':len(inventory),
                      'source_sha256':manifest['sha256']['mcias-source.tar.gz'],
                      'production_accepted':False},indent=2))


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--repo',type=Path,default=Path('.'))
    parser.add_argument('--wheelhouse',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    package(args.repo,args.wheelhouse,args.output)
