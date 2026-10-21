"""Typed immutable extraction records and source locators."""
from dataclasses import dataclass, field

@dataclass(frozen=True)
class Locator:
    kind: str
    index: int
    row: int | None = None
    column: int | None = None
    sheet_name: str | None = None

@dataclass(frozen=True)
class ExtractedRecord:
    locator: Locator
    values: dict[str, str]
    confidence: float = 1.0

@dataclass
class Extraction:
    format: str
    records: list[ExtractedRecord] = field(default_factory=list)
    units_total: int = 0
    units_processed: int = 0
    quarantined: list[dict] = field(default_factory=list)
    worksheet_inventory: list[dict] = field(default_factory=list)

    @property
    def complete(self):
        return self.units_total == self.units_processed + len(self.quarantined)
