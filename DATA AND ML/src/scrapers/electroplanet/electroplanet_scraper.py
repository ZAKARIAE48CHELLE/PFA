"""
Electroplanet.ma Scraper
━━━━━━━━━━━━━━━━━━━━━━━━
Schema aligned with the project's data model:
  Produit  → titre, prixInitial (float), prixBase (float), prixOffre (float),
              categorie, location, statut, monnaie, offre, seller, rating, link, date

Features:
  - Playwright-based for infinite scroll handling
  - UML-aligned schema
  - Saves to data/raw/electroplanet_full.json
"""

import json
import logging
import random
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

# ─── Paths ────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent  # Go up 4 levels to PFA
OUTPUT_FILE  = PROJECT_ROOT / "data" / "raw" / "electroplanet_full.json"
LOG_FILE     = PROJECT_ROOT / "logs" / "electroplanet_scraper.log"

# Create directories if they don't exist
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

# ─── Config ───────────────────────────────────────────────────────────────────
TARGET_PRODUCTS     = 10000
TODAY               = datetime.today().strftime("%Y-%m-%d")
SCROLL_PAUSE_S      = (1.5, 3.0)
MAX_EMPTY_SCROLLS   = 15
MONNAIE             = "MAD"

# Granular Leaf Categories for full catalog coverage
CATEGORIES = [
    # Gros electroménager
    ("Réfrigérateur 4 portes", "https://www.electroplanet.ma/gros-electromenager/refrigerateur/refrigerateur-4-portes"),
    ("Réfrigérateur Side by side", "https://www.electroplanet.ma/gros-electromenager/refrigerateur/refrigerateur-americain-side-by-side"),
    ("Réfrigérateur combiné", "https://www.electroplanet.ma/gros-electromenager/refrigerateur/refrigerateur-avec-congelateur-en-bas"),
    ("Congélateur Armoire", "https://www.electroplanet.ma/gros-electromenager/congelateur/congelateur-armoire"),
    ("Congélateur Coffre", "https://www.electroplanet.ma/gros-electromenager/congelateur/congelateur-coffre"),
    ("Cuisinière 4 feux", "https://www.electroplanet.ma/gros-electromenager/cuisiniere/cuisiniere-4-feux"),
    ("Cuisinière 5 feux", "https://www.electroplanet.ma/gros-electromenager/cuisiniere/cuisiniere-5-feux"),
    ("Lave-vaisselle Pose Libre", "https://www.electroplanet.ma/gros-electromenager/lave-vaisselle/lave-vaisselle-pose-libre"),
    ("Machine à laver Hublot", "https://www.electroplanet.ma/gros-electromenager/machine-a-laver/machine-a-laver-a-hublot"),
    ("Machine à laver Top", "https://www.electroplanet.ma/gros-electromenager/machine-a-laver/machine-a-laver-ouverture-en-haut"),
    
    # Informatique
    ("Notebook", "https://www.electroplanet.ma/informatique/ordinateur-portable/notebook"),
    ("PC Gamer", "https://www.electroplanet.ma/informatique/ordinateur-portable/pc-gamer"),
    ("Macbook", "https://www.electroplanet.ma/informatique/ordinateur-portable/macbook"),
    ("Ultrabook", "https://www.electroplanet.ma/informatique/ordinateur-portable/ultrabook"),
    ("Desktop", "https://www.electroplanet.ma/informatique/ordinateur-bureau/desktop"),
    ("iMac", "https://www.electroplanet.ma/informatique/ordinateur-bureau/imac"),
    
    # Smartphone
    ("Smartphone Android", "https://www.electroplanet.ma/smartphone-tablette-gps/smartphone/telephone-android"),
    ("iPhone", "https://www.electroplanet.ma/smartphone-tablette-gps/smartphone/iphone"),
    ("Tablette Android", "https://www.electroplanet.ma/smartphone-tablette-gps/tablettes/tablettes-android"),
    ("iPad", "https://www.electroplanet.ma/smartphone-tablette-gps/tablettes/ipad"),
    
    # TV
    ("Smart TV", "https://www.electroplanet.ma/tv-photo-video/televiseur/smart-tv"),
    ("TV 4K UHD", "https://www.electroplanet.ma/tv-photo-video/televiseur/televiseurs-4k-uhd"),
    ("TV Premium 4K", "https://www.electroplanet.ma/tv-photo-video/televiseur/televiseurs-premium-4k-uhd"),
    ("OLED", "https://www.electroplanet.ma/tv-photo-video/televiseur/oled"),
    
    # Gaming
    ("Jeux PS5", "https://www.electroplanet.ma/jeux-consoles/jeux-video/jeux"),
    ("Consoles", "https://www.electroplanet.ma/jeux-consoles/consoles/consoles-play-station"),
    
    # Bulk Sections (High Volume)
    ("Promotions", "https://www.electroplanet.ma/promotions"),
    ("Exclu Web", "https://www.electroplanet.ma/exclu-web"),
    ("Petits Prix", "https://www.electroplanet.ma/petits-prix"),
    
    # Petit electroménager
    ("Blender", "https://www.electroplanet.ma/petit-electromenager/preparation-culinaire/blender"),
    ("Robot de cuisine", "https://www.electroplanet.ma/petit-electromenager/preparation-culinaire/robot-de-cuisine"),
    ("Cafetière classique", "https://www.electroplanet.ma/petit-electromenager/cafetiere-et-expresso/cafetiere-classique"),
    ("Brosse soufflante", "https://www.electroplanet.ma/sante-beaute-bebe/coiffure/brosse-soufflante"),
]

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)

# ─── UA pool ──────────────────────────────────────────────────────────────────
UA_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]

# ─── Price helpers ────────────────────────────────────────────────────────────

def clean_price(text: str) -> str:
    if not text:
        return ""
    # Remove "DH", spaces, etc.
    return re.sub(r"\s+", " ", text.replace("\u202f", " ").replace("\xa0", " ").replace("DH", "").strip())

def price_to_float(text: str) -> float | None:
    if not text:
        return None
    cleaned = re.sub(r"[^\d,\.]", "", clean_price(text)).replace(",", ".")
    try:
        return round(float(cleaned), 2)
    except ValueError:
        return None

def build_offer(price_old: float, price_new: float):
    if price_old and price_new and price_old > price_new:
        p = round((price_old - price_new) / price_old * 100, 2)
        if p >= 0.1:
            return [{
                "typeOffre": "pourcentage",
                "valeurOffre": p,
                "monnaie": MONNAIE,
                "dateCreation": TODAY,
                "statut": "active"
            }]
    return []

# ─── Parser ─────────────────────────────────────────────────────────────────────

def parse_cards(html: str, seen_links: set, category_name: str) -> list:
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select("li.item.product.product-item")
    new_records = []

    for card in cards:
        try:
            # ── Link ──────────────────────────────────────────────────────
            a_tag = card.select_one("a.product-item-link")
            if not a_tag or not a_tag.get("href"):
                continue
            link = a_tag["href"]
            if link in seen_links:
                continue

            # ── Title ─────────────────────────────────────────────────────
            # Electroplanet has two spans for title: brand and model
            spans = a_tag.find_all("span")
            title = " ".join([s.get_text(strip=True) for s in spans]) if spans else a_tag.get_text(strip=True)
            if not title:
                continue

            # ── Prices ────────────────────────────────────────────────────
            price_offer_el = card.select_one(".special-price .price") or card.select_one(".price-wrapper .price")
            price_old_el = card.select_one(".old-price .price")
            
            prix_offre = price_to_float(price_offer_el.get_text()) if price_offer_el else None
            prix_initial = price_to_float(price_old_el.get_text()) if price_old_el else None
            
            # If no old price, prix_initial = prix_offre (no discount)
            if prix_initial is None:
                prix_initial = prix_offre
            
            prix_base = prix_offre if prix_offre is not None else prix_initial

            # ── Brand/Seller ──────────────────────────────────────────────
            brand = spans[0].get_text(strip=True) if spans else "Electroplanet"

            # ── Image ─────────────────────────────────────────────────────
            img_el = card.select_one("img.product-image-photo")
            image = img_el.get("src") if img_el else ""

            # ── Record ────────────────────────────────────────────────────
            new_records.append({
                "titre": title,
                "prixInitial": prix_initial,
                "prixBase": prix_base,
                "prixOffre": prix_offre,
                "categorie": category_name,
                "location": "Electroplanet.ma",
                "statut": "actif",
                "monnaie": MONNAIE,
                "offre": build_offer(prix_initial, prix_offre) if prix_initial and prix_offre else [],
                "seller": brand,
                "rating": "",
                "image": image,
                "link": link,
                "date": TODAY,
                "source": "electroplanet_catalog"
            })
            seen_links.add(link)

        except Exception as e:
            log.debug(f"  Card parse error: {e}")

    return new_records

# ─── Main Scraper ─────────────────────────────────────────────────────────────

def scrape_electroplanet():
    all_results = []
    seen_links = set()

    # Resume support
    if OUTPUT_FILE.exists():
        try:
            all_results = json.loads(OUTPUT_FILE.read_text(encoding="utf-8"))
            seen_links = {item["link"] for item in all_results if item.get("link")}
            log.info(f"♻️ Resume: {len(all_results)} products already saved.")
        except Exception as e:
            log.warning(f"Could not load existing data: {e}")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=random.choice(UA_POOL)
        )
        page = context.new_page()
        Stealth().use_sync(page)

        # 1. Visit homepage to establish session/cookies
        try:
            log.info("🏠 Visiting homepage to establish session...")
            page.goto("https://www.electroplanet.ma/", wait_until="networkidle", timeout=60000)
            time.sleep(random.uniform(2, 4))
        except Exception as e:
            log.warning(f"  ⚠️ Homepage visit failed: {e}")

        total_extracted = len(all_results)
        
        for category_name, base_cat_url in CATEGORIES:
            if total_extracted >= TARGET_PRODUCTS:
                break
                
            log.info(f"\n📁 Starting Category: {category_name}")
            page_number = 1
            empty_streak = 0

            while total_extracted < TARGET_PRODUCTS and empty_streak < 5:
                # Optimized for bulk: use product_list_limit=all to get a full grid
                sep = "&" if "?" in base_cat_url else "?"
                current_url = f"{base_cat_url}{sep}product_list_limit=all"
                
                # If pagination is still needed for very large pages, we skip for now 
                # because limit=all handled 100+ items in tests.
                if page_number > 1:
                    current_url += f"&p={page_number}"
                
                log.info(f"  📄 Fetching: {current_url}")
                
                try:
                    page.goto(current_url, wait_until="domcontentloaded", timeout=120000)
                    
                    # Force load all products (some Magento sites lazy-load items in the grid)
                    for i in range(15):
                        page.evaluate(f"window.scrollTo(0, {i * 1000})")
                        time.sleep(1.0)
                    
                    # Wait for cards
                    try:
                        page.wait_for_selector("li.item.product.product-item", timeout=30000)
                    except: pass
                    
                except Exception as e:
                    log.warning(f"  Navigation/Timeout on {current_url}: {e}")
                    empty_streak += 1
                    page_number += 1
                    continue

                html = page.content()
                new_cards = parse_cards(html, seen_links, category_name)
                
                if new_cards:
                    all_results.extend(new_cards)
                    total_extracted = len(all_results)
                    log.info(f"    ✅ Extracted {len(new_cards)} new. Session total: {total_extracted}")
                    OUTPUT_FILE.write_text(json.dumps(all_results, ensure_ascii=False, indent=2), encoding="utf-8")
                    empty_streak = 0
                else:
                    log.info(f"    🔍 No cards found. Page title: {page.title()}")
                    # Save debug info
                    if empty_streak == 0:
                        try:
                            bn = f"debug_{category_name.replace(' ', '_')}_p{page_number}"
                            page.screenshot(path=str(LOG_FILE.parent / f"{bn}.png"))
                            (LOG_FILE.parent / f"{bn}.html").write_text(html, encoding="utf-8")
                        except: pass
                    
                    empty_streak += 1
                    log.info(f"    ∅ No new cards. Streak: {empty_streak}")

                page_number += 1
                time.sleep(random.uniform(1, 3))

        browser.close()

    log.info(f"\n🎉 Scraping finished. Final total: {len(all_results)}")
    log.info(f"💾 Saved to: {OUTPUT_FILE}")

if __name__ == "__main__":
    try:
        scrape_electroplanet()
    except KeyboardInterrupt:
        log.info("\n⚠️ Interrupted. Data saved up to now.")
