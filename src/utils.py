# Sticky MetaFASTA
# Copyright (C) 2026 Sticky Ends Bio Private Limited
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import logging
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, TypeVar

T = TypeVar("T")


def sanitize_query_term(query_term: str, *, maximum_length: int = 60) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", query_term.strip())
    cleaned = cleaned.strip("._-")
    return (cleaned[:maximum_length].rstrip("._-") or "query")


def create_run_folder(base_dir: Path, query_term: str = "") -> Path:
    base_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    query_label = sanitize_query_term(query_term)
    folder_stem = f"{timestamp}_{query_label}"
    candidate = base_dir / folder_stem
    suffix = 1

    while candidate.exists():
        candidate = base_dir / f"{folder_stem}_{suffix}"
        suffix += 1

    candidate.mkdir(parents=True)
    return candidate


def run_timestamp(run_folder: Path) -> str:
    match = re.match(r"\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}", run_folder.name)
    if not match:
        raise ValueError(
            f"Results folder does not begin with a timestamp: {run_folder.name}"
        )
    return match.group(0)


def timestamped_filename(run_folder: Path, filename: str) -> str:
    return f"{run_timestamp(run_folder)}_{filename}"


def result_path(run_folder: Path, filename: str) -> Path:
    return run_folder / timestamped_filename(run_folder, filename)


def setup_logger(log_file: Path) -> logging.Logger:
    logger = logging.getLogger("sticky_metafasta")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler = logging.FileHandler(log_file, encoding="utf-8")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


def retry(
    func: Callable[[], T],
    *,
    attempts: int,
    base_wait_seconds: float,
    description: str,
    logger: logging.Logger,
    status_callback: Callable[[str], None] | None = None,
) -> T:
    last_error: Exception | None = None

    for attempt in range(1, attempts + 1):
        try:
            return func()
        except KeyboardInterrupt:
            raise
        except Exception as exc:
            last_error = exc
            logger.warning(
                "%s failed on attempt %s/%s: %s",
                description,
                attempt,
                attempts,
                exc,
            )
            if attempt < attempts:
                wait_seconds = base_wait_seconds * attempt
                status_message = (
                    f"{description} failed: {type(exc).__name__}: {exc}. "
                    f"Retrying in {wait_seconds:.0f} seconds "
                    f"(attempt {attempt + 1}/{attempts})."
                )
                if status_callback is not None:
                    status_callback(status_message)
                print(
                    "\nSTATUS: NCBI/network request failed\n"
                    f"Operation: {description}\n"
                    f"Error: {type(exc).__name__}: {exc}\n"
                    f"Retrying in {wait_seconds:.0f} seconds "
                    f"- attempt {attempt + 1} of {attempts}...",
                    flush=True,
                )
                time.sleep(wait_seconds)

    final_message = (
        "Unable to complete the NCBI/network request after "
        f"{attempts} attempts."
    )
    if status_callback is not None:
        status_callback(final_message)
    print(
        f"\nSTATUS: {final_message}",
        flush=True,
    )
    raise RuntimeError(
        f"{description} failed after {attempts} attempts: {last_error}"
    )


def extract_year(text: str) -> str:
    match = re.search(r"\b(?:18|19|20)\d{2}\b", text or "")
    return match.group(0) if match else ""


def format_duration(seconds: float) -> str:
    total = max(0, int(seconds))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def mask_email(email: str) -> str:
    if "@" not in email:
        return "Configured"
    local, domain = email.split("@", 1)
    if len(local) <= 2:
        masked_local = local[:1] + "*"
    else:
        masked_local = local[:2] + "*" * max(1, len(local) - 2)
    return f"{masked_local}@{domain}"


def format_length_range(
    minimum_length: int | None,
    maximum_length: int | None,
) -> str:
    if minimum_length is None and maximum_length is None:
        return "No restriction"
    if minimum_length is not None and maximum_length is not None:
        return f"{minimum_length:,}-{maximum_length:,} nt (inclusive)"
    if minimum_length is not None:
        return f"Minimum {minimum_length:,} nt (inclusive)"
    return f"Maximum {maximum_length:,} nt (inclusive)"

