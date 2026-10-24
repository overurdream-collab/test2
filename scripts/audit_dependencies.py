"""Audit every installed external distribution, including transitive/tool deps.

Only this repository's editable mcias package is omitted from the PyPI query.
Its direct_url.json must attest a local editable source; all other packages are
queried at their actual installed versions and any audit error fails the job.
"""
from importlib import metadata
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from urllib.parse import unquote, urlsplit


def main():
    repository = Path(__file__).resolve().parents[1]
    versions = {}
    excluded = 0
    for distribution in metadata.distributions():
        name = distribution.metadata["Name"]
        key = re.sub(r"[-_.]+", "-", name).lower()
        if key == "mcias":
            direct = json.loads(distribution.read_text("direct_url.json") or "{}")
            location = urlsplit(direct.get("url", ""))
            editable = (location.scheme == "file" and not location.netloc
                and direct.get("dir_info", {}).get("editable")
                and Path(unquote(location.path)).resolve() == repository)
            # Running inside a setuptools source checkout may expose its local
            # egg-info as well as the installed editable dist-info.
            source_metadata = (not direct
                and Path(distribution.locate_file("")).resolve() == repository
                and (repository / "mcias" / "__init__.py").is_file())
            if not (editable or source_metadata):
                raise RuntimeError("mcias must be this repository's local editable distribution")
            excluded += 1
            continue
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", name):
            raise RuntimeError("invalid external distribution name")
        if key in versions and versions[key] != distribution.version:
            raise RuntimeError("conflicting installed external versions")
        versions[key] = distribution.version
    if excluded < 1:
        raise RuntimeError("local mcias source distribution required")
    print(f"Auditing {len(versions)} installed external packages; local editable mcias source is checked separately.", flush=True)
    with tempfile.TemporaryDirectory(prefix="mcias-dependency-audit-") as temporary:
        requirements = Path(temporary) / "resolved-external.txt"
        requirements.write_text("".join(f"{name}=={version}\n" for name, version in sorted(versions.items())))
        # All transitive dependencies are explicitly enumerated above. Disable
        # resolution so the scanned versions are exactly those installed.
        return subprocess.run([sys.executable, "-m", "pip_audit", "--strict",
            "--no-deps", "--disable-pip", "--cache-dir", str(Path(temporary) / "cache"),
            "-r", str(requirements), *sys.argv[1:]], check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
