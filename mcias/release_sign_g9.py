"""Optional G9 offline release-receipt signatures (not a human acceptance).

Operator-controlled Ed25519 keys must be provisioned outside the repository.
Never emit private keys into logs, JSON responses or Docker images.
"""
import hashlib
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey, Ed25519PublicKey,
)
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from mcias.release_g9 import ReleaseBlocked, verify_manifest, encode_receipt

SCHEME = "MCIAS-G9-ED25519-RECEIPT-V1"

def _trusted_private_file(path: Path) -> bytes:
    try:
        if (path.is_symlink() or not path.is_file()
            or path.stat().st_mode & 0o077):
            raise ReleaseBlocked("offline private signing key has unsafe permissions")
        raw=path.read_bytes()
    except OSError as exc:
        raise ReleaseBlocked("offline signing key unavailable") from exc
    if len(raw)!=32:
        raise ReleaseBlocked("Ed25519 private signing seed must be 32 bytes")
    return raw

def sign_release(manifest: dict, root: Path, private_key_path: Path) -> dict:
    verify_manifest(manifest,root)
    seed=_trusted_private_file(private_key_path)
    signer=Ed25519PrivateKey.from_private_bytes(seed)
    public=signer.public_key().public_bytes(Encoding.Raw,PublicFormat.Raw)
    signature=signer.sign(SCHEME.encode("ascii")+b"\x00"+encode_receipt(manifest))
    return {"scheme":SCHEME, "public_key_sha256":hashlib.sha256(public).hexdigest(),
            "signature_hex":signature.hex(), "acceptance":"NOT_A_HUMAN_SIGNOFF"}

def verify_release_signature(manifest:dict, root:Path,
                             statement:dict, trusted_public_key:bytes)->bool:
    verify_manifest(manifest,root)
    if (type(statement) is not dict
        or set(statement)!={"scheme","public_key_sha256","signature_hex","acceptance"}
        or statement["scheme"]!=SCHEME
        or statement["acceptance"]!="NOT_A_HUMAN_SIGNOFF"):
        raise ReleaseBlocked("signature statement has incorrect format or approval claim")
    if not isinstance(trusted_public_key,bytes) or len(trusted_public_key)!=32:
        raise ReleaseBlocked("independent trusted public key must contain 32 bytes")
    if statement["public_key_sha256"]!=hashlib.sha256(trusted_public_key).hexdigest():
        raise ReleaseBlocked("release signer not in independent trust registry")
    try:
        raw=bytes.fromhex(statement["signature_hex"])
        if len(raw)!=64:
            raise ValueError("bad signature length")
        Ed25519PublicKey.from_public_bytes(trusted_public_key).verify(
            raw,SCHEME.encode("ascii")+b"\x00"+encode_receipt(manifest))
    except (ValueError,TypeError,InvalidSignature) as exc:
        raise ReleaseBlocked("release receipt signature invalid") from exc
    return True
