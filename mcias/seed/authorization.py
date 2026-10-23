"""Synthetic-only reviewed RBAC fixtures for dedicated development *_e2e databases.

Private test signing keys live outside the repository. Never use this helper for
client data or production; operational migration uses out-of-band institution keys.
"""
import json,os
from pathlib import Path
from sqlalchemy import select
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from mcias.models import User,Role,UserRole,MFAFactor
from mcias.services import rbac_provisioning as plans,authorization_service as auth

def approve_synthetic(db,organization_id,environment):
    url=db.get_bind().url
    if environment!='development' or url.get_backend_name()!='postgresql' or not url.database.endswith('_e2e'):
        raise ValueError('Explicit development and a dedicated *_e2e database required for synthetic RBAC approval')
    location=os.getenv('MCIAS_RBAC_TRUST_REGISTRY')
    if not location:raise ValueError('MCIAS_RBAC_TRUST_REGISTRY must point to a private synthetic fixture registry')
    path=Path(location);key_path=path.with_suffix('.synthetic-keys.json')
    path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    if path.is_symlink() or key_path.is_symlink():raise ValueError('Synthetic key registry cannot be symbolic')
    registry=json.loads(path.read_text()) if path.exists() else {'trusted_approvers':{}}
    secrets=json.loads(key_path.read_text()) if key_path.exists() else {}
    root=db.scalar(select(User).where(User.username=='SYN-seed-rbac-root-'+organization_id))
    if root is None:
        root=User(organization_id=organization_id,username='SYN-seed-rbac-root-'+organization_id,password_hash='synthetic-no-login')
        db.add(root);db.flush()
        role=db.scalar(select(Role).where(Role.code=='super_admin'))
        if role is None:role=Role(code='super_admin');db.add(role);db.flush()
        db.add(UserRole(user_id=root.id,role_id=role.id));db.add(MFAFactor(user_id=root.id,enabled=True,encrypted_secret=b'synthetic-no-login'))
    signer=db.scalar(select(User).where(User.username=='SYN-seed-rbac-signer-'+organization_id))
    if signer is None:
        signer=User(organization_id=organization_id,username='SYN-seed-rbac-signer-'+organization_id,password_hash='synthetic-no-login')
        db.add(signer);db.flush()
    db.flush()
    if signer.id not in secrets:secrets[signer.id]=Ed25519PrivateKey.generate().private_bytes_raw().hex()
    key=Ed25519PrivateKey.from_private_bytes(bytes.fromhex(secrets[signer.id]))
    registry['trusted_approvers'].setdefault(organization_id,{})[signer.id]=key.public_key().public_bytes_raw().hex()
    for target,data in ((key_path,secrets),(path,registry)):
        temporary=target.with_name(target.name+'.tmp')
        fd=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
        try:
            with os.fdopen(fd,'w',encoding='utf-8') as stream:json.dump(data,stream)
            temporary.replace(target)
        finally:temporary.unlink(missing_ok=True)
    manifest=plans.preview_migration(db,organization_id)
    ref='SYNTHETIC ONLY — NOT INSTITUTIONAL APPROVAL'
    envelope={'manifest':manifest,'approved_by':signer.id,'approval_reference':ref,
        'signature':key.sign(auth.signed_document(manifest,signer.id,ref)).hex()}
    return plans.apply_plan(db,root.id,envelope)
