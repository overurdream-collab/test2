"""Production G3 contract activation requires external signed organization-head authorization."""
import json
from datetime import date, datetime, timezone
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from mcias.models import Base, Organization, User, SourceFile, WrittenAuthorization
from mcias.models_reference import ContractVersion
from mcias.production_authorization import signed_payload, verify_production_approval

def test_g3_signed_authorization_registry(tmp_path, monkeypatch):
    engine=create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        org=Organization(name="synthetic")
        approver=User(username="g3-head",password_hash="fixture")
        db.add_all([org,approver]);db.flush()
        approver.organization_id=org.id
        source=SourceFile(sha256="a"*64,original_filename="signed-authorization.pdf",storage_key="synthetic")
        db.add(source);db.flush()
        authorization=WrittenAuthorization(organization_id=org.id,source_id=source.id,
            approved_by=approver.id,approved_at=datetime.now(timezone.utc))
        contract=ContractVersion(organization_id=org.id,provider_code="P",version=1,
            effective_from=date(2027,1,1),effective_until=date(2028,1,1),
            status="draft",authorization_id=None)
        db.add_all([authorization,contract]);db.flush()
        contract.authorization_id=authorization.id
        db.commit()
        monkeypatch.delenv("MCIAS_AUTHORIZATION_REGISTRY",raising=False)
        assert not verify_production_approval(db,contract,authorization)
        private=Ed25519PrivateKey.generate()
        public=private.public_key().public_bytes(encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw)
        signature=private.sign(signed_payload(contract,authorization,source))
        registry={"approvals":{authorization.id:{"rule_id":contract.id,
            "authorization_id":authorization.id,"signature":signature.hex()}},
            "trusted_heads":{org.id:{approver.id:public.hex()}}}
        path=tmp_path/"trusted-heads.json"
        path.write_text(json.dumps(registry),encoding="utf-8")
        path.chmod(0o600)
        monkeypatch.setenv("MCIAS_AUTHORIZATION_REGISTRY",str(path))
        assert verify_production_approval(db,contract,authorization)
        registry["approvals"][authorization.id]["signature"]="00"*64
        path.write_text(json.dumps(registry),encoding="utf-8")
        assert not verify_production_approval(db,contract,authorization)
    engine.dispose()
