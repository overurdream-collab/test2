import hashlib
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from mcias.authorization_signatures import verify_written_authorization

def test_authorization_signature_binds_exact_document():
    key = Ed25519PrivateKey.generate()
    document = b"synthetic signed approval fixture"
    digest = hashlib.sha256(document).hexdigest()
    signature = key.sign(document).hex()
    trusted = key.public_key().public_bytes_raw()
    assert verify_written_authorization(document, digest, signature, trusted)
    assert not verify_written_authorization(document+b"!", digest, signature, trusted)
    assert not verify_written_authorization(document, "0"*64, signature, trusted)
    assert not verify_written_authorization(document, digest, "00"*64, trusted)
