"""
Data model: the shape of one scraped listing.

CHECKLIST — Cohesion / Shared Contract:
This is the one thing every other module agrees on. parsing.py produces
Property objects, storage.py consumes them, scraper.py passes them along.
None of those modules need to import each other directly — they only need
to agree on this shape. That's what "clear interface" means in practice.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Property:
    price: Optional[float] = None
    area_marla: Optional[float] = None
    city: str = "Islamabad"
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    location: Optional[str] = None
    property_type: Optional[str] = None
    built_year: Optional[int] = None
    parking_spaces: Optional[int] = None
    servant_quarters: Optional[int] = None
    store_rooms: Optional[int] = None
    kitchens: Optional[int] = None
    drawing_rooms: Optional[int] = None
    listing_url: Optional[str] = None
