"""L1-FIX-001 Phase 1: intentionally RED safety contract tests.

Run from repository root: python -m pytest -q tests/test_l1_alembic_target_red.py
No Alembic module import, database URL parsing with real credentials, socket, engine,
or migration execution occurs. Only the ORIGINAL selector function is compiled.
Expected RED cases document missing security policy; do not xfail or weaken them.
"""
import ast
import os
from pathlib import Path

import pytest

ENV_FILE = Path(__file__).resolve().parents[1] / "alembic" / "env.py"
TEST_URL = "postgresql+psycopg://synthetic:fake@127.0.0.1:5432/mcias_ci"
RUNTIME_URL = "postgresql+psycopg://synthetic:fake@127.0.0.1:5432/mcias_runtime"


@pytest.fixture
def selector(monkeypatch):
    """Execute migration_database_url exactly as authored, without env.py side effects."""
    parsed = ast.parse(ENV_FILE.read_text(encoding="utf-8"), filename=str(ENV_FILE))
    fn = next(node for node in parsed.body
              if isinstance(node, ast.FunctionDef) and node.name == "migration_database_url")
    namespace = {"os": os}
    class FakeSettings:
        @property
        def database_url(self):
            return os.environ.get("MCIAS_DATABASE_URL", "")
        @property
        def environment(self):
            return os.environ.get("MCIAS_ENVIRONMENT", "development")
    namespace["Settings"] = FakeSettings
    monkeypatch.delenv("MCIAS_DATABASE_URL", raising=False)
    monkeypatch.delenv("MCIAS_TEST_DATABASE_URL", raising=False)
    monkeypatch.delenv("MCIAS_ENVIRONMENT", raising=False)
    monkeypatch.delenv("MCIAS_MIGRATION_TARGET", raising=False)
    exec(compile(ast.Module(body=[fn], type_ignores=[]), str(ENV_FILE), "exec"), namespace)
    return namespace["migration_database_url"]


def _configure(monkeypatch, *, runtime=None, test=None, environment="development", target=None):
    for key, value in {
        "MCIAS_DATABASE_URL": runtime,
        "MCIAS_TEST_DATABASE_URL": test,
        "MCIAS_ENVIRONMENT": environment,
        "MCIAS_MIGRATION_TARGET": target,
    }.items():
        if value is None:
            monkeypatch.delenv(key, raising=False)
        else:
            monkeypatch.setenv(key, value)


def test_allow_explicit_runtime_only(selector, monkeypatch):
    _configure(monkeypatch, runtime=RUNTIME_URL, environment="development", target="runtime")
    assert selector() == RUNTIME_URL


def test_allow_isolated_test_only(selector, monkeypatch):
    _configure(monkeypatch, test=TEST_URL, environment="test", target="test")
    assert selector() == TEST_URL


def test_reject_ambiguous_two_urls_before_connection(selector, monkeypatch):
    _configure(monkeypatch, runtime=RUNTIME_URL, test=TEST_URL)
    with pytest.raises(ValueError, match="ALEMBIC_TARGET_AMBIGUOUS"):
        selector()


def test_reject_test_override_in_production(selector, monkeypatch):
    _configure(monkeypatch, runtime=RUNTIME_URL, test=TEST_URL,
               environment="production", target="test")
    with pytest.raises(ValueError, match="ALEMBIC_TARGET"):
        selector()


def test_reject_missing_url(selector, monkeypatch):
    _configure(monkeypatch, environment="test", target="test")
    with pytest.raises(ValueError, match="ALEMBIC_TARGET"):
        selector()


def test_reject_malformed_test_url(selector, monkeypatch):
    _configure(monkeypatch, test="not-a-database-url", environment="test", target="test")
    with pytest.raises(ValueError, match="ALEMBIC_TARGET"):
        selector()


def test_reject_unapproved_test_database(selector, monkeypatch):
    _configure(monkeypatch, test=RUNTIME_URL, environment="test", target="test")
    with pytest.raises(ValueError, match="ALEMBIC_TARGET"):
        selector()


def test_reject_implicit_fallback_after_empty_test(selector, monkeypatch):
    _configure(monkeypatch, runtime=RUNTIME_URL, test="", environment="test", target="test")
    with pytest.raises(ValueError, match="ALEMBIC_TARGET"):
        selector()


def test_offline_online_share_same_selector_source():
    """Static test: both modes use the same selector, without invoking either mode."""
    parsed = ast.parse(ENV_FILE.read_text(encoding="utf-8"))
    funcs = {f.name: f for f in parsed.body if isinstance(f, ast.FunctionDef)}
    for name in ("run_migrations_offline", "run_migrations_online"):
        calls = [n for n in ast.walk(funcs[name])
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                 and n.func.id == "migration_database_url"]
        assert len(calls) == 1, name


def test_ci_contract_explicit_test_url_does_not_require_runtime(selector, monkeypatch):
    """Authorized isolated CI must remain possible without a runtime URL."""
    _configure(monkeypatch, test=TEST_URL, environment="test", target="test")
    assert selector() == TEST_URL
