from __future__ import annotations
import getpass, logging
from pathlib import Path
from . import __version__
from .config import SETTINGS, with_credentials
from .metadata import METADATA_FIELDS, field_label
from .ncbi import NCBIClient
from .output import export_results
from .scanner import build_query, scan_history, validate_lengths


def _optional_int(prompt: str) -> int | None:
    while True:
        raw = input(prompt).strip()
        if not raw: return None
        try:
            value = int(raw)
            if value > 0: return value
        except ValueError: pass
        print("Enter a positive whole number, or press Enter for no limit.")


def _yes(prompt: str) -> bool: return input(prompt).strip().casefold() in {"y", "yes"}


def main() -> None:
    print(f"Sticky MetaFASTA v{__version__}\nNCBI metadata scanner & FASTA downloader\n")
    email = SETTINGS.email or input("NCBI email ID: ").strip()
    if not email: raise SystemExit("An NCBI email ID is required.")
    api_key = SETTINGS.api_key or getpass.getpass("NCBI API key (optional): ").strip()
    search_term = input("Query / search term: ").strip(); organism = input("Organism (optional): ").strip()
    query = build_query(search_term, organism)
    minimum = _optional_int("Minimum nucleotide length (optional): "); maximum = _optional_int("Maximum nucleotide length (optional): ")
    validate_lengths(minimum, maximum); keys = list(METADATA_FIELDS)
    print("\nMetadata fields:")
    for n, key in enumerate(keys, 1): print(f"  {n}. {field_label(key)}")
    while True:
        try:
            numbers = sorted({int(v.strip()) for v in input("Select metadata numbers (comma-separated): ").split(",")})
            fields = [keys[n-1] for n in numbers if 1 <= n <= len(keys)]
            if fields and len(fields) == len(numbers): break
        except ValueError: pass
        print("Select at least one valid metadata number.")
    rule = "any" if input("Matching rule - 1 All, 2 At least one [1]: ").strip() == "2" else "all"
    logger = logging.getLogger("sticky_metafasta_cli"); logger.addHandler(logging.NullHandler())
    settings = with_credentials(SETTINGS, email, api_key); client = NCBIClient(settings, logger, status_callback=lambda m: print(f"\n{m}"))
    history = client.search_history(query)
    if not history.count: print("No exact matches were found in NCBI."); return
    print(f"NCBI matches: {history.count:,}")
    if history.count >= settings.large_warning_threshold: print("Warning: this large scan may require substantial time and storage.")
    if not _yes("Continue scanning? [y/N]: "): return
    def progress(r):
        q = r.all_count if rule == "all" else r.any_count
        print(f"\rFetched {r.fetched:,}/{r.total_matches:,} | Inspected {r.inspected:,} | Qualifying {q:,}", end="", flush=True)
    result = scan_history(client=client, history=history, settings=settings, query=query, selected_fields=fields,
                          minimum_length=minimum, maximum_length=maximum, logger=logger, progress_callback=progress)
    print(f"\n\nAll selected fields: {result.all_count:,}\nAt least one selected field: {result.any_count:,}")
    include_fasta = _yes("Download FASTA plus data files? [y/N] (No creates CSV reports): ")
    limit = None
    qualifying = result.all_count if rule == "all" else result.any_count
    if include_fasta and not _yes(f"Download all {qualifying:,} qualifying sequences? [y/N]: "):
        limit = _optional_int("Number to download: ")
    base = Path(input("Results location [Results]: ").strip() or "Results")
    folder = export_results(result, rule=rule, base_dir=base, query_term=search_term, include_fasta=include_fasta,
        limit=limit, search_term=search_term, organism=organism, minimum_length=minimum, maximum_length=maximum,
        api_key_used=bool(api_key)); print(f"Results saved to: {folder.resolve()}")


if __name__ == "__main__": main()
