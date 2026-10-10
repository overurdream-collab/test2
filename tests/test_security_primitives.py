import os
import pytest
from cryptography.exceptions import InvalidTag
from mcias.security import hash_password, verify_password, new_session_token
from mcias.storage import EncryptedStore
from mcias.backup import encrypt_bundle, decrypt_bundle

def test_password_hash():
    encoded = hash_password("correct horse battery staple")
    assert verify_password("correct horse battery staple", encoded)
    assert not verify_password("wrong password", encoded)
    assert encoded != hash_password("correct horse battery staple")

def test_short_password_rejected():
    with pytest.raises(ValueError): hash_password("short")

def test_opaque_session_token():
    token, digest = new_session_token()
    assert token != digest and len(digest) == 64

def test_encrypted_store_roundtrip(tmp_path):
    store = EncryptedStore(str(tmp_path), os.urandom(32))
    key, digest = store.put(b"private medical claim")
    assert b"private medical claim" not in (tmp_path / key).read_bytes()
    assert store.get(key, digest) == b"private medical claim"
    with pytest.raises(ValueError): store.get("../etc/passwd", digest)
    with pytest.raises(ValueError): store.get(key, "0"*64)

def test_encrypted_bundle_restore_and_tamper():
    key = os.urandom(32)
    source = {"db.dump": b"test database", "files/document": b"private record"}
    encrypted = encrypt_bundle(source, key)
    assert b"private record" not in encrypted
    assert decrypt_bundle(encrypted, key) == source
    tampered = bytearray(encrypted)
    tampered[-1] ^= 1
    with pytest.raises(InvalidTag): decrypt_bundle(bytes(tampered), key)

def test_archive_path_traversal_rejected():
    with pytest.raises(ValueError): encrypt_bundle({"../escape": b"x"}, os.urandom(32))
