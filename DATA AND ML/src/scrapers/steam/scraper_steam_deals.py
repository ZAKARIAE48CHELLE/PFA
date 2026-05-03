"""
steam_multi_scraper.py
----------------------
Scrapes multiple Steam categories and outputs products in the project JSON schema.

Requirements:
    pip install requests beautifulsoup4

Usage:
    python steam_multi_scraper.py
    python steam_multi_scraper.py --count 1000 --output data/raw/steam_products.json --cc fr
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import argparse
import os
from datetime import date

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
BASE_URL = "https://store.steampowered.com/search/"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
}
TODAY = str(date.today())

# Categories to scrape to ensure diversity and quantity
CATEGORIES = {
    "Specials": {"specials": 1},
    "Top Sellers": {"filter": "topsellers"},
    "Popular New": {"filter": "popularnew"},
    "All Games": {"category1": 998}, # Fallback to reach high counts
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def parse_price(raw: str) -> float | None:
    """Convert '12,99€', '$12.99', or '12.99' to float."""
    if not raw:
        return None
    # Remove currency symbols, non-breaking spaces, and common separators
    cleaned = raw.replace("\xa0", "").replace(" ", "")
    # Remove symbols like €, $, £, ¥
    for symbol in ["€", "$", "£", "¥", "zł", "kr"]:
        cleaned = cleaned.replace(symbol, "")
    
    # Handle European decimal comma
    cleaned = cleaned.replace(",", ".")
    
    # Sometimes it says 'Free' or similar
    if any(word in cleaned.lower() for word in ["gratuit", "free", "offert"]):
        return 0.0

    try:
        # Final cleanup for any remaining non-numeric chars except the dot
        cleaned = "".join(c for c in cleaned if c.isdigit() or c == ".")
        return round(float(cleaned), 2)
    except ValueError:
        return None


def fetch_page(page_index: int, category_params: dict, cc: str = "fr") -> BeautifulSoup | None:
    """Fetch one search results page (25 items each) for a given category."""
    params = {
        "cc": cc,
        "start": page_index * 25,
        "count": 25,
    }
    params.update(category_params)
    
    try:
        resp = requests.get(BASE_URL, headers=HEADERS, params=params, timeout=15)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "html.parser")
    except requests.RequestException as e:
        print(f"  [!] Request error on page {page_index}: {e}")
        return None


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------
def parse_items(soup: BeautifulSoup) -> list[dict]:
    results = []
    rows = soup.select("#search_resultsRows a.search_result_row")

    for row in rows:
        # --- title ---
        title_el = row.select_one("span.title")
        titre = title_el.get_text(strip=True) if title_el else ""

        # --- link & app_id ---
        link = row.get("href", "").split("?")[0]
        app_id = row.get("data-ds-appid", "")

        # --- thumb ---
        image_el = row.select_one(".search_capsule img")
        image_url = image_el.get("src") if image_el else ""

        # --- prices ---
        # Steam uses .discount_original_price for the crossed out price
        orig_el = row.select_one(".discount_original_price")
        prix_initial = parse_price(orig_el.get_text(strip=True)) if orig_el else None

        # .discount_final_price for the current price
        final_el = row.select_one(".discount_final_price")
        prix_offre = parse_price(final_el.get_text(strip=True)) if final_el else None

        # Fallback if no discount block (regular price)
        if prix_offre is None:
            price_block = row.select_one(".search_price")
            if price_block:
                prix_offre = parse_price(price_block.get_text(strip=True))

        prix_base = prix_initial if prix_initial is not None else prix_offre

        # --- discount percentage ---
        disc_el = row.select_one(".discount_pct")
        discount_pct = None
        if disc_el:
            raw_disc = disc_el.get_text(strip=True).replace("-", "").replace("%", "")
            try:
                discount_pct = float(raw_disc)
            except ValueError:
                pass

        # --- rating ---
        rating_el = row.select_one(".search_review_summary")
        rating_text = rating_el.get("data-tooltip-html", "") if rating_el else ""
        if rating_text:
            # strip HTML tags from tooltip
            rating_text = BeautifulSoup(rating_text, "html.parser").get_text(separator=" ", strip=True)

        # --- build offre block ---
        offre = []
        if discount_pct:
            offre.append({
                "typeOffre": "pourcentage",
                "valeurOffre": discount_pct,
                "monnaie": "EUR",
                "dateCreation": TODAY,
                "statut": "active",
            })

        record = {
            "titre": titre,
            "prixInitial": prix_initial,
            "prixBase": prix_base,
            "prixOffre": prix_offre,
            "discountPercentage": discount_pct,
            "categorie": "Gaming",
            "location": "Steam",
            "statut": "actif",
            "monnaie": "EUR",
            "offre": offre,
            "seller": "Valve",
            "rating": rating_text,
            "app_id": app_id,
            "image": image_url,
            "link": link,
            "date": TODAY,
        }
        results.append(record)

    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def scrape(target_count: int = 20000, output: str = "data/raw/steam_products.json", cc: str = "fr") -> None:
    all_deals: list[dict] = []
    seen_links: set[str] = set()

    # Ensure output directory exists
    output_dir = os.path.dirname(output)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    print(f"Goal: Collect {target_count} products from Steam (cc={cc})...")

    category_list = list(CATEGORIES.items())
    current_cat_idx = 0

    while len(all_deals) < target_count and current_cat_idx < len(category_list):
        cat_name, cat_params = category_list[current_cat_idx]
        print(f"\n--- Scraping Category: {cat_name} ---")
        
        # Determine how many pages to scrape for this category
        # Roughly target_count / count_categories
        pages_to_scrape = (target_count // len(category_list)) // 25 + 5
        
        for i in range(pages_to_scrape):
            if len(all_deals) >= target_count:
                break

            print(f"  Page {i + 1} | Total: {len(all_deals)}/{target_count}...")
            soup = fetch_page(i, cat_params, cc=cc)
            
            if soup is None:
                continue

            items = parse_items(soup)
            if not items:
                print("    → No more items in this category. Moving to next.")
                break

            new_count = 0
            for item in items:
                if item["link"] not in seen_links:
                    item["source"] = cat_name
                    seen_links.add(item["link"])
                    all_deals.append(item)
                    new_count += 1
                
                if len(all_deals) >= target_count:
                    break

            print(f"    → {len(items)} found, {new_count} unique added.")
            time.sleep(1.0)  # polite delay

        current_cat_idx += 1

    with open(output, "w", encoding="utf-8") as f:
        json.dump(all_deals, f, ensure_ascii=False, indent=2)

    print(f"\nDone. {len(all_deals)} products saved to '{output}'")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Steam multi-category product scraper")
    parser.add_argument("--count", type=int, default=10000, help="Target number of products to collect")
    parser.add_argument("--output", type=str, default="data/raw/steam_products.json", help="Output JSON file name")
    parser.add_argument("--cc", type=str, default="fr", help="Country code for pricing (fr, us, de...)")
    args = parser.parse_args()

    scrape(target_count=args.count, output=args.output, cc=args.cc)