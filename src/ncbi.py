# Sticky MetaFASTA
# Copyright (C) 2026 Sticky Ends Bio Private Limited
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import logging
import queue
import socket
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, TypeVar

from Bio import Entrez
from Bio.GenBank import parse as parse_genbank
from Bio.SeqRecord import SeqRecord

from .config import Settings
from .utils import retry

T = TypeVar("T")


@dataclass(frozen=True)
class SearchHistory:
    count: int
    webenv: str
    query_key: str


class NCBIClient:
    def __init__(
        self,
        settings: Settings,
        logger: logging.Logger,
        status_callback: Callable[[str], None] | None = None,
    ) -> None:
        self.settings = settings
        self.logger = logger
        self.status_callback = status_callback

        Entrez.email = settings.email
        Entrez.tool = "StickyMetaFASTA"
        Entrez.api_key = settings.api_key or None
        socket.setdefaulttimeout(settings.network_timeout_seconds)

        self.request_delay = (
            settings.delay_with_api_key_seconds
            if settings.api_key
            else settings.delay_without_api_key_seconds
        )

    def _run_with_heartbeat(
        self,
        operation: Callable[[], T],
        *,
        description: str,
    ) -> T:
        result_queue: queue.Queue[tuple[str, object]] = queue.Queue(maxsize=1)

        def worker() -> None:
            try:
                result_queue.put(("ok", operation()))
            except BaseException as exc:
                result_queue.put(("error", exc))

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        waited = 0

        while True:
            try:
                status, payload = result_queue.get(
                    timeout=self.settings.heartbeat_seconds
                )
            except queue.Empty:
                waited += self.settings.heartbeat_seconds
                status_message = (
                    f"Still working: {description}. "
                    f"Elapsed waiting time: {waited} seconds."
                )
                if self.status_callback is not None:
                    self.status_callback(status_message)
                print(
                    f"\nStatus: still working - {description}\n"
                    f"Elapsed waiting time: {waited} seconds",
                    flush=True,
                )
                continue

            if status == "error":
                if isinstance(payload, BaseException):
                    raise payload
                raise RuntimeError(str(payload))
            return payload  # type: ignore[return-value]

    def _request(
        self,
        operation: Callable[[], T],
        *,
        description: str,
    ) -> T:
        def attempt() -> T:
            try:
                return self._run_with_heartbeat(
                    operation,
                    description=description,
                )
            finally:
                time.sleep(self.request_delay)

        return retry(
            attempt,
            attempts=self.settings.retry_count,
            base_wait_seconds=self.settings.retry_base_wait_seconds,
            description=description,
            logger=self.logger,
            status_callback=self.status_callback,
        )

    def search_history(self, query: str) -> SearchHistory:
        def operation() -> SearchHistory:
            with Entrez.esearch(
                db=self.settings.database,
                term=query,
                retmax=0,
                usehistory="y",
            ) as handle:
                result: dict[str, Any] = Entrez.read(handle)

            count = int(result.get("Count", 0))
            if count == 0:
                return SearchHistory(count=0, webenv="", query_key="")

            webenv = str(result.get("WebEnv", "")).strip()
            query_key = str(result.get("QueryKey", "")).strip()
            if not webenv or not query_key:
                raise RuntimeError(
                    "NCBI did not return the History Server identifiers."
                )
            return SearchHistory(
                count=count,
                webenv=webenv,
                query_key=query_key,
            )

        return self._request(
            operation,
            description="Searching NCBI and creating the result history",
        )

    def fetch_genbank_batch(
        self,
        history: SearchHistory,
        *,
        retstart: int,
        retmax: int,
    ) -> list[SeqRecord]:
        def operation() -> list[SeqRecord]:
            with Entrez.efetch(
                db=self.settings.database,
                query_key=history.query_key,
                WebEnv=history.webenv,
                retstart=retstart,
                retmax=retmax,
                rettype="gb",
                retmode="text",
            ) as handle:
                return list(parse_genbank(handle))

        end = min(history.count, retstart + retmax)
        return self._request(
            operation,
            description=(
                f"Downloading GenBank records {retstart + 1}-{end}"
            ),
        )

