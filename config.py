from __future__ import annotations

import os
from dataclasses import dataclass, replace


def _positive_int(name: str, default: int) -> int:
    try:
        value = int(os.getenv(name, ""))
    except ValueError:
        return default
    return value if value > 0 else default


@dataclass(frozen=True)
class Settings:
    email: str = os.getenv("NCBI_EMAIL", "").strip()
    api_key: str = os.getenv("NCBI_API_KEY", "").strip()
    database: str = "nucleotide"
    batch_size: int = _positive_int("STICKY_METAFASTA_BATCH_SIZE", 100)
    large_warning_threshold: int = _positive_int("STICKY_METAFASTA_LARGE_WARNING", 5000)
    retry_count: int = 5
    retry_base_wait_seconds: float = 2.0
    network_timeout_seconds: int = 45
    heartbeat_seconds: int = 5
    delay_with_api_key_seconds: float = 0.12
    delay_without_api_key_seconds: float = 0.34
    missing_value_label: str = "Not provided"


SETTINGS = Settings()


def with_credentials(settings: Settings, email: str, api_key: str) -> Settings:
    return replace(settings, email=email.strip(), api_key=api_key.strip())
