"""
Configuration for the Zameen.com scraper.

CHECKLIST — Change Impact / Low Coupling:
Your original code used bare module-level constants (BASE_URL, TARGET,
DELAY_LOW, DELAY_HIGH...) that every function silently reached into.
That's a hidden dependency: you can't tell from a function's signature
that it depends on DELAY_LOW, and you can't run two scrapers with
different settings in the same process (e.g. one for Islamabad, one for
Lahore) without them fighting over the same globals.

A single frozen dataclass passed explicitly to whatever needs it fixes
both problems: dependencies are visible in the signature, and the object
is immutable so nothing can mutate config mid-run by accident.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ScraperConfig:
    base_url: str = "https://www.zameen.com"
    search_path_template: str = "/Houses_Property/Islamabad-3-{page}.html"
    target_listings: int = 400
    delay_low: float = 1.0
    delay_high: float = 2.5
    page_load_timeout: int = 30
    retries: int = 3
    output_csv: str = "islamabad_properties.csv"

    # BUG FIX: original hardcoded version_main=148. That breaks the
    # instant your local Chrome auto-updates past 148. None lets
    # undetected-chromedriver detect the installed version itself.
    chrome_version_main: Optional[int] = None
