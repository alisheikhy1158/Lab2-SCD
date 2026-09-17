"""
Orchestration layer: runs the scrape loop by coordinating Browser,
parsing, and (indirectly, via the return value) storage.

CHECKLIST — Single Responsibility / Dependency Direction:
This is the only module that knows the ORDER of operations ("fetch a
search page, pull listing URLs, fetch each one, parse it, repeat until
target or Cloudflare beats us"). It does NOT know HOW to fetch a page
(Browser's job), HOW to parse one (parsing's job), or HOW to save
results (storage's job — called from main.py, not here). That's the
difference between this and the original scrape(), which mixed driver
lifecycle, pagination, retry-adjacent logic, and CSV writing into one
70-line function.

Browser is passed in (constructor injection) rather than created inside
run(). That's what makes this class testable: hand it a fake Browser
whose get_soup() returns canned soup, and you can test the pagination /
target-count logic with no real network or Chrome involved.
"""

import logging
from typing import List

from .browser import Browser
from .config import ScraperConfig
from .models import Property
from .parsing import get_listing_urls, parse_listing

log = logging.getLogger(__name__)


class ZameenScraper:
    def __init__(self, config: ScraperConfig, browser: Browser):
        self.config = config
        self.browser = browser

    def run(self) -> List[Property]:
        collected: List[Property] = []
        page_number = 1

        try:
            while len(collected) < self.config.target_listings:
                search_url = self._search_url(page_number)
                log.info("Page %d | Collected: %d | URL: %s", page_number, len(collected), search_url)

                soup = self.browser.get_soup(search_url)
                if soup is None:
                    log.error("Failed to load search page. Stopping.")
                    break

                listing_urls = get_listing_urls(soup, self.config.base_url)
                log.info("  Found %d listings on this page", len(listing_urls))

                # Stop early once the site stops returning real results.
                # Without this check, the scraper can keep paging forever.
                if not listing_urls:
                    log.warning("No listings found on page %d. Stopping.", page_number)
                    break

                collected.extend(self._collect_from_page(listing_urls, collected))
                page_number += 1

        except KeyboardInterrupt:
            log.warning("Scraper interrupted by user. Keeping %d records collected so far.", len(collected))

        return collected

    def _collect_from_page(self, listing_urls: List[str], already_collected: List[Property]) -> List[Property]:
        """Fetch and parse each listing URL on one search-results page,
        stopping early once the overall target is reached."""
        new_records: List[Property] = []
        for listing_url in listing_urls:
            if len(already_collected) + len(new_records) >= self.config.target_listings:
                break

            detail_soup = self.browser.get_soup(listing_url)
            if detail_soup is None:
                continue

            prop = parse_listing(detail_soup, listing_url)
            if prop is None:
                continue

            new_records.append(prop)
            price_str = f"{prop.price:,.0f}" if prop.price is not None else "N/A"
            log.info(
                " [%d] PKR %s  %s",
                len(already_collected) + len(new_records),
                price_str,
                prop.location,
            )

        return new_records

    def _search_url(self, page_num: int) -> str:
        return self.config.base_url + self.config.search_path_template.format(page=page_num)
