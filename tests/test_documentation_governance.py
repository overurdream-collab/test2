"""DG-001 independent standard-library checks; does not require live GitHub."""
import importlib.util
import pathlib
import unittest
import tempfile
import subprocess
import os

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "check_documentation_governance.py"
spec = importlib.util.spec_from_file_location("documentation_governance", SCRIPT)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


class GovernanceParserTests(unittest.TestCase):
    def test_complete_record_passes(self):
        diff = "+### HANDOFF-20261017-001\n" + "".join(
            "+- " + key + ": documented relevant detail\n" for key in gate.REQUIRED)
        self.assertEqual(gate.validate_added_entry(diff), [])

    def test_titled_handoff_keeps_all_eight_required_fields(self):
        titled = "+### HANDOFF-20261017-026 — C22 bounded timeout\n"
        documented = titled + "".join(
            "+- " + field + ": independently logged\n" for field in gate.REQUIRED)
        self.assertEqual(gate.validate_added_entry(documented), [])
        self.assertTrue(any("Tests" in problem for problem in
            gate.validate_added_entry(titled + "+- Scope: incomplete\n")))
        self.assertTrue(gate.validate_added_entry(
            "+### HANDOFF-20261017-026 unstructured fake heading\n" +
            "".join("+- " + field + ": value\n" for field in gate.REQUIRED)))

    def test_incomplete_record_fails(self):
        problems = gate.validate_added_entry("+### HANDOFF-20261017-002\n+- Scope: only scope\n")
        self.assertTrue(any("Tests" in text for text in problems))

    def test_unstructured_notes_cannot_bypass(self):
        self.assertTrue(gate.validate_added_entry("+recorded something\n"))

    def test_git_history_rejects_undocumented_code_commit(self):
        def cmd(repo, *args):
            p = subprocess.run(("git", *args), cwd=repo, capture_output=True,
                               text=True, check=True)
            return p.stdout.strip()
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            cmd(tmp, "init", "-q")
            cmd(tmp, "config", "user.name", "Synthetic CI")
            cmd(tmp, "config", "user.email", "synthetic@example.invalid")
            (root / "docs").mkdir()
            (root / gate.JOURNAL).write_text("# Audit log\n")
            (root / gate.STATE).write_text("## الحالة الآن\n## أين نتوقف؟\n"
                                          "## الخطوة التالية المحددة\n")
            cmd(tmp, "add", ".")
            cmd(tmp, "commit", "-qm", "initial checkpoint")
            initial = cmd(tmp, "rev-parse", "HEAD")
            (root / "service.py").write_text("x = 1\n")
            cmd(tmp, "add", "service.py")
            cmd(tmp, "commit", "-qm", "changed without documentation")
            latest = cmd(tmp, "rev-parse", "HEAD")
            original = os.getcwd()
            try:
                os.chdir(tmp)
                checked, _, errors = gate.validate(initial, latest, "")
            finally:
                os.chdir(original)
            self.assertEqual(checked, 1)
            self.assertTrue(any("documentation missing" in e for e in errors))

    def test_git_history_accepts_atomic_handoff(self):
        def cmd(repo, *args):
            return subprocess.run(("git", *args), cwd=repo,
                                  capture_output=True, text=True, check=True).stdout.strip()
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            cmd(tmp, "init", "-q")
            cmd(tmp, "config", "user.name", "Synthetic CI")
            cmd(tmp, "config", "user.email", "synthetic@example.invalid")
            (root / "docs").mkdir()
            (root / gate.JOURNAL).write_text("# Audit log\n")
            (root / gate.STATE).write_text("## الحالة الآن\n## أين نتوقف؟\n"
                                          "## الخطوة التالية المحددة\n")
            cmd(tmp, "add", ".")
            cmd(tmp, "commit", "-qm", "initial checkpoint")
            initial = cmd(tmp, "rev-parse", "HEAD")
            (root / "service.py").write_text("x = 1\n")
            with (root / gate.JOURNAL).open("a") as fh:
                fh.write("\n### HANDOFF-20261017-999\n")
                fh.writelines("- " + key + ": synthetic proof\n" for key in gate.REQUIRED)
            with (root / gate.STATE).open("a") as fh:
                fh.write("\nChanged code and next task recorded.\n")
            cmd(tmp, "add", ".")
            cmd(tmp, "commit", "-qm", "code with atomic handoff")
            original = os.getcwd()
            try:
                os.chdir(tmp)
                checked, _, errors = gate.validate(initial, cmd(tmp, "rev-parse", "HEAD"), "")
            finally:
                os.chdir(original)
            self.assertEqual(checked, 1)
            self.assertEqual(errors, [])

    def test_baseline_document_paths_are_explicit(self):
        self.assertIn(gate.JOURNAL, gate.EXEMPT)
        self.assertIn(gate.STATE, gate.EXEMPT)
        self.assertEqual(len(gate.REQUIRED), 8)


if __name__ == "__main__":
    unittest.main()
