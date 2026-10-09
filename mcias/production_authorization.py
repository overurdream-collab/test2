"""Production rule approval: signed, externally provisioned trust registry.

No keys or approvals are accepted from HTTP requests. A deployment must provide
a read-only JSON file at MCIAS_AUTHORIZATION_REGISTRY containing approvals and
trusted organization-head public keys. The signature binds organization, approver,
authorization, source SHA-256 and rule ID.
"""
import json
import os
from pathlib import Path
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from mcias.models import SourceFile

def signed_payload(rule, approval, source):
    return json.dumps({
        "authorization_id": approval.id,
        "organization_id": rule.organization_id,
        "approved_by": approval.approved_by,
        "rule_id": rule.id,
        "source_id": approval.source_id,
        "source_sha256": source.sha256,
    }, sort_keys=True, separators=(",", ":")).encode("utf-8")

def verify_production_approval(db, rule, approval):
    location = os.environ.get("MCIAS_AUTHORIZATION_REGISTRY")
    if not location:
        return False
    try:
        path = Path(location)
        if not path.is_file() or path.is_symlink() or (path.stat().st_mode & 0o022):
            return False
        registry = json.loads(path.read_text(encoding="utf-8"))
        entry = registry["approvals"][approval.id]
        trusted = registry["trusted_heads"][rule.organization_id][approval.approved_by]
        if entry["rule_id"] != rule.id or entry["authorization_id"] != approval.id:
            return False
        source = db.get(SourceFile, approval.source_id)
        if source is None or len(source.sha256) != 64:
            return False
        payload = signed_payload(rule, approval, source)
        key = bytes.fromhex(trusted)
        signature = bytes.fromhex(entry["signature"])
        if len(key) != 32 or len(signature) != 64:
            return False
        Ed25519PublicKey.from_public_bytes(key).verify(signature, payload)
        return True
    except (OSError, ValueError, TypeError, KeyError, InvalidSignature):
        return False
