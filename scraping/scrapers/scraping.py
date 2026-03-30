from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import json, time, random, re, urllib.parse
from datetime import datetime

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
    "appartements":              "Immobilier",
    "maisons":                   "Immobilier",
    "voitures_d_occasion":       "Voitures",
    "smartphone_et_téléphone":   "Téléphones",
    "motos":                     "Motos",
    "electronique":              "Électronique",
    "informatique":              "Informatique",
    "meubles_et_décoration":     "Maison",
}

MAX_PAGES_PER_URL   = 3          # increase to 5 or 10 for even more data
SLEEP_BETWEEN_PAGES = (2, 4)     # random sleep range in seconds (be polite)
OUTPUT_FILE         = "avito_data.json"

TODAY = datetime.today().strftime("%Y-%m-%d")

# ─── Helpers ───────────────────────────────────────────────────────────────────

def clean_price(text: str) -> str:
    """Normalize price text: remove currency junk, keep digits + spaces + DH."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", text.replace("\u202f", " ").replace("\xa0", " ").strip())


def parse_offer(badge_text: str) -> dict:
    """
    Given an Avito discount badge text such as '-38%' or '-50 DH',
    return:
      {
        "type_offre":  "pourcentage" | "forfaite",
        "valeur_offre": "38%"          | "50 DH"
      }
    Returns None if no offer badge found.
    """
    if not badge_text:
        return None
    badge_text = badge_text.strip()
    # Percentage  e.g. "-38%" or "38%"
    pct = re.search(r"(\d+)\s*%", badge_text)
    if pct:
        return {"type_offre": "pourcentage", "valeur_offre": f"{pct.group(1)}%"}
    # Flat deduction  e.g. "-50 DH" or "-200DH"
    flat = re.search(r"(\d[\d\s]*)\s*(DH|MAD|Dhs?)", badge_text, re.IGNORECASE)
    if flat:
        return {"type_offre": "forfaite", "valeur_offre": f"{flat.group(1).strip()} DH"}
    # Badge present but pattern unrecognized → keep raw value
    return {"type_offre": "forfaite", "valeur_offre": badge_text}


# ─── Parser ────────────────────────────────────────────────────────────────────

def parse_page(html: str, category_label: str) -> list:
    """Extract listing cards from raw HTML using BeautifulSoup."""
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select("a.sc-1jge648-0")
    listings = []

    for card in cards:
        try:
            title_el    = card.select_one("p.sc-1x0vz2r-0.iHApav")
            price_el    = card.select_one("span.sc-3286ebc5-2")
            price_old_el= card.select_one("span.sc-3286ebc5-3")   # old / barré price
            location_el = card.select_one("p.sc-1x0vz2r-0.layWaX")
            seller_el   = card.select_one("p.sc-1x0vz2r-0.hNCqYw")
            badge_el    = card.select_one(".sc-3286ebc5-5") or card.select_one("[class*='discount']")
            rating_el   = card.select_one(".sc-iHGNWf") or card.select_one("[class*='rating']")

            title         = title_el.get_text(strip=True)    if title_el    else ""
            price_offer   = clean_price(price_el.get_text())  if price_el    else ""
            if price_offer and not price_offer.endswith("DH"):
                price_offer = price_offer + " DH"
            price_initial = clean_price(price_old_el.get_text()) if price_old_el else ""
            if price_initial and not price_initial.endswith("DH"):
                price_initial = price_initial + " DH"
            location      = location_el.get_text(strip=True) if location_el else ""
            seller        = seller_el.get_text(strip=True)   if seller_el   else ""
            badge_text    = badge_el.get_text(strip=True)    if badge_el    else ""
            offer         = parse_offer(badge_text)

            # Rating: Avito sometimes shows stars via inline style
            stars = ""
            if rating_el:
                style = rating_el.get("style", "")
                stars_match = re.search(r"width:\s*(\d+(?:\.\d+)?)", style)
                stars = stars_match.group(1) + "%" if stars_match else rating_el.get_text(strip=True)

            link = card.get("href", "")
            if link and not link.startswith("http"):
                link = f"https://www.avito.ma{link}"

            if not title:
                continue   # skip empty / ad cards

            listings.append({
                "title":         title,
                "price_initial": price_initial,   # original / barré price (empty if none)
                "price_offre":   price_offer,     # current / offer price
                "seller":        seller,
                "location":      location,
                "category":      category_label,
                "link":          link,
                "date":          TODAY,
                "rating":        stars,
                "offre":         offer,           # None if no discount badge
            })
        except Exception as e:
            print(f"  ⚠ Card parse error: {e}")

    return listings


# ─── Scraper core ──────────────────────────────────────────────────────────────

def scrape_page(page_obj, url: str, label: str) -> list:
    """Navigate to url, scroll to load lazy content, and return parsed cards."""
    try:
        page_obj.goto(url, wait_until="domcontentloaded", timeout=60000)
        time.sleep(random.uniform(*SLEEP_BETWEEN_PAGES))
        page_obj.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(1)
        return parse_page(page_obj.content(), label)
    except Exception as e:
        print(f"     ❌ {e}")
        return []


def scrape_url_paginated(page_obj, base_url: str, category_label: str,
                          max_pages: int = MAX_PAGES_PER_URL) -> list:
    """Scrape multiple pages of a single category/city URL."""
    all_listings = []

    for page_num in range(1, max_pages + 1):
        url = base_url if page_num == 1 else f"{base_url}?o={page_num}"
        print(f"    📄 Page {page_num}: {url}")

        cards = scrape_page(page_obj, url, category_label)
        print(f"         → {len(cards)} listings", end="")

        if not cards:
            print("  (vide – arrêt)")
            break

        all_listings.extend(cards)
        print()

    return all_listings


def _save(data: list):
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ─── Main ──────────────────────────────────────────────────────────────────────

def scrape_all():
    """Main scrape loop: iterates over all cities × categories."""
    all_results = []
    seen_links  = set()   # for deduplication

    def absorb(cards):
        new = 0
        for item in cards:
            if item["link"] and item["link"] not in seen_links:
                seen_links.add(item["link"])
                all_results.append(item)
                new += 1
        return new

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.set_extra_http_headers({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
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
                new_count = absorb(listings)

                print(f"  ✅ +{new_count} nouveaux  | total: {len(all_results)}")

                # Save progress after every URL so no data is lost on crash
                _save(all_results)

        browser.close()

    return all_results


# ─── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("🚀 Avito Maroc Scraper – multi-villes / multi-catégories")
    print(f"   Villes     : {len(CITIES)}")
    print(f"   Catégories : {len(CATEGORIES)}")
    print(f"   Max pages  / URL : {MAX_PAGES_PER_URL}")
    print(f"   Cibles max       : ~{len(CITIES)*len(CATEGORIES)*MAX_PAGES_PER_URL*30}+")
    print(f"   Fichier          : {OUTPUT_FILE}")
    print()

    results = scrape_all()

    with_offer  = [r for r in results if r.get("offre")]
    pct_offers  = [r for r in with_offer if r["offre"]["type_offre"] == "pourcentage"]
    flat_offers = [r for r in with_offer if r["offre"]["type_offre"] == "forfaite"]

    print(f"\n🎉 Terminé ! {len(results)} annonces uniques → {OUTPUT_FILE}")
    print(f"\n📊 Statistiques :")
    print(f"   Annonces avec offre %    : {len(pct_offers)}")
    print(f"   Annonces avec forfait    : {len(flat_offers)}")
    print(f"   Annonces sans offre      : {len(results) - len(with_offer)}")

    print("\n📦 Exemples avec offre pourcentage :")
    print(json.dumps(pct_offers[:2], ensure_ascii=False, indent=2))