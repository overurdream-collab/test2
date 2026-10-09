"""Tamper-evident audit export for independently controlled off-host storage.

An export is not proof of off-host delivery. The operator must verify
signature, custody and receipt independently.
"""
import hashlib
import json
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.exceptions import InvalidSignature

def canonical_event(event):
    return json.dumps(event, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

def chain_events(events, starting_hash="0"*64):
    previous = starting_hash
    result = []
    for event in events:
        digest = hashlib.sha256(bytes.fromhex(previous) + canonical_event(event)).hexdigest()
        result.append({"previous": previous, "digest": digest, "event": event})
        previous = digest
    return result

def verify_chain(records, starting_hash="0"*64):
    previous = starting_hash
    for item in records:
        if item.get("previous") != previous:
            return False
        expected = hashlib.sha256(bytes.fromhex(previous) + canonical_event(item["event"])).hexdigest()
        if item.get("digest") != expected:
            return False
        previous = expected
    return True

def sign_checkpoint(records, private_key: Ed25519PrivateKey):
    final_hash = records[-1]["digest"] if records else "0"*64
    return {"head": final_hash, "signature": private_key.sign(bytes.fromhex(final_hash)).hex()}

def verify_checkpoint(checkpoint, public_key: Ed25519PublicKey):
    try:
        public_key.verify(bytes.fromhex(checkpoint["signature"]), bytes.fromhex(checkpoint["head"]))
        return True
    except (InvalidSignature, ValueError, KeyError, TypeError):
        return False
