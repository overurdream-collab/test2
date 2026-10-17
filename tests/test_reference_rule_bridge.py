"""Synthetic G3-G5-to-point integration: historical/tenant/provider checks.

All records are fabricated, no medical data or institutional approvals.
"""
from datetime import date
from decimal import Decimal
from types import SimpleNamespace as Obj
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from mcias.models import Base, Organization, User
from mcias.models_reference_points import ReferencePoint, ReferencePointClosure
from mcias.reference_rule_bridge import reconcile


def make_point(db, org, user, *, provider="H1", service="CONSULT",
               begin=date(2026, 1, 1), price="5000", version=1,
               section="tariffs", key=None, rule_type="amount", end=date(9999, 12, 31)):
    point = ReferencePoint(organization_id=org, section=section,
        logical_key=key or provider + ":" + service, version=version,
        title="synthetic", clause_text="fabricated policy clause",
        rule_type=rule_type, provider_code=provider, service_code=service,
        amount=Decimal(price) if price is not None else None, currency="YER",
        effective_from=begin, effective_until=end, status="approved",
        created_by=user, approved_by=user)
    db.add(point)
    db.flush()
    return point


def context(org, provider, when, price):
    claim = Obj(organization_id=org, provider_code=provider,
                service_code="CONSULT", service_date=when, currency="YER")
    p = Obj(tariff=Decimal(price), copay_percent=Decimal(20), exclusion=Decimal(0))
    g3 = Obj(amount=Decimal(price), currency="YER")
    return claim, p, g3


def test_boundary_switch_uses_service_date_and_independent_provider():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        org = Organization(name="synthetic time-travel claims")
        db.add(org)
        db.flush()
        user = User(organization_id=org.id, username="syn-reference-bridge", password_hash="synthetic")
        db.add(user)
        db.flush()
        original = make_point(db, org.id, user.id)
        update = make_point(db, org.id, user.id,
                            begin=date(2026, 7, 1), version=2, price="5500")
        db.add(ReferencePointClosure(point_id=original.id, organization_id=org.id,
            effective_until=date(2026, 7, 1), replaced_by_id=update.id,
            reason="signed test amendment", approved_by=user.id))
        provider2 = make_point(db, org.id, user.id, provider="H2", price="7000")
        db.flush()
        for when, amount, expected in [
            (date(2026, 6, 30), "5000", original.id),
            (date(2026, 7, 1), "5500", update.id),
            (date(2026, 10, 1), "5500", update.id),
        ]:
            claim, p, g3 = context(org.id, "H1", when, amount)
            r = reconcile(db, claim, p, g3)
            assert r["status"] == "pass"
            assert [v["point_id"] for v in r["points"]] == [expected]
        claim, p, g3 = context(org.id, "H2", date(2026, 9, 1), "7000")
        assert reconcile(db, claim, p, g3)["points"][0]["point_id"] == provider2.id
        # Comparing the July price with an obsolete or wrong provider tariff holds.
        claim, p, g3 = context(org.id, "H1", date(2026, 7, 1), "5000")
        assert reconcile(db, claim, p, g3)["status"] == "hold"
        other = Organization(name="second synthetic isolated institution")
        db.add(other)
        db.flush()
        claim, p, g3 = context(other.id, "H1", date(2026, 7, 1), "5000")
        assert reconcile(db, claim, p, g3)["points"] == []
    engine.dispose()


def test_uncompiled_clause_is_held_instead_of_claimed_pass():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        org = Organization(name="synthetic missing compilers")
        db.add(org)
        db.flush()
        user = User(organization_id=org.id, username="syn-reference-uncompiled", password_hash="synthetic")
        db.add(user)
        db.flush()
        point = make_point(db, org.id, user.id, section="approvals",
                           key="requires_prior_approval", rule_type="approval",
                           price=None)
        claim, p, g3 = context(org.id, "H1", date(2026, 5, 1), "5000")
        r = reconcile(db, claim, p, g3)
        assert r["status"] == "hold"
        assert "uncompiled_approvals_point" in r["unresolved"]
        assert r["points"][0]["point_id"] == point.id
    engine.dispose()


def test_cost_share_requires_exact_signed_policy_agreement():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        org = Organization(name="synthetic financial policy map")
        db.add(org)
        db.flush()
        user = User(organization_id=org.id, username="syn-reference-copay", password_hash="synthetic")
        db.add(user)
        db.flush()
        make_point(db, org.id, user.id, section="cost_sharing",
                   key="copay_percent", rule_type="percentage", price="20")
        claim, policy, g3 = context(org.id, "H1", date(2026, 5, 1), "5000")
        assert reconcile(db, claim, policy, g3)["status"] == "pass"
        wrong_policy = Obj(tariff=Decimal(5000), copay_percent=Decimal(15), exclusion=Decimal(0))
        assert reconcile(db, claim, wrong_policy, g3)["status"] == "hold"
    engine.dispose()
