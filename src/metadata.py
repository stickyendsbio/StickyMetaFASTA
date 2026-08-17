from __future__ import annotations

import re
from typing import Any
from Bio.Seq import UndefinedSequenceError
from Bio.SeqRecord import SeqRecord

METADATA_FIELDS = {
    "organism": ("Organism", "Organism"), "collection_date": ("Collection date", "Collection_Date"),
    "collection_year": ("Collection year", "Collection_Year"),
    "geographic_location": ("Geographic location / country", "Geographic_Location"),
    "host": ("Host", "Host"), "isolation_source": ("Isolation source", "Isolation_Source"),
    "strain": ("Strain", "Strain"), "isolate": ("Isolate", "Isolate"),
    "breed": ("Breed", "Breed"), "biosample": ("BioSample accession", "BioSample"),
    "bioproject": ("BioProject accession", "BioProject"),
}
BASE_COLUMNS = ["Accession", "Version", "Description", "Organism", "Sequence_Length",
                "Publication_Associated", "Direct_Submission", "Reference_Category", "NCBI_Record_Link"]
MISSING_MARKERS = {"", "not provided", "unknown", "missing", "not applicable", "n/a", "na", "none", "not available", "unspecified"}


def _values(q: dict[str, list[str]], key: str) -> str:
    return "; ".join(dict.fromkeys(str(v).strip() for v in q.get(key, []) if str(v).strip()))


def _source(record: SeqRecord) -> dict[str, list[str]]:
    return next((f.qualifiers for f in record.features if f.type == "source"), {})


def _xref(q: dict[str, list[str]], prefix: str) -> str:
    found = [str(v).split(":", 1)[1].strip() for v in q.get("db_xref", [])
             if str(v).casefold().startswith(prefix.casefold() + ":")]
    return "; ".join(dict.fromkeys(found))


def reference_classification(record: SeqRecord) -> tuple[str, str, str]:
    publication = direct = False
    for ref in record.annotations.get("references", []) or []:
        title = str(getattr(ref, "title", "") or "").strip()
        journal = str(getattr(ref, "journal", "") or "").strip()
        pubmed = str(getattr(ref, "pubmed_id", "") or "").strip()
        if "direct submission" in title.casefold() or journal.casefold().startswith("submitted"):
            direct = True
        elif title or journal or pubmed:
            publication = True
    category = ("Publication and direct submission" if publication and direct else
                "Publication" if publication else "Direct submission" if direct else "Not identified")
    return "Yes" if publication else "No", "Yes" if direct else "No", category


def sequence_is_defined(record: SeqRecord) -> bool:
    try:
        return bool(str(record.seq).strip())
    except UndefinedSequenceError:
        return False


def extract_metadata(record: SeqRecord) -> dict[str, Any]:
    q = _source(record); date = _values(q, "collection_date")
    location = _values(q, "geo_loc_name") or _values(q, "country")
    publication, direct, category = reference_classification(record); version = record.id
    year = re.search(r"\b(?:18|19|20)\d{2}\b", date)
    return {"Accession": version.split(".")[0], "Version": version, "Description": record.description,
        "Organism": str(record.annotations.get("organism", "")).strip(), "Sequence_Length": len(record.seq),
        "Collection_Date": date, "Collection_Year": year.group(0) if year else "", "Geographic_Location": location,
        "Host": _values(q, "host"), "Isolation_Source": _values(q, "isolation_source"),
        "Strain": _values(q, "strain"), "Isolate": _values(q, "isolate"), "Breed": _values(q, "breed"),
        "BioSample": _xref(q, "BioSample"), "BioProject": _values(q, "bio_project") or _xref(q, "BioProject"),
        "Publication_Associated": publication, "Direct_Submission": direct, "Reference_Category": category,
        "NCBI_Record_Link": f"https://www.ncbi.nlm.nih.gov/nuccore/{version}"}


def field_column(field: str) -> str: return METADATA_FIELDS[field][1]
def field_label(field: str) -> str: return METADATA_FIELDS[field][0]
def is_available(value: Any) -> bool: return str(value if value is not None else "").strip().casefold() not in MISSING_MARKERS


def qualifies(row: dict[str, Any], fields: list[str], rule: str) -> bool:
    flags = [is_available(row.get(field_column(field), "")) for field in fields]
    return all(flags) if rule == "all" else any(flags)


def selected_columns(fields: list[str]) -> list[str]:
    columns = list(BASE_COLUMNS)
    for field in fields:
        if field_column(field) not in columns: columns.append(field_column(field))
    return columns
