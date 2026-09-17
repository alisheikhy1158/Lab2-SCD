"""
Zameen.com Scraper
Task 1 - Data Collection

"""

import time
import random
import csv
import re
import logging
from dataclasses import dataclass, fields, asdict
from typing import Optional

from bs4 import BeautifulSoup
import undetected_chromedriver as uc
from selenium.common.exceptions import TimeoutException, WebDriverException

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

#  Configuration 
BASE_URL   = "https://www.zameen.com"
TARGET     = 400          
DELAY_LOW  = 1.0          
DELAY_HIGH = 2.5
OUTPUT_CSV = "islamabad_properties.csv"

#  Data model 
@dataclass
class Property:
    price: Optional[float]          = None   
    area_marla: Optional[float]     = None
    city: str                       = "Islamabad"
    bedrooms: Optional[int]         = None
    bathrooms: Optional[int]        = None
    location: Optional[str]         = None
    property_type: Optional[str]    = None
    built_year: Optional[int]       = None
    parking_spaces: Optional[int]   = None
    servant_quarters: Optional[int] = None
    store_rooms: Optional[int]      = None
    kitchens: Optional[int]         = None
    drawing_rooms: Optional[int]    = None
    listing_url: Optional[str]      = None

#  Helpers 
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

#  Selenium Setup & Fetching 
def setup_driver() -> uc.Chrome:
    log.info("Initializing Selenium WebDriver...")
    options = uc.ChromeOptions()
    
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--disable-notifications")
    options.page_load_strategy = 'eager'
    
    prefs = {
        "profile.managed_default_content_settings.images": 2,
        "profile.default_content_setting_values.notifications": 2,
        "profile.managed_default_content_settings.stylesheets": 2
    }
    options.add_experimental_option("prefs", prefs)
    
    driver = uc.Chrome(options=options, version_main=148)
    driver.set_page_load_timeout(30) 
    return driver

def safe_get(driver: uc.Chrome, url: str, retries: int = 3) -> Optional[BeautifulSoup]:
    for attempt in range(retries):
        try:
            driver.get(url)
            time.sleep(random.uniform(DELAY_LOW, DELAY_HIGH))
            
            if "Just a moment" in driver.title or "Cloudflare" in driver.page_source:
                log.warning(f"Cloudflare challenge detected on attempt {attempt+1}. Waiting 10s...")
                time.sleep(10)

            driver.execute_script("window.scrollTo(0, 500);")
            time.sleep(0.5)  
            page_source = driver.page_source
            
            if "zameen" not in driver.current_url.lower():
                log.warning("Redirected away from Zameen. Retrying...")
                continue
                
            return BeautifulSoup(page_source, "html.parser")
            
        except TimeoutException:
            log.warning(f"Page load timeout ({attempt+1}/{retries}) for {url}")
        except WebDriverException as e:
            log.warning(f"WebDriver error ({attempt+1}/{retries}): {e}")
            
        time.sleep(random.uniform(DELAY_LOW, DELAY_HIGH) * (attempt + 1))
        
    log.error(f"Failed to fetch {url} after {retries} attempts.")
    return None

#  Parsers 
def parse_listing(soup: BeautifulSoup, url: str) -> Optional[Property]:
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

        for li in soup.find_all("li"):
            text = li.get_text(" ", strip=True).lower()
            
            if len(text) > 50:
                continue

            if "area" in text and prop.area_marla is None:
                prop.area_marla = parse_area(text)
                
            elif "bed" in text and prop.bedrooms is None:
                m = re.search(r"(\d+)", text)
                if m: prop.bedrooms = int(m.group(1))
                
            elif "bath" in text and prop.bathrooms is None:
                m = re.search(r"(\d+)", text)
                if m: prop.bathrooms = int(m.group(1))
                
            elif "built" in text or "year" in text:
                m = re.search(r"(19\d{2}|20\d{2})", text)
                if m: prop.built_year = int(m.group(1))
                
            elif "park" in text:
                m = re.search(r"(\d+)", text)
                prop.parking_spaces = int(m.group(1)) if m else 1
                
            elif "servant" in text:
                m = re.search(r"(\d+)", text)
                prop.servant_quarters = int(m.group(1)) if m else 1
                
            elif "store" in text:
                m = re.search(r"(\d+)", text)
                prop.store_rooms = int(m.group(1)) if m else 1
                
            elif "kitchen" in text:
                m = re.search(r"(\d+)", text)
                prop.kitchens = int(m.group(1)) if m else 1
                
            elif "drawing" in text:
                prop.drawing_rooms = 1

        return prop if prop.price else None

    except Exception as e:
        log.error(f"Error parsing listing {url}: {e}")
        return None

def get_listing_urls(soup: BeautifulSoup) -> list[str]:
    urls = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if re.search(r"^(https://www\.zameen\.com)?/Property/[^?]+\.html$", href, re.I):
            full = href if href.startswith("http") else BASE_URL + href
            if full not in urls:
                urls.append(full)
                
    return urls

def get_next_page_url(soup: BeautifulSoup, current_url: str) -> Optional[str]:
    next_btn = soup.find("a", {"aria-label": re.compile(r"next", re.I)}) or \
               soup.find("li", class_=re.compile(r"next", re.I))
    if next_btn and next_btn.find("a"):
        href = next_btn.find("a")["href"]
        return href if href.startswith("http") else BASE_URL + href
    return None

#  CSV Writer 
def write_csv(records: list[Property], path: str):
    if not records:
        log.warning("No records to write.")
        return
    col_names = [f.name for f in fields(Property)]
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=col_names)
        writer.writeheader()
        for rec in records:
            writer.writerow(asdict(rec))
    log.info(f"Saved {len(records)} records → {path}")

#  Main Loop 
def scrape(target: int = TARGET, output: str = OUTPUT_CSV):
    driver = setup_driver()
    collected: list[Property] = []
    search_url = f"{BASE_URL}/Houses_Property/Islamabad-3-1.html"
    page_num = 1
    
    try:
        while len(collected) < target and search_url:
            log.info(f"Page {page_num} | Collected: {len(collected)} | URL: {search_url}")
            
            soup = safe_get(driver, search_url)
            if soup is None:
                log.error("Failed to load search page. Stopping.")
                break

            listing_urls = get_listing_urls(soup)
            log.info(f"  Found {len(listing_urls)} listings on this page")

            for lurl in listing_urls:
                if len(collected) >= target:
                    break
                
                detail_soup = safe_get(driver, lurl)
                if detail_soup:
                    prop = parse_listing(detail_soup, lurl)
                    if prop:
                        collected.append(prop)
                        log.info(f" [{len(collected)}] PKR {prop.price:,.0f}  {prop.location}")

            page_num += 1
            search_url = f"{BASE_URL}/Houses_Property/Islamabad-3-{page_num}.html"
            
    except KeyboardInterrupt:
        log.warning("Scraper interrupted. Saving progress...")
    finally:
        log.info("Closing browser...")
        driver.quit()
        
    write_csv(collected, output)
    log.info(f"Done. Total collected: {len(collected)}")
    return collected

#  Entry Point 
if __name__ == "__main__":
    scrape()