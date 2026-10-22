"""Independent metadata-role checks; no fixture gold enters the parser."""
from scripts.document_reader_dynamic_layout_pilot import meta_fields


def lines(*texts):
    output=[]
    for row,text in enumerate(texts):
        words=[];x=130
        for token in text.split():
            words.append({'text':token,'bbox':[x,90+row*80,x+len(token)*13,122+row*80],
                          'confidence_uncalibrated':0.91})
            x+=len(token)*13+20
        output.append({'words':words})
    return output


def parse(*texts):
    source=lines(*texts)
    return meta_fields(source,len(source),'SYN-HOLDOUT','a'*64)


def test_effective_date_is_not_bound_to_service_date_when_it_comes_first():
    fields,_=parse('EFFECTIVE_FROM 2025-12-01','SERVICE_DATE 2026-04-09')
    assert fields['date']['value']=='2026-04-09'
    assert fields['service_date']['value']=='2026-04-09'
    assert fields['effective_from']['value']=='2025-12-01'
    assert fields['service_date']['semantic_role']=='service_date'
    assert fields['effective_from']['source_line']==1
    assert fields['service_date']['source_line']==2


def test_explicit_provider_code_is_not_a_fixture_specific_constant():
    fields,_=parse('PROVIDER SYN-HOSPITAL-42')
    assert fields['provider']['value']=='SYN-HOSPITAL-42'
    assert fields['provider']['semantic_role']=='provider_code'
    assert fields['provider']['source']['sha256']=='a'*64


def test_repeated_provider_identity_does_not_choose_a_source_region():
    fields,issues=parse('PROVIDER SYNCLINIC','PROVIDER SYNCLINIC')
    assert 'provider' not in fields
    assert 'AMBIGUOUS_METADATA_provider' in issues


def test_conflicting_service_dates_abstain_even_when_both_are_valid_iso_dates():
    fields,issues=parse('SERVICE_DATE 2026-04-09','SERVICE_DATE 2026-04-10')
    assert 'service_date' not in fields and 'date' not in fields
    assert 'AMBIGUOUS_METADATA_service_date' in issues


def test_unlabelled_date_is_not_claim_service_date():
    fields,issues=parse('REFERENCE 2026-04-09')
    assert 'date' not in fields and 'service_date' not in fields
    assert 'UNLABELLED_METADATA_DATE' in issues


def test_generic_document_date_is_retained_without_medical_service_authority():
    fields,_=parse('DATE 2026-04-09')
    assert fields['date']['value']=='2026-04-09'
    assert fields['document_date']['semantic_role']=='document_date'
    assert 'service_date' not in fields
    assert fields['date']['status']=='UNATTESTED_OCR_CANDIDATE'


def test_effective_until_and_repeated_amount_values_keep_separate_source_lines():
    fields,_=parse('EFFECTIVE_UNTIL 2026-10-01','GRANDTOTAL 42.00','SERVICE_DATE 2026-04-09')
    assert fields['effective_until']['value']=='2026-10-01'
    assert fields['stated_total']['value']=='42.00'
    assert fields['effective_until']['source_line']!=fields['stated_total']['source_line']


def test_arabic_source_label_is_preserved_during_anchoring():
    fields,_=parse('PROVIDER SYN-42','التاريخ 2026-04-09')
    assert fields['provider']['value']=='SYN-42'
    assert fields['document_date']['source_label']=='التاريخ'


def test_generic_date_and_ambiguous_metadata_block_existing_a1_payload():
    from scripts.document_reader_dynamic_layout_pilot import a1_block_reasons,a1_payload
    fields,_=parse('DATE 2026-04-09')
    parsed={'fields':fields,'rows':[{}],'issues':[]}
    assert a1_payload(parsed,'generic-date') is None
    assert a1_block_reasons(parsed)==['SERVICE_DATE_NOT_EXPLICIT']
    assert a1_payload({'fields':{'service_date':{'semantic_role':'service_date'}},
                       'rows':[{}],'issues':['AMBIGUOUS_METADATA_provider']},'ambiguous') is None


def test_existing_reviewed_advisory_retains_reason_and_does_not_call_a1(monkeypatch):
    from types import SimpleNamespace
    from unittest.mock import patch
    from pathlib import Path
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]/"scripts"))
    from scripts import reader_g2_audit_a1_pg16_contract as bridge
    row={k:{'value':v} for k,v in {'id':'QA','code':'LAB','unit':'EA','qty':'1','price':'42.00','total':'42.00'}.items()}
    parsed={'fields':{},'rows':[row],'issues':[]}
    a1=SimpleNamespace(analyze=lambda _:(_ for _ in ()).throw(AssertionError('A1 must remain blocked')))
    with patch.object(bridge,'qualified',return_value=(([],{'QA':{k:v['value'] for k,v in row.items()}}),[])):
        report=bridge.advisory(None,None,None,'SYN',parsed,a1)
    assert report['blocked']==['SERVICE_DATE_NOT_EXPLICIT']
    assert report['financial_decision']=='NOT_AUTHORIZED'
