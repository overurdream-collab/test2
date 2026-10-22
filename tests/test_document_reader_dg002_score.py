"""Synthetic evaluator contract tests; NO OCR engine is installed or run."""
import copy
import unittest
from scripts.document_reader_dg002_score import canonical, evaluate

SHA = "a" * 64

def fixture():
    truth = {
        "documents": [{
            "id": "synthetic-medical", "sha256": SHA, "language": "ar",
            "pages": [{"page": 1, "text": "باراسيتامول ٥٠٠ ملغ"}],
            "fields": [
                {"field_id": "drug.name", "kind": "medication_name",
                 "value": "باراسيتامول", "page": 1, "row_id": "RX-1", "bbox": [20, 10, 180, 30]},
                {"field_id": "drug.dose", "kind": "medication_dose",
                 "value": "٥٠٠ ملغ", "page": 1, "row_id": "RX-1", "bbox": [200, 10, 320, 30]}
            ]
        }]
    }
    pred = copy.deepcopy(truth)
    pred["engine"] = "FAKE_TEST_PREDICTION_NOT_OCR"
    for field in pred["documents"][0]["fields"]:
        field["review_required"] = False
    return truth, pred


class ScoringContract(unittest.TestCase):
    def test_exact_values_with_correct_evidence(self):
        gold, pred = fixture()
        r = evaluate(gold, pred)
        self.assertEqual(r["fields_exact_and_aligned"], 2)
        self.assertEqual(r["field_exact_rate"], 1)
        self.assertEqual(r["cer_whitespace_ignored"], 0)
        self.assertEqual(r["unsafe_accepted_fields"], 0)
        self.assertEqual(r["invented_extra_field_ids"], 0)
        self.assertIsNone(r["performance"]["peak_vram_mb"])

    def test_same_text_in_wrong_cell_is_not_evidence(self):
        gold, pred = fixture()
        pred["documents"][0]["fields"][0]["row_id"] = "RX-2"
        pred["documents"][0]["fields"][0]["bbox"] = [200, 10, 320, 30]
        r = evaluate(gold, pred)
        self.assertEqual(r["fields_exact"], 2)
        self.assertEqual(r["fields_exact_and_aligned"], 1)
        self.assertEqual(r["unsafe_accepted_fields"], 1)

    def test_wrong_drug_dose_cannot_be_silently_accepted(self):
        gold, pred = fixture()
        pred["documents"][0]["fields"][1]["value"] = "٥٠ ملغ"
        r = evaluate(gold, pred)
        self.assertEqual(r["fields_exact"], 1)
        self.assertEqual(r["unsafe_accepted_fields"], 1)
        self.assertEqual(r["by_kind"]["medication_dose"]["exact"], 0)

    def test_missing_field_is_counted_as_review_and_in_recall_denominator(self):
        gold, pred = fixture()
        pred["documents"][0]["fields"].pop()
        r = evaluate(gold, pred)
        self.assertEqual(r["fields_expected"], 2)
        self.assertEqual(r["fields_exact"], 1)
        self.assertEqual(r["review_or_missing_fields"], 1)
        self.assertEqual(r["unsafe_accepted_fields"], 0)

    def test_abstention_is_not_value_correctness(self):
        gold, pred = fixture()
        pred["documents"][0]["fields"][0]["review_required"] = True
        r = evaluate(gold, pred)
        self.assertEqual(r["fields_exact"], 2)
        self.assertEqual(r["review_or_missing_fields"], 1)

    def test_extra_field_is_counted(self):
        gold, pred = fixture()
        extra = copy.deepcopy(pred["documents"][0]["fields"][0])
        extra["field_id"] = "invented-drug"
        pred["documents"][0]["fields"].append(extra)
        self.assertEqual(evaluate(gold, pred)["invented_extra_field_ids"], 1)

    def test_cross_source_sha_never_scored(self):
        gold, pred = fixture()
        pred["documents"][0]["sha256"] = "b" * 64
        with self.assertRaisesRegex(ValueError, "SOURCE_SHA256_MISMATCH"):
            evaluate(gold, pred)

    def test_repeated_field_id_is_invalid(self):
        gold, pred = fixture()
        pred["documents"][0]["fields"].append(copy.deepcopy(pred["documents"][0]["fields"][0]))
        with self.assertRaisesRegex(ValueError, "Duplicate predicted field"):
            evaluate(gold, pred)

    def test_arabic_digits_are_not_silently_normalized(self):
        self.assertNotEqual(canonical("٥٠٠ ملغ"), canonical("500 ملغ"))


if __name__ == "__main__":
    unittest.main()
