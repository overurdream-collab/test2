import os
import pytest
from cryptography.exceptions import InvalidTag
from mcias.storage import EncryptedStore
from mcias.backup import encrypt_bundle, decrypt_bundle

def test_encrypted_source_integrity_and_path_restrictions(tmp_path):
    key = os.urandom(32)
    store = EncryptedStore(str(tmp_path), key)
    original = b"synthetic-private-patient-fixture-not-real"
    identifier, digest = store.put(original)
    blob = (tmp_path / identifier).read_bytes()
    assert original not in blob
    assert store.get(identifier, digest) == original
    with pytest.raises(ValueError):
        store.get("../" + identifier, digest)
    with pytest.raises(ValueError):
        store.get(identifier, "0" * 64)
    tampered = bytearray(blob)
    tampered[-1] ^= 1
    (tmp_path / identifier).write_bytes(tampered)
    with pytest.raises(InvalidTag):
        store.get(identifier, digest)

def test_encrypted_backup_tamper_and_wrong_key_fail_closed():
    key = os.urandom(32)
    archive = encrypt_bundle({"database.dump": b"synthetic-db", "sources/source1": b"synthetic-file"}, key)
    assert b"synthetic-db" not in archive
    assert decrypt_bundle(archive, key)["sources/source1"] == b"synthetic-file"
    with pytest.raises(InvalidTag):
        decrypt_bundle(archive, os.urandom(32))
    damaged = bytearray(archive)
    damaged[-1] ^= 1
    with pytest.raises(InvalidTag):
        decrypt_bundle(bytes(damaged), key)
