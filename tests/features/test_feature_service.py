from datetime import date, timedelta
import pytest
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from mcias.models import AuditLog, User
from mcias.models_features import OrganizationFeature
from mcias.services import feature_service as f

def test_catalog_and_tree(features_api):
    with Session(features_api.engine) as db:
        assert len(f.list_features(db)) == 45
        tree = f.list_feature_tree(db)
        assert len(tree) == 11
        assert sum(len(n["children"]) for n in tree) == 34

def test_grant_has_version_and_audit_without_commit(features_api):
    a = features_api
    with Session(a.engine) as db:
        db.begin()
        row = f.grant_feature(db, a.organization_id, "inputs.contracts", a.ids["root"])
        assert row.version == 1 and row.status == "open"
        assert db.scalar(select(func.count()).select_from(AuditLog).where(AuditLog.action == "feature.grant")) == 1
        db.rollback()
    with Session(a.engine) as db:
        assert not f.check_feature(db, a.organization_id, "inputs.contracts")

@pytest.mark.parametrize("code", ["inputs", "unknown.feature"])
def test_only_existing_leaves_can_be_granted(features_api, code):
    a = features_api
    with Session(a.engine) as db:
        with pytest.raises(ValueError): f.grant_feature(db, a.organization_id, code, a.ids["root"])
        assert db.scalar(select(User.id).limit(1))

def test_duplicate_and_future_overlap(features_api):
    a = features_api
    with Session(a.engine) as db:
        row = f.grant_feature(db, a.organization_id, "inputs.contracts", a.ids["root"])
        row.effective_from = date.today() + timedelta(days=1)
        db.flush()
        assert not f.check_feature(db, a.organization_id, row.feature_code)
        with pytest.raises(ValueError): f.grant_feature(db, a.organization_id, row.feature_code, a.ids["root"])
        assert db.scalar(select(User.id).limit(1))

def test_revoke_and_regrant_increment_version(features_api):
    a = features_api
    with Session(a.engine) as db:
        f.grant_feature(db, a.organization_id, "inputs.contracts", a.ids["root"])
        row = f.revoke_feature(db, a.organization_id, "inputs.contracts", a.ids["root"], "Test closure")
        assert row.closed_by and row.closed_at and row.effective_to == date.today()
        assert not f.check_feature(db, a.organization_id, row.feature_code)
        with pytest.raises(ValueError): f.revoke_feature(db, a.organization_id, row.feature_code, a.ids["root"], "Again")
        assert f.grant_feature(db, a.organization_id, row.feature_code, a.ids["root"]).version == 2

def test_empty_reason_does_not_close(features_api):
    a = features_api
    with Session(a.engine) as db:
        f.grant_feature(db, a.organization_id, "inputs.contracts", a.ids["root"])
        with pytest.raises(ValueError): f.revoke_feature(db, a.organization_id, "inputs.contracts", a.ids["root"], " ")
        assert f.check_feature(db, a.organization_id, "inputs.contracts")

def test_visible_is_entitlement_intersection_permission(features_api):
    a = features_api
    with Session(a.engine) as db:
        admin, none = db.get(User, a.ids["admin"]), db.get(User, a.ids["none"])
        assert f.get_visible_features(db, admin) == []
        f.grant_feature(db, a.organization_id, "inputs.contracts", a.ids["root"])
        assert f.get_visible_features(db, admin) == ["inputs.contracts"]
        assert f.get_visible_features(db, none) == []
        assert f.get_visible_features(db, db.get(User, a.ids["other"])) == []
        assert len(f.get_visible_features(db, db.get(User, a.ids["root"]))) == 34

def test_inactive_users_and_role_flag_do_not_bypass(features_api):
    a = features_api
    with Session(a.engine) as db:
        for name in ("admin", "flag_only", "no_mfa", "future"):
            with pytest.raises(ValueError): f.grant_feature(db, a.organization_id, "inputs.contracts", a.ids[name])
        actor = db.get(User, a.ids["admin"]); actor.active = False
        assert f.get_visible_features(db, actor) == []

def test_atomic_batch_stale_editor_and_failure_rollback(features_api):
    a = features_api
    with Session(a.engine) as db:
        initial = f.grant_revision(db, a.organization_id)
        f.replace_features(db, a.organization_id, ["inputs.contracts"], a.ids["root"], "", initial)
        with pytest.raises(ValueError): f.replace_features(db, a.organization_id, [], a.ids["root"], "Close", initial)
        revision = f.grant_revision(db, a.organization_id)
        with pytest.raises(ValueError): f.replace_features(db, a.organization_id, ["inputs"], a.ids["root"], "Close", revision)
        with pytest.raises(ValueError): f.replace_features(db, a.organization_id, [], a.ids["root"], "", revision)
        assert f.check_feature(db, a.organization_id, "inputs.contracts")
