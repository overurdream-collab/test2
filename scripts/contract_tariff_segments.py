"""Strictly optional synthetic-benchmark tariff segmentation, preserving literal source spans.
No gold values, model output or target prices are used for segmentation.
"""
import re
from mcias.contract_intelligence import make_source_blocks

# Only split complete, independently identifiable, source-literal provider tariff clauses.
# Fail closed to the unchanged full record on ambiguity, missing amounts or overlap.
CLAUSE = re.compile(
    r"Provider\s+(?P<provider>[A-Za-z0-9_]+)\s+(?P<service>[A-Za-z0-9_]+)\s+"
    r"(?P<amount>\d+(?:\.\d{1,4})?)\s+(?P<currency>[A-Z]{3})\s+"
    r"from\s+\d{4}-\d{2}-\d{2}\s+until\s+\d{4}-\d{2}-\d{2}\.",
    re.ASCII,
)

def isolated_tariff_blocks(case):
    original = case["source"]
    default = make_source_blocks([{"id":case["id"],"locator":case.get("locator",{"kind":"page","index":1}),
                                   "values":case.get("values",{"text":original})}])
    # Only page text; never transform sheets, negatives, Arabic clauses or unmatched text.
    if "values" in case or case.get("locator",{}).get("kind","page") != "page":
        return [default]
    matches = list(CLAUSE.finditer(original))
    if len(matches) < 2 or original[:matches[0].start()].strip() or original[matches[-1].end():].strip():
        return [default]
    if any(original[a.end():b.start()].strip() for a,b in zip(matches,matches[1:])):
        return [default]
    identities = [(m["provider"],m["service"]) for m in matches]
    if len(set(identities)) != len(identities):
        return [default]
    parts = []
    for n,m in enumerate(matches,1):
        locator={**default[0]["locator"],"source_start":m.start(),"source_end":m.end(),"segment_index":n}
        parts.append(make_source_blocks([{"id":case["id"],"locator":locator,
                                         "values":{"text":original[m.start():m.end()]}}]))
    return parts
