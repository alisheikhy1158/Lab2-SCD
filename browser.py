"""
Browser layer: everything related to driving a real Chrome instance.

CHECKLIST — Low Coupling / Reusability:
This is the ONLY file in the package that imports selenium or
undetected_chromedriver. parsing.py and scraper.py never touch them
directly. That means:

  1. If you ever swap Selenium for Playwright, you rewrite this one file
     and nothing else changes.
  2. You can write a "FakeBrowser" with the same get_soup() signature for
     tests, and scraper.py won't know the difference.

Using a class instead of a free-floating `driver` object plus a
`safe_get(driver, url)` function also gives us __enter__/__exit__, so
`driver.quit()` can't be forgotten by a caller — it happens automatically
when the `with` block exits, even on an exception.
"""

import logging
import random
import time
from typing import Optional

import undetected_chromedriver as uc
from bs4 import BeautifulSoup
from selenium.common.exceptions import TimeoutException, WebDriverException

from .config import ScraperConfig

log = logging.getLogger(__name__)


class Browser:
    def __init__(self, config: ScraperConfig):
        self.config = config
        self.driver: Optional[uc.Chrome] = None

    def __enter__(self) -> "Browser":
        self.driver = self._build_driver()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def _build_driver(self) -> uc.Chrome:
        log.info("Initializing Selenium WebDriver...")
        options = uc.ChromeOptions()
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--disable-notifications")
        options.page_load_strategy = "eager"

        prefs = {
            "profile.managed_default_content_settings.images": 2,
            "profile.default_content_setting_values.notifications": 2,
            "profile.managed_default_content_settings.stylesheets": 2,
        }
        options.add_experimental_option("prefs", prefs)

        driver = uc.Chrome(options=options, version_main=self.config.chrome_version_main)
        driver.set_page_load_timeout(self.config.page_load_timeout)
        return driver

    def close(self) -> None:
        if self.driver is not None:
            log.info("Closing browser...")
            self.driver.quit()
            self.driver = None

    def get_soup(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch a URL with retry/backoff and return parsed HTML, or None
        if every attempt failed."""
        cfg = self.config
        for attempt in range(cfg.retries):
            try:
                self.driver.get(url)
                time.sleep(random.uniform(cfg.delay_low, cfg.delay_high))

                if "Just a moment" in self.driver.title or "Cloudflare" in self.driver.page_source:
                    log.warning("Cloudflare challenge detected on attempt %d. Waiting 10s...", attempt + 1)
                    time.sleep(10)

                self.driver.execute_script("window.scrollTo(0, 500);")
                time.sleep(0.5)

                if "zameen" not in self.driver.current_url.lower():
                    log.warning("Redirected away from Zameen. Retrying...")
                    continue

                return BeautifulSoup(self.driver.page_source, "html.parser")

            except TimeoutException:
                log.warning("Page load timeout (%d/%d) for %s", attempt + 1, cfg.retries, url)
            except WebDriverException as e:
                log.warning("WebDriver error (%d/%d): %s", attempt + 1, cfg.retries, e)

            time.sleep(random.uniform(cfg.delay_low, cfg.delay_high) * (attempt + 1))

        log.error("Failed to fetch %s after %d attempts.", url, cfg.retries)
        return None
