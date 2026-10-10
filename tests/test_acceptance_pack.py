"""Validate portable bilingual handoff references and scenario parity."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAMES = ['MCIAS_MASTER_DESIGN_BASELINE','policies/POLICY_PACK','policies/COVER_LETTER','policies/CLIENT_REQUIREMENTS','DEPLOYMENT_GUIDE','EXTERNAL_TEST_PLAN','EXTERNAL_TEST_REPORT_TEMPLATE','UAT_PLAN','UAT_SCENARIOS','UAT_CHECKLIST','PENETRATION_TEST_PLAN','PENETRATION_TEST_SCOPE']

def test_bilingual_metadata_and_local_links():
    for name in NAMES + ['ACCEPTANCE_PACK_INDEX']:
        ar = ROOT / 'docs' / (name + '.md')
        en = ROOT / 'docs' / (name + '_EN.md')
        texts = [ar.read_text(), en.read_text()]
        assert re.findall(r'MCIAS-[A-Z]+-\d{3}', texts[0]) == re.findall(r'MCIAS-[A-Z]+-\d{3}', texts[1])
        assert re.search('[\u0600-\u06ff]', texts[0])
        for path, body in zip((ar,en), texts):
            assert body.count('```') % 2 == 0
            for link in re.findall(r'\]\(([^)]+)\)', body):
                if '://' in link or link.startswith('#'):
                    continue
                target = (path.parent / link.split('#')[0]).resolve()
                assert target.is_relative_to(ROOT), (path,link)
                assert target.exists(), (path,link)

def test_scenario_identifiers_match_both_languages():
    for name, pattern, count in [('policies/POLICY_PACK',r'FIN-ADR-\d{3}',13),('UAT_SCENARIOS',r'(?<!MCIAS-)UAT-\d{2}(?!\d)',25),('PENETRATION_TEST_SCOPE',r'PT-\d{2}',15)]:
        a=set(re.findall(pattern,(ROOT/'docs'/f'{name}.md').read_text()))
        b=set(re.findall(pattern,(ROOT/'docs'/f'{name}_EN.md').read_text()))
        assert a == b and len(a) == count
