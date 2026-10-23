"""Explicit synthetic institution approvals. No production permission bypass."""
import hashlib,json,os
from pathlib import Path
from uuid import uuid4
from sqlalchemy import select
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from mcias.models import User,Role,UserRole,MFAFactor,Organization
from mcias.services import rbac_provisioning as plans,authorization_service as auth

_KEYS={}

def approve_fixture(db,org_id=None,root_id=None):
    """Review the existing fixture matrix explicitly, using real signature checks."""
    path=Path(os.environ['MCIAS_RBAC_TRUST_REGISTRY'])
    registry=json.loads(path.read_text()) if path.exists() else {'trusted_approvers':{}}
    results=[]
    for org in db.scalars(select(Organization).where(Organization.id==org_id) if org_id else select(Organization)):
        suffix=org.id
        root=db.get(User,root_id) if root_id else db.scalar(select(User).where(User.username=='SYN-rbac-root-'+suffix))
        if root is None:
            root=User(organization_id=org.id,username='SYN-rbac-root-'+suffix,password_hash='synthetic-not-login')
            db.add(root);db.flush()
            role=db.scalar(select(Role).where(Role.code=='super_admin'))
            if role is None:role=Role(code='super_admin');db.add(role);db.flush()
            db.add(UserRole(user_id=root.id,role_id=role.id));db.add(MFAFactor(user_id=root.id,enabled=True,encrypted_secret=b'synthetic-not-login'))
            db.flush()
        signer=db.scalar(select(User).where(User.username=='SYN-rbac-signer-'+suffix))
        if signer is None:
            signer=User(organization_id=org.id,username='SYN-rbac-signer-'+suffix,password_hash='synthetic-not-login');db.add(signer);db.flush()
        key=_KEYS.setdefault(signer.id,Ed25519PrivateKey.generate())
        registry['trusted_approvers'].setdefault(org.id,{})[signer.id]=key.public_key().public_bytes_raw().hex()
        path.write_text(json.dumps(registry));path.chmod(0o600)
        manifest=plans.preview_migration(db,org.id)
        ref='SYNTHETIC FIXTURE APPROVAL — NOT INSTITUTIONAL ACCEPTANCE'
        signature=key.sign(auth.signed_document(manifest,signer.id,ref)).hex()
        results.append(plans.apply_plan(db,root.id,{'manifest':manifest,'approved_by':signer.id,'approval_reference':ref,'signature':signature}))
    db.flush()
    return results


def signed_fixture(db,root_id,manifest):
    root=db.get(User,root_id)
    signer=db.scalar(select(User).where(User.username=='SYN-rbac-signer-'+root.organization_id))
    ref='SYNTHETIC CONFIGURATION APPROVAL'
    return {'manifest':manifest,'approved_by':signer.id,'approval_reference':ref,
        'signature':_KEYS[signer.id].sign(auth.signed_document(manifest,signer.id,ref)).hex()}
