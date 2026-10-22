"""G9 reproducible release receipt for offline/on-premise installation.

Manifest is SHA-256 integrity metadata, *not* an organization approval or signature.
No patient data, environment variables, or secrets should ever enter this manifest.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath

MAX_ASSETS = 128
MAX_FILE_BYTES = 64 * 1024 * 1024
ALLOWED_EXTENSIONS = frozenset({".whl", ".toml", ".md", ".yml", ".yaml", ".sh", ".sql", ".conf", ".txt"})
MANIFEST_SCHEMA = "mcias-offline-release-receipt-v1"

class ReleaseBlocked(ValueError):
    pass

def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def encode_receipt(value: dict) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                       allow_nan=False) + "\n").encode("utf-8")

def _validate_path(name: str) -> None:
    if (not isinstance(name, str) or not 1 <= len(name) <= 200 or "\\" in name
        or name.startswith("/") or name.startswith(".") or ":" in name
        or not all(part not in ("", ".", "..") for part in name.split("/"))
        or (PurePosixPath(name).suffix.lower() not in ALLOWED_EXTENSIONS
            and name != "deploy/Dockerfile")):
        raise ReleaseBlocked("unsafe artifact name or extension")

def artifact_record(path: Path, logical_name: str) -> dict:
    _validate_path(logical_name)
    if path.is_symlink() or not path.is_file():
        raise ReleaseBlocked("artifact is not a regular file")
    size = path.stat().st_size
    if not 0 < size <= MAX_FILE_BYTES:
        raise ReleaseBlocked("artifact size exceeds bounded release policy")
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    if path.stat().st_size != size:
        raise ReleaseBlocked("release artifact changed during hashing")
    return {"path": logical_name, "size": size, "sha256": digest.hexdigest()}

def create_manifest(artifacts: dict[str, Path], commit_sha: str,
                    migration_head: str = "0019_reference_dataset_v1") -> dict:
    if (not isinstance(commit_sha, str) or len(commit_sha) != 40
        or any(c not in "0123456789abcdef" for c in commit_sha)):
        raise ReleaseBlocked("a verified full git commit SHA is mandatory")
    if not 1 <= len(artifacts) <= MAX_ASSETS:
        raise ReleaseBlocked("release requires bounded nonempty artifact list")
    items = [artifact_record(Path(path), name) for name, path in sorted(artifacts.items())]
    manifest = {"schema": MANIFEST_SCHEMA, "commit_sha": commit_sha,
                "migration_head": migration_head, "artifacts": items,
                "acceptance": "OPEN_NOT_AUTHORIZED_FOR_PRODUCTION"}
    manifest["sha256"] = digest_bytes(encode_receipt(manifest))
    return manifest

def verify_manifest(manifest: dict, directory: Path) -> bool:
    if type(manifest) is not dict or set(manifest) != {
        "schema", "commit_sha", "migration_head", "artifacts",
        "acceptance", "sha256"}:
        raise ReleaseBlocked("invalid release receipt schema")
    content = {k: v for k, v in manifest.items() if k != "sha256"}
    if (manifest["schema"] != MANIFEST_SCHEMA
        or manifest["acceptance"] != "OPEN_NOT_AUTHORIZED_FOR_PRODUCTION"
        or manifest["sha256"] != digest_bytes(encode_receipt(content))):
        raise ReleaseBlocked("release receipt integrity or acceptance marker invalid")
    if not isinstance(manifest["artifacts"], list) or not 1 <= len(manifest["artifacts"]) <= MAX_ASSETS:
        raise ReleaseBlocked("invalid release artifact inventory")
    if Path(directory).is_symlink() or not Path(directory).is_dir():
        raise ReleaseBlocked("artifact root not a regular directory")
    seen = set()
    for item in manifest["artifacts"]:
        if type(item) is not dict or set(item) != {"path", "size", "sha256"}:
            raise ReleaseBlocked("invalid release artifact entry")
        name = item["path"]
        _validate_path(name)
        if name in seen:
            raise ReleaseBlocked("duplicate release artifact")
        seen.add(name)
        artifact = Path(directory) / name
        root = Path(directory).resolve()
        segments = PurePosixPath(name).parts
        parent = root
        for segment in segments:
            parent = parent / segment
            if parent.is_symlink():
                raise ReleaseBlocked("symlinked release component forbidden")
        if artifact.resolve().is_relative_to(root) is False:
            raise ReleaseBlocked("release artifact escapes selected directory")
        if artifact_record(artifact, name) != item:
            raise ReleaseBlocked("release artifact checksum or size mismatch")
    return True
