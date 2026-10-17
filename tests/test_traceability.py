"""Use fresh synthetic Git repositories to test the governance guard itself."""
import subprocess
import tempfile
import unittest
from pathlib import Path
from scripts.check_traceability import verify, FIELDS


def run(repo, *args):
    return subprocess.check_output(["git", *args], cwd=repo, text=True).strip()


class TraceabilityTests(unittest.TestCase):
    def setUp(self):
        self.workspace = tempfile.TemporaryDirectory()
        self.root = Path(self.workspace.name)
        run(self.root, "init", "-q")
        run(self.root, "config", "user.name", "Synthetic Test")
        run(self.root, "config", "user.email", "synthetic@example.invalid")
        (self.root/"README.md").write_text("initial\n")
        run(self.root, "add", ".")
        run(self.root, "commit", "-qm", "base")
        self.cutoff = run(self.root, "rev-parse", "HEAD")

    def tearDown(self):
        self.workspace.cleanup()

    def append_log(self, parent):
        path = self.root/"docs/engineering/worklogs/fixture.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(["### TEST-EVENT",
            *["- "+k+" synthetic" for k in FIELDS if k not in ("before_sha:","after_ref:")],
            "- before_sha: "+parent,
            "- after_ref: SELF"]) + "\n")

    def test_missing_same_commit_log_is_rejected(self):
        (self.root/"code.py").write_text("print(1)\n")
        run(self.root, "add", ".")
        run(self.root, "commit", "-qm", "unlogged change")
        self.assertTrue(verify(self.root, self.cutoff))

    def test_valid_atomic_change_is_accepted(self):
        (self.root/"code.py").write_text("print(1)\n")
        self.append_log(self.cutoff)
        run(self.root, "add", ".")
        run(self.root, "commit", "-qm", "atomic change")
        self.assertEqual(verify(self.root, self.cutoff), [])

    def test_wrong_parent_and_missing_fields_is_rejected(self):
        (self.root/"code.py").write_text("print(1)\n")
        dest=self.root/"docs/engineering/worklogs/fixture.md"
        dest.parent.mkdir(parents=True)
        dest.write_text("- before_sha: "+("0"*40)+"\n- after_ref: SELF\n")
        run(self.root, "add", ".")
        run(self.root, "commit", "-qm", "bad ledger")
        errors=verify(self.root, self.cutoff)
        self.assertTrue(any("parent" in e for e in errors))
        self.assertTrue(any("fields" in e for e in errors))

    def test_log_only_update_does_not_self_recurse(self):
        self.append_log(self.cutoff)
        run(self.root, "add", ".")
        run(self.root, "commit", "-qm", "log only")
        self.assertEqual(verify(self.root, self.cutoff), [])


if __name__ == "__main__":
    unittest.main()
