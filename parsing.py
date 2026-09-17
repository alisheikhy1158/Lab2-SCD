"""
Pure parsing functions: turn text/HTML into typed data.

CHECKLIST — Testability / Single Responsibility:
Every function here takes what it needs as an argument and returns a
value. None of them touch a network, a browser, a file, or a global.
That's exactly what makes them unit-testable with zero setup:

    assert parse_price("2.5 crore") == 25_000_000
    assert parse_area("10 marla") == 10

No driver, no HTML fixture, no mocking required. Contrast this with the
original safe_get(), which mixed retry logic, sleep timing, and parsing
concerns in one function — you couldn't test "does this handle a
Cloudflare page" without actually driving a browser.
"""

import logging
import re
from typing import List, Optional

from bs4 import BeautifulSoup

from .models import Property

log = logging.getLogger(__name__)


def parse_price(text: str) -> Optional[float]:
    if not text:
        return None
    text = text.replace(",", "").strip()
    m = re.search(r"([\d.]+)\s*(crore|lakh|thousand)?", text, re.I)
    if not m:
        return None
    num = float(m.group(1))
    unit = (m.group(2) or "").lower()

    if unit == "crore":
        return num * 1e7
    if unit == "lakh":
        return num * 1e5
    if unit == "thousand":
        return num * 1e3
    return num


def parse_area(text: str) -> Optional[float]:
    if not text:
        return None
    text = text.strip()
    m = re.search(r"([\d.]+)\s*(marla|kanal|sq\.?\s*ft|square\s*feet)?", text, re.I)
    if not m:
        return None
    num = float(m.group(1))
    unit = (m.group(2) or "marla").lower()

    if "kanal" in unit:
        return num * 20
    if "sq" in unit or "feet" in unit or "ft" in unit:
        return round(num / 272.25, 2)
    return num


def parse_listing(soup: BeautifulSoup, url: str) -> Optional[Property]:
    """Parse a single listing detail page into a Property.

    Returns None if no price was found — we treat price as mandatory
    for a "usable" record, same as the original.
    """
    try:
        prop = Property(listing_url=url)

        price_tag = soup.find(attrs={"aria-label": "Price"}) or soup.find(string=re.compile(r"PKR", re.I))
        if price_tag:
            price_text = price_tag if isinstance(price_tag, str) else price_tag.get_text()
            prop.price = parse_price(price_text)

        loc_tag = soup.find(attrs={"aria-label": "Location"})
        if loc_tag:
            prop.location = loc_tag.get_text(strip=True)

        type_tag = soup.find(attrs={"aria-label": "Type"})
        if type_tag:
            prop.property_type = type_tag.get_text(strip=True)

        _fill_feature_list(soup, prop)

        return prop if prop.price else None

    except Exception as e:
        log.error("Error parsing listing %s: %s", url, e)
        return None


def _extract_first_number(text: str) -> Optional[int]:
    match = re.search(r"(\d+)", text)
    return int(match.group(1)) if match else None


def _extract_year(text: str) -> Optional[int]:
    match = re.search(r"(19\d{2}|20\d{2})", text)
    return int(match.group(1)) if match else None


def _fill_feature_list(soup: BeautifulSoup, prop: Property) -> None:
    """Populate compact numeric features such as bedrooms, baths, and parking.

    This helper keeps parse_listing() focused on the overall page structure,
    while the feature extraction rules stay in one dedicated place.
    """
    feature_rules = [
        ("area", "area_marla", parse_area),
        ("bed", "bedrooms", _extract_first_number),
        ("bath", "bathrooms", _extract_first_number),
        ("built", "built_year", _extract_year),
        ("year", "built_year", _extract_year),
        ("park", "parking_spaces", lambda text: _extract_first_number(text) or 1),
        ("servant", "servant_quarters", lambda text: _extract_first_number(text) or 1),
        ("store", "store_rooms", lambda text: _extract_first_number(text) or 1),
        ("kitchen", "kitchens", lambda text: _extract_first_number(text) or 1),
        ("drawing", "drawing_rooms", lambda text: 1),
    ]

    for li in soup.find_all("li"):
        text = li.get_text(" ", strip=True).lower()
        if len(text) > 50:
            continue

        for keyword, attribute_name, extractor in feature_rules:
            if keyword not in text:
                continue
            if getattr(prop, attribute_name) is not None:
                break

            value = extractor(text)
            if value is not None:
                setattr(prop, attribute_name, value)
            break


def get_listing_urls(soup: BeautifulSoup, base_url: str) -> List[str]:
    """Extract listing detail-page URLs from a search results page.

    Takes base_url as a parameter instead of reading a module-level
    BASE_URL constant — same reasoning as config.py: explicit input,
    testable output, no hidden global.
    """
    urls: List[str] = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if re.search(r"^(https://www\.zameen\.com)?/Property/[^?]+\.html$", href, re.I):
            full = href if href.startswith("http") else base_url + href
            if full not in urls:
                urls.append(full)
    return urls
