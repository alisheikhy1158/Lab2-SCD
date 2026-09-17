"""
Entry point. Wires config -> browser -> scraper -> storage together.

CHECKLIST — this file should be boring on purpose:
No parsing logic, no retry logic, no CSV logic lives here — just
construction and one straight-line sequence of calls. Anyone new to the
project can read this file top to bottom and understand the whole
pipeline in ten seconds, then go look at the one module they actually
need to change.
"""

import logging

from .browser import Browser
from .config import ScraperConfig
from .scraper import ZameenScraper
from .storage import write_csv

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


def main() -> None:
    config = ScraperConfig()

    with Browser(config) as browser:
        scraper = ZameenScraper(config, browser)
        records = scraper.run()

    write_csv(records, config.output_csv)
    log.info("Done. Total collected: %d", len(records))


if __name__ == "__main__":
    main()
