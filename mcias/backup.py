"""Authenticated encrypted backup archive helpers. PostgreSQL dump is an external input."""
import hashlib
import io
import json
import os
import tarfile
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

MAGIC = b"MCIASBACKUP1"

def encrypt_bundle(entries: dict[str, bytes], key: bytes) -> bytes:
    if len(key) != 32:
        raise ValueError("32-byte key required")
    stream = io.BytesIO()
    manifest = {name: hashlib.sha256(data).hexdigest() for name, data in entries.items()}
    with tarfile.open(fileobj=stream, mode="w") as tar:
        for name, data in {**entries, "manifest.json": json.dumps(manifest).encode()}.items():
            if not name or name.startswith("/") or ".." in Path(name).parts:
                raise ValueError("unsafe archive path")
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    nonce = os.urandom(12)
    return MAGIC + nonce + AESGCM(key).encrypt(nonce, stream.getvalue(), MAGIC)

def decrypt_bundle(blob: bytes, key: bytes) -> dict[str, bytes]:
    if not blob.startswith(MAGIC):
        raise ValueError("invalid backup format")
    offset = len(MAGIC)
    payload = AESGCM(key).decrypt(blob[offset:offset+12], blob[offset+12:], MAGIC)
    result = {}
    with tarfile.open(fileobj=io.BytesIO(payload), mode="r:") as tar:
        for member in tar:
            if not member.isfile() or member.name.startswith("/") or ".." in Path(member.name).parts or member.name in result:
                raise ValueError("unsafe archive member")
            result[member.name] = tar.extractfile(member).read()
    manifest = json.loads(result.pop("manifest.json"))
    if set(result) != set(manifest) or any(hashlib.sha256(v).hexdigest() != manifest[k] for k,v in result.items()):
        raise ValueError("backup checksum mismatch")
    return result
