from __future__ import annotations
import logging
from collections.abc import Callable
from .config import Settings
from .metadata import extract_metadata, field_column, is_available, qualifies, sequence_is_defined
from .models import ScanResult
from .ncbi import NCBIClient, SearchHistory


def build_query(search_term: str, organism: str = "") -> str:
    query = search_term.strip()
    if not query: raise ValueError("Query/search term is required.")
    return f'({query}) AND "{organism.strip()}"[Organism]' if organism.strip() else query


def validate_lengths(minimum: int | None, maximum: int | None) -> None:
    if minimum is not None and minimum <= 0: raise ValueError("Minimum nucleotide length must be positive.")
    if maximum is not None and maximum <= 0: raise ValueError("Maximum nucleotide length must be positive.")
    if minimum is not None and maximum is not None and minimum > maximum:
        raise ValueError("Minimum nucleotide length cannot exceed maximum length.")


def scan_history(*, client: NCBIClient, history: SearchHistory, settings: Settings, query: str,
                 selected_fields: list[str], logger: logging.Logger, minimum_length: int | None = None,
                 maximum_length: int | None = None, progress_callback: Callable[[ScanResult], None] | None = None,
                 should_stop: Callable[[], bool] | None = None) -> ScanResult:
    if not selected_fields: raise ValueError("Select at least one metadata field.")
    validate_lengths(minimum_length, maximum_length)
    result = ScanResult(query=query, selected_fields=selected_fields, total_matches=history.count); seen: set[str] = set()
    for retstart in range(0, history.count, settings.batch_size):
        if should_stop and should_stop(): result.interrupted = True; break
        try:
            records = client.fetch_genbank_batch(history, retstart=retstart, retmax=settings.batch_size)
        except Exception:
            result.retrieval_failures += min(settings.batch_size, history.count - retstart)
            logger.exception("Failed to retrieve batch beginning at %s", retstart); continue
        result.fetched += len(records)
        for record in records:
            if should_stop and should_stop(): result.interrupted = True; break
            if record.id in seen: result.duplicates += 1; continue
            seen.add(record.id)
            if not sequence_is_defined(record): result.undefined_sequences += 1; continue
            row = extract_metadata(record); length = int(row["Sequence_Length"])
            if ((minimum_length is not None and length < minimum_length) or
                    (maximum_length is not None and length > maximum_length)):
                result.length_excluded += 1; continue
            result.inspected += 1; result.rows.append(row); result.records.append(record)
            for field in selected_fields:
                if is_available(row.get(field_column(field), "")): result.availability[field] += 1
            if qualifies(row, selected_fields, "all"): result.all_count += 1
            if qualifies(row, selected_fields, "any"): result.any_count += 1
        if progress_callback: progress_callback(result)
        if result.interrupted: break
    return result
