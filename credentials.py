# Sticky MetaFASTA
# Copyright (C) 2026 Sticky Ends Bio Private Limited
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def credentials_path() -> Path:
    if sys.platform == "darwin":
        return (
            Path.home()
            / "Library"
            / "Application Support"
            / "Sticky MetaFASTA"
            / "credentials.json"
        )
    base = os.getenv("APPDATA", "").strip()
    if os.name != "nt" and not base:
        return Path.home() / ".config" / "sticky-metafasta" / "credentials.json"
    root = Path(base) if base else Path.home() / "AppData" / "Roaming"
    return root / "Sticky MetaFASTA" / "credentials.json"


def load_credentials(path: Path | None = None) -> tuple[str, str]:
    target = path or credentials_path()
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return "", ""
    if not isinstance(data, dict):
        return "", ""
    return (
        str(data.get("email", "")).strip(),
        str(data.get("api_key", "")).strip(),
    )


def save_credentials(
    email: str,
    api_key: str,
    path: Path | None = None,
) -> None:
    target = path or credentials_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(
            {"email": email.strip(), "api_key": api_key.strip()},
            indent=2,
        ),
        encoding="utf-8",
    )


def clear_credentials(path: Path | None = None) -> None:
    target = path or credentials_path()
    try:
        target.unlink()
    except FileNotFoundError:
        pass

