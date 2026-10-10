"""Source handoff contains committed engineering files, never workspace credentials."""
import hashlib
import json
import subprocess
import tarfile

import pytest

from scripts.build_integrated_handoff import package
from scripts.g9_release import ALLOWED_REPO_FILES, verify
from mcias.release_g9 import ReleaseBlocked

@pytest.fixture
def checkout(tmp_path):
    root=tmp_path/'repo';root.mkdir()
    subprocess.run(['git','init','-q',str(root)],check=True)
    (root/'.gitignore').write_text('.env\nprivate/\n')
    for name in ALLOWED_REPO_FILES:
        path=root/name;path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text('SYNTHETIC ENGINEERING FIXTURE '+name)
    subprocess.run(['git','add','.'],cwd=root,check=True)
    subprocess.run(['git','-c','user.name=Synthetic','-c','user.email=synthetic@example.invalid','commit','-qm','synthetic'],cwd=root,check=True)
    wheels=tmp_path/'wheels';wheels.mkdir()
    (wheels/'mcias-0.1.0-py3-none-any.whl').write_bytes(b'synthetic wheel fixture')
    return root,wheels,tmp_path/'handoff'

def test_handoff_uses_commit_archive_and_omits_ignored_credentials(checkout):
    root,wheels,output=checkout
    (root/'.env').write_text('SYNTHETIC_SECRET_NOT_FOR_DISTRIBUTION')
    (root/'private').mkdir();(root/'private'/'patient.csv').write_text('SYNTHETIC_PRIVATE_SOURCE')
    package(root,wheels,output)
    manifest=json.loads((output/'HANDOFF.json').read_text())
    assert manifest['acceptance']=='OPEN_NOT_AUTHORIZED_FOR_PRODUCTION'
    assert manifest['commit_sha']==subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
    for name,sha in manifest['sha256'].items():
        assert hashlib.sha256((output/name).read_bytes()).hexdigest()==sha
    with tarfile.open(output/'mcias-source.tar.gz') as archive:
        assert 'mcias/docs/INTEGRATED_CANDIDATE_HANDOFF_AR.md' in archive.getnames()
        assert not any('.env' in name or '/private/' in name for name in archive.getnames())
    verify(output/'candidate')

def test_handoff_rejects_dirty_checkout(checkout):
    root,wheels,output=checkout
    (root/'GATE_STATUS.md').write_text('unreviewed modification')
    with pytest.raises(ReleaseBlocked,match='clean'):
        package(root,wheels,output)
    assert not output.exists()

def test_handoff_rejects_committed_private_key(checkout):
    root,wheels,output=checkout
    (root/'accidental.key').write_text('synthetic private key fixture')
    subprocess.run(['git','add','accidental.key'],cwd=root,check=True)
    subprocess.run(['git','-c','user.name=Synthetic','-c','user.email=synthetic@example.invalid','commit','-qm','accident fixture'],cwd=root,check=True)
    with pytest.raises(ReleaseBlocked,match='forbidden'):
        package(root,wheels,output)
    assert not output.exists()


def test_handoff_accepts_only_reviewed_public_synthetic_fixture(checkout):
    from pathlib import Path
    root,wheels,output=checkout
    source=Path(__file__).resolve().parents[1]/'mcias/seed/data/workspace-v1.json'
    target=root/'mcias/seed/data/workspace-v1.json';target.parent.mkdir(parents=True)
    target.write_bytes(source.read_bytes())
    subprocess.run(['git','add','.'],cwd=root,check=True)
    subprocess.run(['git','-c','user.name=Synthetic','-c','user.email=synthetic@example.invalid','commit','-qm','public fixture'],cwd=root,check=True)
    package(root,wheels,output)
    with tarfile.open(output/'mcias-source.tar.gz') as archive:
        assert 'mcias/mcias/seed/data/workspace-v1.json' in archive.getnames()


def test_handoff_rejects_unreviewed_public_fixture_content(checkout):
    root,wheels,output=checkout
    target=root/'mcias/seed/data/workspace-v1.json';target.parent.mkdir(parents=True)
    target.write_text('{"private":"SYNTHETIC_UNREVIEWED"}')
    subprocess.run(['git','add','.'],cwd=root,check=True)
    subprocess.run(['git','-c','user.name=Synthetic','-c','user.email=synthetic@example.invalid','commit','-qm','unreviewed fixture'],cwd=root,check=True)
    with pytest.raises(ReleaseBlocked,match='hash review'):
        package(root,wheels,output)


def test_handoff_still_rejects_other_data_paths(checkout):
    root,wheels,output=checkout
    target=root/'data/client.json';target.parent.mkdir(parents=True)
    target.write_text('SYNTHETIC_PRIVATE_TEST')
    subprocess.run(['git','add','.'],cwd=root,check=True)
    subprocess.run(['git','-c','user.name=Synthetic','-c','user.email=synthetic@example.invalid','commit','-qm','private fixture'],cwd=root,check=True)
    with pytest.raises(ReleaseBlocked,match='forbidden'):
        package(root,wheels,output)
