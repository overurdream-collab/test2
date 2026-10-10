"""G2 OCR golden-set evaluation: character error rate and exact transcription."""
from dataclasses import dataclass
from difflib import SequenceMatcher

@dataclass(frozen=True)
class OCRScore:
    character_error_rate: float
    exact_matches: int
    samples: int

def score(pairs: list[tuple[str, str]]) -> OCRScore:
    if not pairs:
        raise ValueError("golden dataset required")
    errors = 0
    total = 0
    matches = 0
    for expected, actual in pairs:
        if not isinstance(expected, str) or not isinstance(actual, str):
            raise ValueError("text required")
        matches += expected == actual
        total += len(expected)
        matcher = SequenceMatcher(None, expected, actual, autojunk=False)
        errors += sum(max(i2-i1, j2-j1) if tag == "replace" else (i2-i1 if tag == "delete" else j2-j1)
                      for tag, i1, i2, j1, j2 in matcher.get_opcodes() if tag != "equal")
    return OCRScore(errors / max(total, 1), matches, len(pairs))
