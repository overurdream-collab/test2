"""Bounded authenticated backup archive helpers for local on-premise restore.

A bundle contains an external PostgreSQL dump and encrypted source blobs.
This in-memory proof-of-concept is intentionally capped and is NOT a substitute
for streaming production backups, off-site custody, or approved retention.
"""
import hashlib
import io
import json
import os
import tarfile
from pathlib import PurePosixPath

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

MAGIC=b"MCIASBACKUP1"
MAX_ENTRIES=2048
MAX_BUNDLE_BYTES=128 * 1024 * 1024  # engineering safety cap; NOT approved production SLA
MAX_FILENAME=240
MANIFEST_NAME="manifest.json"

def _safe_name(name):
    if (type(name) is not str or not 1 <= len(name) <= MAX_FILENAME
        or name.startswith(("/", ".")) or "\\" in name or ":" in name
        or any(p in ("", ".", "..") for p in name.split("/"))
        or PurePosixPath(name).is_absolute() or name == MANIFEST_NAME):
        raise ValueError("unsafe backup member")
    return True

def _verify_limits(entries):
    if type(entries) is not dict or not 1 <= len(entries) <= MAX_ENTRIES:
        raise ValueError("invalid backup entry count")
    total=0
    for name, value in entries.items():
        _safe_name(name)
        if type(value) is not bytes:
            raise ValueError("binary backup entries required")
        total += len(value)
        if total > MAX_BUNDLE_BYTES:
            raise ValueError("backup exceeds bounded size")
    return total

def encrypt_bundle(entries: dict[str, bytes], key: bytes) -> bytes:
    if len(key) != 32:
        raise ValueError("32-byte key required")
    total=_verify_limits(entries)
    stream=io.BytesIO()
    manifest={name: hashlib.sha256(data).hexdigest() for name,data in entries.items()}
    manifest_bytes=json.dumps(manifest,sort_keys=True,separators=(",",":")).encode("utf-8")
    if total+len(manifest_bytes) > MAX_BUNDLE_BYTES:
        raise ValueError("backup metadata exceeds bounded size")
    with tarfile.open(fileobj=stream,mode="w") as tar:
        for name,data in {**entries,MANIFEST_NAME:manifest_bytes}.items():
            info=tarfile.TarInfo(name)
            info.size=len(data)
            info.mode=0o600
            tar.addfile(info,io.BytesIO(data))
    plaintext=stream.getvalue()
    if len(plaintext) > MAX_BUNDLE_BYTES + 1024 * 1024:
        raise ValueError("archive exceeds encrypted memory safety cap")
    nonce=os.urandom(12)
    return MAGIC + nonce + AESGCM(key).encrypt(nonce,plaintext,MAGIC)

def decrypt_bundle(blob: bytes, key: bytes) -> dict[str,bytes]:
    if len(key)!=32:
        raise ValueError("32-byte key required")
    if not isinstance(blob,bytes) or len(blob)>MAX_BUNDLE_BYTES+1024*1024+len(MAGIC)+28:
        raise ValueError("oversized or invalid encrypted backup")
    if not blob.startswith(MAGIC) or len(blob)<len(MAGIC)+28:
        raise ValueError("invalid backup format")
    offset=len(MAGIC)
    payload=AESGCM(key).decrypt(blob[offset:offset+12],blob[offset+12:],MAGIC)
    if len(payload)>MAX_BUNDLE_BYTES+1024*1024:
        raise ValueError("oversized backup content")
    result={}
    manifest_bytes=None
    total=0
    count=0
    with tarfile.open(fileobj=io.BytesIO(payload),mode="r:") as tar:
        for member in tar:
            if not member.isfile() or member.issym() or member.islnk():
                raise ValueError("invalid backup member type")
            count += 1
            if count > MAX_ENTRIES+1:
                raise ValueError("backup member count exceeded")
            if member.name==MANIFEST_NAME:
                if manifest_bytes is not None:
                    raise ValueError("duplicate manifest")
            else:
                _safe_name(member.name)
                if member.name in result:
                    raise ValueError("duplicate backup entry")
            total += member.size
            if member.size<0 or total > MAX_BUNDLE_BYTES:
                raise ValueError("backup extraction size exceeded")
            data=tar.extractfile(member).read()
            if len(data)!=member.size:
                raise ValueError("truncated backup entry")
            if member.name==MANIFEST_NAME:
                manifest_bytes=data
            else:
                result[member.name]=data
    if manifest_bytes is None:
        raise ValueError("backup manifest missing")
    try:
        manifest=json.loads(manifest_bytes)
    except (TypeError,ValueError) as exc:
        raise ValueError("invalid backup manifest") from exc
    if (type(manifest) is not dict or set(result) != set(manifest)
        or any(type(checksum) is not str or
               hashlib.sha256(value).hexdigest()!=manifest[name]
               for name,value in result.items())):
        raise ValueError("backup checksum mismatch")
    return result
