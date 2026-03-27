from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import json, time, random

# ─── Configuration ─────────────────────────────────────────────────────────────

CITIES = [
    "casablanca",
    "rabat",
    "marrakech",
    "tanger",
    "fès",
    "agadir",
    "meknes",
    "oujda",
]

CATEGORIES = {
    "appartements":       "Immobilier",
    "maisons":            "Immobilier",
    "voitures_d_occasion":"Voitures",
    "smartphone_et_téléphone": "Téléphones",
    "motos":              "Motos",
    "electronique":       "Électronique",
    "informatique":       "Informatique",
    "meubles_et_décoration": "Maison",
}

MAX_PAGES_PER_URL = 3         # increase to 5 or 10 for even more data
SLEEP_BETWEEN_PAGES = (2, 4)  # random sleep range in seconds (be polite)

# ─── Scraper ───────────────────────────────────────────────────────────────────

def parse_page(html, category_label):
    """Extract listing cards from raw HTML using BeautifulSoup."""
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select("a.sc-1jge648-0")
    listings = []

    for card in cards:
        try:
            title_el   = card.select_one("p.sc-1x0vz2r-0.iHApav")
            price_el   = card.select_one("span.sc-3286ebc5-2")
            location_el= card.select_one("p.sc-1x0vz2r-0.layWaX")
            seller_el  = card.select_one("p.sc-1x0vz2r-0.hNCqYw")

            title    = title_el.get_text(strip=True)    if title_el    else None
            price    = price_el.get_text(strip=True) + " DH" if price_el else "Prix non indiqué"
            location = location_el.get_text(strip=True) if location_el else None
            seller   = seller_el.get_text(strip=True)   if seller_el   else None

            link = card.get("href", "")
            if link and not link.startswith("http"):
                link = f"https://www.avito.ma{link}"

            if title:
                listings.append({
                    "title":    title,
                    "price":    price,
                    "seller":   seller,
                    "location": location,
                    "category": category_label,
                    "link":     link,
                })
        except Exception as e:
            print(f"  ⚠ Card parse error: {e}")

    return listings


def scrape_url_paginated(page_obj, base_url, category_label, max_pages=MAX_PAGES_PER_URL):
    """Scrape multiple pages of a single category/city URL."""
    all_listings = []

    for page_num in range(1, max_pages + 1):
        url = base_url if page_num == 1 else f"{base_url}?o={page_num}"
        print(f"    📄 Page {page_num}: {url}")

        try:
            page_obj.goto(url, wait_until="domcontentloaded", timeout=60000)
            # Random sleep to avoid rate-limiting
            time.sleep(random.uniform(*SLEEP_BETWEEN_PAGES))
            html = page_obj.content()
        except Exception as e:
            print(f"    ❌ Failed to load page {page_num}: {e}")
            break

        listings = parse_page(html, category_label)
        print(f"       → Found {len(listings)} listings")

        if not listings:
            print("       → No listings found, stopping pagination.")
            break

        all_listings.extend(listings)

    return all_listings


def scrape_all():
    """Main scrape loop: iterates over all cities × categories."""
    all_results = []
    seen_links  = set()   # for deduplication

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.set_extra_http_headers({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        })

        total_urls = len(CITIES) * len(CATEGORIES)
        current    = 0

        for city in CITIES:
            for slug, label in CATEGORIES.items():
                current += 1
                base_url = f"https://www.avito.ma/fr/{city}/{slug}"
                print(f"\n[{current}/{total_urls}] 🌍 {city.capitalize()} › {label}")
                print(f"  URL: {base_url}")

                listings = scrape_url_paginated(page, base_url, label)

                # Deduplicate by link
                new_count = 0
                for item in listings:
                    if item["link"] not in seen_links:
                        seen_links.add(item["link"])
                        all_results.append(item)
                        new_count += 1

                print(f"  ✅ +{new_count} new (total: {len(all_results)})")

                # Save progress after every URL so no data is lost on crash
                with open("avito_data.json", "w", encoding="utf-8") as f:
                    json.dump(all_results, f, ensure_ascii=False, indent=2)

        browser.close()

    return all_results


# ─── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("🚀 Starting Avito multi-city / multi-category scraper")
    print(f"   Cities    : {len(CITIES)}")
    print(f"   Categories: {len(CATEGORIES)}")
    print(f"   Max pages / URL: {MAX_PAGES_PER_URL}")
    print(f"   Max possible listings: ~{len(CITIES)*len(CATEGORIES)*MAX_PAGES_PER_URL*30}+")
    print()

    results = scrape_all()

    print(f"\n🎉 Done! Scraped {len(results)} unique listings → avito_data.json")
    print(json.dumps(results[:2], ensure_ascii=False, indent=2))