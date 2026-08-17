from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from Bio.SeqRecord import SeqRecord


@dataclass
class ScanResult:
    query: str
    selected_fields: list[str]
    total_matches: int
    rows: list[dict[str, Any]] = field(default_factory=list)
    records: list[SeqRecord] = field(default_factory=list)
    fetched: int = 0
    inspected: int = 0
    length_excluded: int = 0
    duplicates: int = 0
    retrieval_failures: int = 0
    undefined_sequences: int = 0
    interrupted: bool = False
    availability: Counter[str] = field(default_factory=Counter)
    all_count: int = 0
    any_count: int = 0

    def qualifying_indexes(self, rule: str) -> list[int]:
        from .metadata import qualifies
        return [i for i, row in enumerate(self.rows) if qualifies(row, self.selected_fields, rule)]

    def qualifying_rows(self, rule: str) -> list[dict[str, Any]]:
        return [self.rows[i] for i in self.qualifying_indexes(rule)]

    def qualifying_records(self, rule: str) -> list[SeqRecord]:
        return [self.records[i] for i in self.qualifying_indexes(rule)]
