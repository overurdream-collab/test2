"""Independent source-region and TSV failure checks; no Gold in association."""
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from scripts.document_reader_dg002b_benchmark import associate_source_regions, tesseract_run


def word(text,box,row=(1,1,1)):
    return {"text":text,"bbox":box,"line_key":row,"confidence_uncalibrated":87.5}


def regions(words,language="en"):
    return associate_source_regions(words,language,source_sha256="a"*64,page_size=(1280,1040))


def test_missing_tsv_config_cannot_silently_become_zero_fields():
    response=SimpleNamespace(returncode=0,stdout=b"MEDICAL INVOICE\nQUANTITY 2",stderr=b"")
    with patch("scripts.document_reader_dg002b_benchmark.subprocess.run",return_value=response) as run:
        with pytest.raises(RuntimeError,match="TSV_FORMAT_INVALID"):
            tesseract_run(b"synthetic", "en")
    assert "tessedit_create_tsv=1" in run.call_args.args[0]


def test_shifted_label_uses_observed_label_boundary_instead_of_fixed_column():
    fields,issues=regions([word("DRUG",[380,200,500,230]),word("Amoxicillin",[650,200,860,230])])
    assert not issues and len(fields)==1
    field=fields[0]
    assert field["value"]=="Amoxicillin"
    assert field["glyph_bbox"]==[650,200,860,230]
    assert field["bbox"][0]>500
    assert field["source_sha256"]=="a"*64
    assert field["review_required"] and not field["g2_native_rows_verified"]
    assert field["financial_decision"]=="NOT_AUTHORIZED"


def test_small_glyph_region_keeps_bounded_visible_context():
    fields,_=regions([word("QUANTITY",[60,348,245,377]),word("2",[438,348,456,377])])
    field=fields[0]
    assert field["glyph_bbox"]==[438,348,456,377]
    assert field["bbox"]==[432,342,462,383]
    assert field["bbox"]!=[0,0,1280,1040]


def test_arabic_visible_token_order_is_retained_without_rewriting_digits():
    fields,_=regions([word("DOSE",[60,200,180,230]),word("واحدة",[600,200,710,230]),
        word("كبسولة",[790,200,910,230])],"ar")
    assert fields[0]["value"]=="كبسولة واحدة"
    assert fields[0]["value_normalized"] is None


def test_multiple_labels_on_one_row_abstain_instead_of_joining_values():
    fields,issues=regions([word("QUANTITY",[60,200,245,230]),word("2",[340,200,360,230]),
        word("AMOUNT",[600,200,750,230]),word("2",[900,200,920,230])])
    assert fields==[]
    assert issues[0]["reason_code"]=="AMBIGUOUS_LABEL_ROW"


def test_repeated_field_on_two_rows_is_not_merged_by_matching_value():
    words=[word("DRUG",[60,200,180,230]),word("A",[400,200,420,230]),
        word("DRUG",[60,400,180,430],(1,1,2)),word("A",[400,400,420,430],(1,1,2))]
    fields,issues=regions(words)
    assert fields==[]
    assert issues==[{"field_id":"drug","reason_code":"MULTIPLE_FIELD_REGIONS"}]


def test_whole_page_value_region_is_unqualified():
    fields,issues=regions([word("DRUG",[10,200,180,230]),word("A",[190,0,1280,1040])])
    assert fields==[]
    assert issues[0]["reason_code"]=="REGION_NOT_FIELD_SPECIFIC"


def test_outside_image_token_is_rejected():
    with pytest.raises(ValueError,match="SOURCE_BOX_INVALID"):
        regions([word("A",[-1,0,1280,100])])
