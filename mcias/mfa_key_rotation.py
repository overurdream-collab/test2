"""Offline MFA key rotation primitive; operator approval and custody are external."""
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

def rewrap_mfa_secret(envelope: bytes, user_id: str, old_key: bytes, new_key: bytes) -> bytes:
    if len(old_key) != 32 or len(new_key) != 32:
        raise ValueError("AES-256 keys required")
    if len(envelope) < 29 or not user_id:
        raise ValueError("invalid MFA envelope")
    secret = AESGCM(old_key).decrypt(envelope[:12], envelope[12:], user_id.encode())
    if len(secret) != 20:
        raise ValueError("invalid TOTP secret length")
    nonce = os.urandom(12)
    return nonce + AESGCM(new_key).encrypt(nonce, secret, user_id.encode())
