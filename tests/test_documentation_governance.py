"""DG-001 independent standard-library checks; does not require live GitHub."""
import importlib.util
import pathlib
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "check_documentation_governance.py"
spec = importlib.util.spec_from_file_location("documentation_governance", SCRIPT)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


class GovernanceParserTests(unittest.TestCase):
    def test_complete_record_passes(self):
        diff = "+### HANDOFF-20261017-001\n" + "".join(
            "+- " + key + ": documented relevant detail\n" for key in gate.REQUIRED)
        self.assertEqual(gate.validate_added_entry(diff), [])

    def test_incomplete_record_fails(self):
        problems = gate.validate_added_entry("+### HANDOFF-20261017-002\n+- Scope: only scope\n")
        self.assertTrue(any("Tests" in text for text in problems))

    def test_unstructured_notes_cannot_bypass(self):
        self.assertTrue(gate.validate_added_entry("+recorded something\n"))

    def test_baseline_document_paths_are_explicit(self):
        self.assertIn(gate.JOURNAL, gate.EXEMPT)
        self.assertIn(gate.STATE, gate.EXEMPT)
        self.assertEqual(len(gate.REQUIRED), 8)


if __name__ == "__main__":
    unittest.main()
