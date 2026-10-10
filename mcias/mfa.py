"""TOTP verification with replay protection; secret custody belongs to encrypted store."""
import base64
import hashlib
import hmac
import struct
import time

def generate_totp(secret: bytes, counter: int, digits: int = 6) -> str:
    if len(secret) < 20 or counter < 0:
        raise ValueError("invalid TOTP parameters")
    digest = hmac.new(secret, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 15
    code = (struct.unpack(">I", digest[offset:offset+4])[0] & 0x7fffffff) % (10**digits)
    return str(code).zfill(digits)

def verify_totp(secret: bytes, submitted: str, last_accepted_counter: int = -1, *, now: int | None = None, step: int = 30) -> int | None:
    if len(submitted) != 6 or not submitted.isascii() or not submitted.isdigit():
        return None
    current = int(time.time() if now is None else now) // step
    for counter in (current-1, current, current+1):
        if counter > last_accepted_counter and counter >= 0 and hmac.compare_digest(generate_totp(secret, counter), submitted):
            return counter
    return None
