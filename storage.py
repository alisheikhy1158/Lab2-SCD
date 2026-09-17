"""
Storage layer: turns collected Property records into a file on disk.

CHECKLIST — Change Impact:
If you later want JSON, SQLite, or a Google Sheet instead of (or in
addition to) CSV, this is the only file that changes. scraper.py just
gets a list[Property] back from run() — it doesn't know or care how
that list eventually gets saved.
"""

import csv
import logging
from dataclasses import asdict, fields
from typing import Sequence

from .models import Property

log = logging.getLogger(__name__)


def write_csv(records: Sequence[Property], path: str) -> None:
    if not records:
        log.warning("No records to write.")
        return

    # Keep the CSV header aligned with the dataclass shape so the export is
    # easy to understand and stays consistent with the model contract.
    column_names = [f.name for f in fields(Property)]
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=column_names)
        writer.writeheader()
        writer.writerows(asdict(rec) for rec in records)

    log.info("Saved %d records → %s", len(records), path)
