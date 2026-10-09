"""Detached organization-head signature verification.

The trusted key registry must be provisioned out of band and tied to the
verified head's authority. Never accept a public key supplied in the request.
"""
import hashlib
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

def verify_written_authorization(document: bytes, expected_sha256: str, signature_hex: str, trusted_public_key: bytes) -> bool:
    if not document or hashlib.sha256(document).hexdigest() != expected_sha256:
        return False
    try:
        signature = bytes.fromhex(signature_hex)
        if len(signature) != 64 or len(trusted_public_key) != 32:
            return False
        Ed25519PublicKey.from_public_bytes(trusted_public_key).verify(signature, document)
        return True
    except (ValueError, TypeError):
        return False
