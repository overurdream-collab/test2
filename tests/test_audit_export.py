from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from mcias.audit_export import chain_events, verify_chain, sign_checkpoint, verify_checkpoint

def test_audit_chain_detects_change_reorder_and_deletion():
    events=[{"id":"a","action":"login"},{"id":"b","action":"deny"},{"id":"c","action":"logout"}]
    chain=chain_events(events)
    assert verify_chain(chain)
    changed=[dict(item) for item in chain]
    changed[1]["event"]={"id":"b","action":"allow"}
    assert not verify_chain(changed)
    assert not verify_chain(chain[1:])
    assert not verify_chain(chain[:-1], starting_hash=chain[-1]["digest"])
    assert not verify_chain([chain[1],chain[0],chain[2]])
    key=Ed25519PrivateKey.generate()
    checkpoint=sign_checkpoint(chain,key)
    assert verify_checkpoint(checkpoint,key.public_key())
    assert not verify_checkpoint({"head":"0"*64,"signature":checkpoint["signature"]},key.public_key())
