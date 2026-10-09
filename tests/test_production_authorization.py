import json
from datetime import datetime, timezone
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from mcias.models import Base, Organization, User, Role, Permission, UserRole, RolePermission, RuleVersion, SourceFile, WrittenAuthorization
from mcias.policy import can_activate_rule
from mcias.production_authorization import signed_payload

def test_production_requires_valid_head_signature(tmp_path, monkeypatch):
    engine=create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        org=Organization(name="synthetic")
        db.add(org);db.flush()
        actor=User(username="actor",password_hash="fixture",organization_id=org.id)
        head=User(username="head",password_hash="fixture",organization_id=org.id)
        role=Role(code="activator")
        perm=Permission(code="rules.activate")
        source=SourceFile(sha256="a"*64,original_filename="authorization.pdf",storage_key="fixture")
        db.add_all([actor,head,role,perm,source]);db.flush()
        db.add_all([UserRole(user_id=actor.id,role_id=role.id),RolePermission(role_id=role.id,permission_id=perm.id)])
        approval=WrittenAuthorization(organization_id=org.id,source_id=source.id,approved_by=head.id,approved_at=datetime.now(timezone.utc))
        db.add(approval);db.flush()
        rule=RuleVersion(organization_id=org.id,rule_type="pricing",written_authorization_id=approval.id)
        db.add(rule);db.flush()
        monkeypatch.setenv("MCIAS_ENVIRONMENT","production")
        monkeypatch.delenv("MCIAS_AUTHORIZATION_REGISTRY",raising=False)
        assert not can_activate_rule(db,actor,rule)
        key=Ed25519PrivateKey.generate()
        registry={"trusted_heads":{org.id:{head.id:key.public_key().public_bytes_raw().hex()}},"approvals":{approval.id:{"rule_id":rule.id,"authorization_id":approval.id,"signature":key.sign(signed_payload(rule,approval,source)).hex()}}}
        path=tmp_path/"registry.json"
        path.write_text(json.dumps(registry))
        monkeypatch.setenv("MCIAS_AUTHORIZATION_REGISTRY",str(path))
        assert can_activate_rule(db,actor,rule)
        path.chmod(0o666)
        assert not can_activate_rule(db,actor,rule)
        path.chmod(0o600)
        assert can_activate_rule(db,actor,rule)
        registry["approvals"][approval.id]["signature"]="00"*64
        path.write_text(json.dumps(registry))
        assert not can_activate_rule(db,actor,rule)
        registry["approvals"][approval.id]["signature"]=key.sign(signed_payload(rule,approval,source)).hex()
        registry["approvals"][approval.id]["rule_id"]="different-rule"
        path.write_text(json.dumps(registry))
        assert not can_activate_rule(db,actor,rule)
    engine.dispose()
