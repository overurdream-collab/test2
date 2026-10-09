"""AES-256-GCM local document storage; never persist plaintext."""
import hashlib
import os
import secrets
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

class EncryptedStore:
    def __init__(self, directory: str, key: bytes):
        if len(key) != 32:
            raise ValueError("AES-256 key required")
        self.root = Path(directory).resolve()
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.aead = AESGCM(key)

    def put(self, data: bytes) -> tuple[str, str]:
        object_id = secrets.token_hex(24)
        nonce = os.urandom(12)
        digest = hashlib.sha256(data).hexdigest()
        ciphertext = b"MCIAS1" + nonce + self.aead.encrypt(nonce, data, object_id.encode())
        with (self.root / object_id).open("xb") as f:
            os.chmod(f.name, 0o600)
            f.write(ciphertext)
            f.flush()
            os.fsync(f.fileno())
        return object_id, digest

    def get(self, object_id: str, digest: str) -> bytes:
        if len(object_id) != 48 or any(c not in "0123456789abcdef" for c in object_id):
            raise ValueError("invalid object identifier")
        blob = (self.root / object_id).read_bytes()
        if not blob.startswith(b"MCIAS1"):
            raise ValueError("invalid encrypted file")
        plaintext = self.aead.decrypt(blob[6:18], blob[18:], object_id.encode())
        if hashlib.sha256(plaintext).hexdigest() != digest:
            raise ValueError("source checksum mismatch")
        return plaintext
