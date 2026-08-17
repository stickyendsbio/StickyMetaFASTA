from __future__ import annotations
import csv, platform
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any
import Bio
from Bio.SeqRecord import SeqRecord
from . import __version__
from .metadata import field_column, field_label, is_available, selected_columns
from .models import ScanResult
from .utils import create_run_folder, result_path


def _pct(n: int, total: int) -> float: return round(n * 100 / total, 2) if total else 0.0


def _write_csv(path: Path, columns: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore"); writer.writeheader(); writer.writerows(rows)


def write_fasta(records: list[SeqRecord], path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            organism = str(record.annotations.get("organism", "")).replace('"', "'").strip()
            handle.write(f">{record.id}" + (f' organism="{organism}"' if organism else "") + "\n")
            sequence = str(record.seq).upper()
            for start in range(0, len(sequence), 70): handle.write(sequence[start:start + 70] + "\n")


def export_results(result: ScanResult, *, rule: str, base_dir: Path, query_term: str, include_fasta: bool,
                   limit: int | None, search_term: str, organism: str, minimum_length: int | None,
                   maximum_length: int | None, api_key_used: bool, status: str = "Completed") -> Path:
    indexes = result.qualifying_indexes(rule)
    if limit is not None: indexes = indexes[:limit]
    rows = [result.rows[i] for i in indexes]; records = [result.records[i] for i in indexes]
    folder = create_run_folder(base_dir, query_term)
    _write_csv(result_path(folder, "qualifying_records.csv"), selected_columns(result.selected_fields), rows)
    availability = [{"Metadata_Field": field_label(f), "Available_Count": result.availability[f],
        "Missing_Count": result.inspected-result.availability[f], "Availability_Percentage": _pct(result.availability[f], result.inspected)}
        for f in result.selected_fields]
    availability += [{"Metadata_Field": "All selected metadata fields", "Available_Count": result.all_count,
        "Missing_Count": result.inspected-result.all_count, "Availability_Percentage": _pct(result.all_count, result.inspected)},
        {"Metadata_Field": "At least one selected metadata field", "Available_Count": result.any_count,
        "Missing_Count": result.inspected-result.any_count, "Availability_Percentage": _pct(result.any_count, result.inspected)}]
    _write_csv(result_path(folder, "metadata_availability.csv"),
               ["Metadata_Field", "Available_Count", "Missing_Count", "Availability_Percentage"], availability)
    for field in result.selected_fields:
        column = field_column(field); counts: Counter[str] = Counter()
        for row in rows:
            raw = str(row.get(column, "")).strip()
            counts.update(dict.fromkeys(
                [v.strip() for v in raw.split(";") if v.strip()]
                if is_available(raw)
                else ["Not provided"]
            ).keys())
        values = [{"Metadata_Field": field_label(field), "Value": value, "Sequence_Count": count,
                   "Percentage_of_Qualifying_Records": _pct(count, len(rows))}
                  for value, count in sorted(counts.items(), key=lambda item: (-item[1], item[0].casefold()))]
        _write_csv(result_path(folder, f"values_{field}.csv"),
                   ["Metadata_Field", "Value", "Sequence_Count", "Percentage_of_Qualifying_Records"], values)
    combo_columns = [field_column(f) for f in result.selected_fields]; combos: Counter[tuple[str, ...]] = Counter()
    for row in rows: combos[tuple(str(row.get(c, "")).strip() or "Not provided" for c in combo_columns)] += 1
    combo_rows = [dict(zip(combo_columns, values)) | {"Sequence_Count": count,
                  "Percentage_of_Qualifying_Records": _pct(count, len(rows))} for values, count in combos.most_common()]
    _write_csv(result_path(folder, "metadata_combinations.csv"),
               combo_columns + ["Sequence_Count", "Percentage_of_Qualifying_Records"], combo_rows)
    if include_fasta: write_fasta(records, result_path(folder, "sequences.fasta"))
    result_path(folder, "query_settings.txt").write_text("\n".join([
        "STICKY METAFASTA QUERY SETTINGS", "="*34, f"Version: {__version__}", f"Search term: {search_term}",
        f"Organism: {organism or 'Not specified'}", f"Full NCBI query: {result.query}",
        f"Minimum length: {minimum_length or 'Not set'}", f"Maximum length: {maximum_length or 'Not set'}",
        f"Selected metadata: {', '.join(field_label(f) for f in result.selected_fields)}",
        f"Matching rule: {'All selected fields' if rule == 'all' else 'At least one selected field'}",
        f"API key used: {'Yes' if api_key_used else 'No'}"]) + "\n", encoding="utf-8")
    result_path(folder, "summary.txt").write_text("\n".join([
        "STICKY METAFASTA SUMMARY", "="*28, f"Status: {status}",
        f"Run time: {datetime.now().astimezone().isoformat(timespec='seconds')}", f"Total NCBI matches: {result.total_matches}",
        f"Records fetched: {result.fetched}", f"Length-eligible records: {result.inspected}",
        f"Length-excluded records: {result.length_excluded}", f"Duplicate versions skipped: {result.duplicates}",
        f"Undefined sequences: {result.undefined_sequences}", f"Retrieval failures: {result.retrieval_failures}",
        f"All-fields count: {result.all_count}", f"At-least-one count: {result.any_count}",
        f"Exported CSV rows: {len(rows)}", f"Exported FASTA sequences: {len(records) if include_fasta else 0}",
        f"Python: {platform.python_version()}", f"Biopython: {Bio.__version__}", f"Operating system: {platform.platform()}"]) + "\n", encoding="utf-8")
    result_path(folder, "log.txt").write_text("Sticky MetaFASTA export completed.\n", encoding="utf-8")
    return folder
