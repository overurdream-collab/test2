"""Local-project exclusion must retain every installed external package."""
import json
from types import SimpleNamespace

import pytest
from scripts import audit_dependencies as audit


class Distribution:
    def __init__(self, name, version, direct=None):
        self.metadata = {"Name": name}
        self.version = version
        self.direct = direct

    def read_text(self, name):
        return json.dumps(self.direct) if self.direct else None

    def locate_file(self, name):
        return "/external/site-packages"


def test_only_local_project_is_omitted_and_audit_failure_is_preserved(monkeypatch):
    from pathlib import Path
    repository = Path(audit.__file__).resolve().parents[1]
    distributions = [Distribution("mcias", "0.1.0", {
        "url": repository.as_uri(), "dir_info": {"editable": True}}),
        Distribution("Pillow", "13.0.0"),
        Distribution("external-editable", "1.2.3", {
            "url": "file:///external", "dir_info": {"editable": True}})]
    monkeypatch.setattr(audit.metadata, "distributions", lambda: distributions)
    monkeypatch.setattr(audit.sys, "argv", ["audit_dependencies.py"])

    def invoke(command, check):
        requirements = Path(command[command.index("-r") + 1]).read_text()
        assert requirements == "external-editable==1.2.3\npillow==13.0.0\n"
        assert "--strict" in command and "--ignore-vuln" not in command
        return SimpleNamespace(returncode=1)

    monkeypatch.setattr(audit.subprocess, "run", invoke)
    assert audit.main() == 1


def test_external_mcias_cannot_be_silently_omitted(monkeypatch):
    monkeypatch.setattr(audit.metadata, "distributions", lambda: [Distribution("mcias", "0.1.0")])
    with pytest.raises(RuntimeError, match="local editable"):
        audit.main()
