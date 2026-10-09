import os
import pytest
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag
from mcias.mfa_key_rotation import rewrap_mfa_secret

def test_mfa_rewrap_preserves_secret_and_binds_identity():
    old_key, new_key = os.urandom(32), os.urandom(32)
    secret, user_id = os.urandom(20), "synthetic-user"
    nonce = os.urandom(12)
    envelope = nonce + AESGCM(old_key).encrypt(nonce, secret, user_id.encode())
    rotated = rewrap_mfa_secret(envelope, user_id, old_key, new_key)
    assert rotated != envelope
    assert AESGCM(new_key).decrypt(rotated[:12], rotated[12:], user_id.encode()) == secret
    with pytest.raises(InvalidTag):
        rewrap_mfa_secret(envelope, user_id, new_key, old_key)
    with pytest.raises(InvalidTag):
        AESGCM(new_key).decrypt(rotated[:12], rotated[12:], b"other-user")
    with pytest.raises(ValueError):
        rewrap_mfa_secret(envelope, user_id, b"short", new_key)
