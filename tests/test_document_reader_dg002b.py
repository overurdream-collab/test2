"""DG-002B separate generator, OCR word association and source scorer checks (synthetic)."""
import hashlib, json, tempfile, unittest
from pathlib import Path
from scripts.document_reader_dg002b_benchmark import FIXTURES, make_fixtures, associate_fields, sha
from scripts.document_reader_dg002_score import evaluate

class DG002B(unittest.TestCase):
    def test_frozen_assets_are_deterministic(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            x=make_fixtures(a);y=make_fixtures(b)
            self.assertEqual(len(x),8)
            self.assertEqual(x,y)
            for item in x:
                self.assertEqual(sha((Path(a)/item['image']).read_bytes()),item['image_sha256'])
                self.assertEqual(sha((Path(a)/item['pdf']).read_bytes()),item['pdf_sha256'])
    def test_four_categories_in_both_languages(self):
        with tempfile.TemporaryDirectory() as path:
            manifest=make_fixtures(path)
            self.assertEqual({(i["category"],i["language"]) for i in manifest},
                             {(c,l) for c in ("invoice","laboratory","radiology","prescription") for l in ("en","ar")})
            docs=json.loads((Path(path)/"gold.json").read_text())["documents"]
            self.assertEqual(sum(len(d['fields']) for d in docs),30)
            self.assertTrue(all(len(d['sha256'])==64 for d in docs))
            self.assertTrue(all(f['page']==1 and f['bbox'][2]>f['bbox'][0] for d in docs for f in d['fields']))
    def test_no_gold_used_by_ocr_association(self):
        tokens=[
            {"text":"DRUG","bbox":[65,200,180,240],"line_key":(1,1,1),"confidence_uncalibrated":99.},
            {"text":"Amoxicillin","bbox":[435,200,670,240],"line_key":(1,1,1),"confidence_uncalibrated":70.}
        ]
        pred=associate_fields(tokens)
        self.assertEqual(pred[0]['field_id'],"drug")
        self.assertEqual(pred[0]['value'],"Amoxicillin")
        self.assertEqual(pred[0]['bbox'],[435,200,670,240])
        self.assertTrue(pred[0]['review_required'])
    def test_arabic_tokens_use_rtl_reading_order(self):
        words=[
          {"text":"DRUG","bbox":[65,300,190,350],"line_key":(1,1,2),"confidence_uncalibrated":90.},
          {"text":"واحدة","bbox":[600,300,710,350],"line_key":(1,1,2),"confidence_uncalibrated":86.},
          {"text":"كبسولة","bbox":[790,300,910,350],"line_key":(1,1,2),"confidence_uncalibrated":88.}
        ]
        self.assertEqual(associate_fields(words,"ar")[0]["value"],"كبسولة واحدة")
        self.assertEqual(associate_fields(words,"en")[0]["value"],"واحدة كبسولة")

    def test_swapped_label_and_region_is_not_success(self):
        with tempfile.TemporaryDirectory() as path:
            make_fixtures(path)
            gold=json.loads((Path(path)/"gold.json").read_text())
            first=gold['documents'][0]
            pred={'engine':'FAKE_UNIT_TEST','documents':[dict(first)]}
            pred['documents'][0]['fields']=[dict(f,review_required=False) for f in first['fields']]
            pred['documents'][0]['fields'][0]['bbox']=[0,0,20,20]
            report=evaluate({"documents":[first]},pred)
            self.assertEqual(report['fields_exact'],4)
            self.assertEqual(report['fields_exact_and_aligned'],3)
            self.assertEqual(report['unsafe_accepted_fields'],1)
    def test_unsupported_sha_must_fail(self):
        with tempfile.TemporaryDirectory() as path:
            make_fixtures(path)
            doc=json.loads((Path(path)/"gold.json").read_text())['documents'][0]
            pred={'documents':[dict(doc,sha256="b"*64)]}
            with self.assertRaisesRegex(ValueError,"SOURCE_SHA256_MISMATCH"):
                evaluate({'documents':[doc]},pred)

if __name__=="__main__": unittest.main()
