"""
Jumia Maroc Scraper — v2
━━━━━━━━━━━━━━━━━━━━━━━
Schema aligned with the UML modelisation (same as amazone2.py):

  Produit  → titre, prixInitial (float), prixBase (float), prixOffre (float),
              categorie, location, statut, monnaie, offre, seller, rating, link, date

  Offre    → typeOffre, valeurOffre (float), monnaie, dateCreation, statut

Upgrades over v1:
  ✅ UML-aligned schema (Produit + Offre)
  ✅ Target 10 000 unique products
  ✅ Resume — loads existing JSON on startup, skips seen links
  ✅ Fixed output path — saves next to this script, not CWD
  ✅ Retry queue — failed pages re-attempted at the end
  ✅ Adaptive delays — backs off when empty pages increase
  ✅ File logging — mirrors console to jumia_scraper.log
  ✅ Live ETA — shows progress every page
  ✅ Graceful Ctrl-C — partial data already saved incrementally
"""

import json
import logging
import random
import re
import sys
import time
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

# ─── Paths (always relative to this script, not CWD) ──────────────────────────
SCRIPT_DIR  = Path(__file__).parent
OUTPUT_FILE = SCRIPT_DIR / "jumia_data.json"
LOG_FILE    = SCRIPT_DIR / "jumia_scraper.log"

# ─── Config ────────────────────────────────────────────────────────────────────
TARGET_PRODUCTS       = 10_000
TODAY                 = datetime.today().strftime("%Y-%m-%d")
MAX_PAGES_PER_SEARCH  = 20    # 50 terms × 20 pages × ~40 cards ≈ 40 000 targets
MAX_PAGES_PER_DIRECT  = 10    # 15 slugs × 10 pages × ~40 cards ≈ 6 000 bonus
SLEEP_BETWEEN_PAGES   = (2, 5)
MAX_RETRIES           = 2
MONNAIE               = "MAD"

# ─── Logging setup ─────────────────────────────────────────────────────────────
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

# ─── Search corpus ─────────────────────────────────────────────────────────────
SEARCH_TERMS = [
    # Téléphones & Tablettes
    ("smartphone",           "Téléphones & Tablettes"),
    ("tablette",             "Téléphones & Tablettes"),
    ("samsung",              "Téléphones & Tablettes"),
    ("iphone",               "Téléphones & Tablettes"),
    ("huawei",               "Téléphones & Tablettes"),
    ("xiaomi",               "Téléphones & Tablettes"),
    ("ecouteurs bluetooth",  "Téléphones & Tablettes"),
    # Informatique
    ("laptop",               "Informatique"),
    ("ordinateur portable",  "Informatique"),
    ("imprimante",           "Informatique"),
    ("disque dur",           "Informatique"),
    ("clé usb",              "Informatique"),
    ("souris sans fil",      "Informatique"),
    ("clavier",              "Informatique"),
    # Électronique
    ("television",           "Électronique"),
    ("casque",               "Électronique"),
    ("enceinte bluetooth",   "Électronique"),
    ("camera",               "Électronique"),
    ("drone",                "Électronique"),
    # Électroménager
    ("climatiseur",          "Électroménager"),
    ("refrigerateur",        "Électroménager"),
    ("machine a laver",      "Électroménager"),
    ("aspirateur",           "Électroménager"),
    ("cafetiere",            "Électroménager"),
    ("micro onde",           "Électroménager"),
    ("fer repasser",         "Électroménager"),
    # Mode
    ("chaussure homme",      "Mode Homme"),
    ("chemise homme",        "Mode Homme"),
    ("sac femme",            "Mode Femme"),
    ("robe",                 "Mode Femme"),
    ("chaussure femme",      "Mode Femme"),
    # Beauté & Santé
    ("parfum",               "Beauté & Santé"),
    ("creme visage",         "Beauté & Santé"),
    ("shampoing",            "Beauté & Santé"),
    ("montre",               "Accessoires"),
    ("lunettes soleil",      "Accessoires"),
    # Maison & Cuisine
    ("tapis",                "Maison & Cuisine"),
    ("coussin",              "Maison & Cuisine"),
    ("huile cuisson",        "Épicerie"),
    ("robot cuisine",        "Maison & Cuisine"),
    # Sport & Loisirs
    ("velo",                 "Sport & Loisir"),
    ("tapis roulant",        "Sport & Loisir"),
    ("jouet enfant",         "Jeux & Jouets"),
    ("livre",                "Livres"),
    # Gaming
    ("manette",              "Gaming"),
    ("console jeux",         "Gaming"),
    ("jeux video",           "Gaming"),
    # Bébé
    ("poussette",            "Bébé"),
    ("couche bebe",          "Bébé"),
    ("jouet bebe",           "Bébé"),
]

DIRECT_CATEGORIES = [
    ("phones-tablets--smartphones/",  "Téléphones & Tablettes"),
    ("phones-tablets--tablets/",      "Tablettes"),
    ("tvs-audio-video/",              "TV & Audio"),
    ("computing/",                    "Informatique"),
    ("electronics/",                  "Électronique"),
    ("home-living/",                  "Maison"),
    ("fashion-men-shoes/",            "Chaussures Homme"),
    ("fashion-women-bags/",           "Sacs Femme"),
    ("fashion-women-clothing/",       "Mode Femme"),
    ("health-beauty/",                "Beauté & Santé"),
    ("sporting-goods/",               "Sport"),
    ("baby-products/",                "Bébé"),
    ("garden-outdoors/",              "Jardin"),
    ("video-games/",                  "Gaming"),
    ("appliances/",                   "Électroménager"),
]

# ─── Price helpers ─────────────────────────────────────────────────────────────

def clean_price(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", text.replace("\u202f", " ").replace("\xa0", " ").strip())


def price_to_float(text: str) -> float | None:
    """Convert a Jumia price string (e.g. '1 299,00 Dhs') to a float."""
    if not text:
        return None
    # Remove currency symbols and letters, keep digits , .
    cleaned = re.sub(r"[^\d,\.]", "", clean_price(text)).replace(",", ".")
    parts = cleaned.split(".")
    if len(parts) > 2:
        # '1.299.00' → thousand-sep case
        cleaned = "".join(parts[:-1]) + "." + parts[-1]
    try:
        return round(float(cleaned), 2)
    except ValueError:
        return None


def parse_offer(badge_text: str, price_old_str: str, price_new_str: str) -> list | None:
    """
    Build Offre objects matching the UML model:
      typeOffre    : str   ('pourcentage' | 'forfaite')
      valeurOffre  : float
      monnaie      : str   ('MAD')
      dateCreation : str   (ISO date)
      statut       : str   ('active')
    """
    offers = []

    if badge_text:
        badge_text = badge_text.strip()
        pct = re.search(r"(\d+)\s*%", badge_text)
        if pct:
            offers.append({
                "typeOffre":    "pourcentage",
                "valeurOffre":  float(pct.group(1)),
                "monnaie":      MONNAIE,
                "dateCreation": TODAY,
                "statut":       "active",
            })
        else:
            flat = re.search(r"(\d[\d\s,\.]*?)\s*(Dhs?|MAD|DH)", badge_text, re.IGNORECASE)
            if flat:
                val = price_to_float(flat.group(1)) or 0.0
                offers.append({
                    "typeOffre":    "forfaite",
                    "valeurOffre":  val,
                    "monnaie":      MONNAIE,
                    "dateCreation": TODAY,
                    "statut":       "active",
                })
            elif badge_text:
                offers.append({
                    "typeOffre":    "forfaite",
                    "valeurOffre":  0.0,
                    "monnaie":      MONNAIE,
                    "dateCreation": TODAY,
                    "statut":       "active",
                })

    # Fallback: compute % from price difference
    if not offers and price_old_str and price_new_str:
        ov = price_to_float(price_old_str)
        nv = price_to_float(price_new_str)
        if ov and nv and ov > nv:
            p = round((ov - nv) / ov * 100, 2)
            if p >= 1:
                offers.append({
                    "typeOffre":    "pourcentage",
                    "valeurOffre":  p,
                    "monnaie":      MONNAIE,
                    "dateCreation": TODAY,
                    "statut":       "active",
                })

    return offers or None


# ─── HTML parser ───────────────────────────────────────────────────────────────

def parse_cards(html: str, category_label: str) -> list:
    """Extract and return product records matching the UML Produit model."""
    soup = BeautifulSoup(html, "html.parser")
    articles = soup.select("article.prd")
    results  = []

    for art in articles:
        try:
            # Link (used as unique key)
            a_tag = art.select_one("a.core")
            link  = ""
            if a_tag and a_tag.get("href"):
                href = a_tag["href"]
                link = href if href.startswith("http") else f"https://www.jumia.ma{href}"

            # Title
            title_el = art.select_one("h3.name") or art.select_one(".name")
            title    = title_el.get_text(strip=True) if title_el else ""
            if not title:
                continue

            # Prices (raw strings → floats)
            price_offer_el = art.select_one("div.prc")
            price_new_str  = clean_price(price_offer_el.get_text()) if price_offer_el else ""

            price_old_el   = art.select_one("div.old")
            price_old_str  = clean_price(price_old_el.get_text()) if price_old_el else ""

            prix_offre   = price_to_float(price_new_str)
            prix_initial = price_to_float(price_old_str)
            prix_base    = prix_offre if prix_offre else prix_initial

            # Seller / brand
            seller_el = (
                art.select_one(".aut") or
                art.select_one("[class*='aut']") or
                art.select_one(".shps")
            )
            seller = seller_el.get_text(strip=True) if seller_el else ""

            # Location
            loc_el   = art.select_one(".loc") or art.select_one("[class*='loc']")
            location = loc_el.get_text(strip=True) if loc_el else "Maroc"

            # Discount badge
            badge_el   = art.select_one(".bdg._dsct") or art.select_one("[class*='dsct']")
            badge_text = badge_el.get_text(strip=True) if badge_el else ""
            offer      = parse_offer(badge_text, price_old_str, price_new_str)

            # Rating (% width → numeric)
            rating = ""
            rating_el = art.select_one(".stars._s")
            if rating_el:
                style = rating_el.get("style", "")
                m = re.search(r"width:\s*(\d+(?:\.\d+)?)", style)
                rating = m.group(1) + "%" if m else ""

            results.append({
                # ─── Produit (UML model) ─────────────────────────────────────
                "titre":       title,
                "prixInitial": prix_initial,   # float | None
                "prixBase":    prix_base,       # float | None
                "prixOffre":   prix_offre,      # float | None
                "categorie":   category_label,
                "location":    location,
                "statut":      "actif",
                "monnaie":     MONNAIE,
                # ─── Offre list (UML model) ──────────────────────────────────
                "offre":       offer,           # list[Offre] | None
                # ─── Extra metadata ──────────────────────────────────────────
                "seller":      seller,
                "rating":      rating,
                "link":        link,
                "date":        TODAY,
            })

        except Exception as e:
            log.warning(f"  ⚠ Card parse error: {e}")

    return results


# ─── Persistence ──────────────────────────────────────────────────────────────

def load_existing() -> tuple[list, set]:
    """Load saved data to enable resuming interrupted runs."""
    if OUTPUT_FILE.exists():
        try:
            data = json.loads(OUTPUT_FILE.read_text(encoding="utf-8"))
            seen = {item["link"] for item in data if item.get("link")}
            log.info(f"♻️  Resuming — loaded {len(data):,} products, {len(seen):,} known links")
            return data, seen
        except Exception as e:
            log.warning(f"  ⚠ Could not load existing data: {e}")
    return [], set()


def save(data: list):
    OUTPUT_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ─── ETA helper ───────────────────────────────────────────────────────────────

class ETA:
    def __init__(self, target: int, start_count: int):
        self.target      = target
        self.start_count = start_count
        self.start_time  = time.time()

    def estimate(self, current: int) -> str:
        added   = current - self.start_count
        elapsed = time.time() - self.start_time
        if added <= 0 or elapsed <= 0:
            return "—"
        rate      = added / elapsed
        remaining = self.target - current
        if rate <= 0:
            return "—"
        return str(timedelta(seconds=int(remaining / rate)))


# ─── Scraper core ──────────────────────────────────────────────────────────────

def scrape_page(page_obj, url: str, label: str, sleep_range: tuple) -> list:
    """Navigate to url and return parsed cards ([] on failure)."""
    try:
        page_obj.goto(url, wait_until="domcontentloaded", timeout=60_000)
        time.sleep(random.uniform(*sleep_range))
        page_obj.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(random.uniform(0.5, 1.5))
        return parse_cards(page_obj.content(), label)
    except Exception as e:
        log.warning(f"     ❌ {e}")
        return []


def scrape_jumia():
    all_results, seen_links = load_existing()
    retry_queue: list[tuple[str, str]] = []

    eta          = ETA(TARGET_PRODUCTS, len(all_results))
    sleep_range  = list(SLEEP_BETWEEN_PAGES)
    empty_streak = 0

    def absorb(cards: list, url: str = "") -> int:
        added = 0
        for item in cards:
            key = item.get("link", "")
            if key and key not in seen_links:
                seen_links.add(key)
                all_results.append(item)
                added += 1
        return added

    def run_pages(url_list: list[tuple[str, str]], phase_label: str):
        nonlocal empty_streak, sleep_range

        for idx, (url, label) in enumerate(url_list, 1):
            if len(all_results) >= TARGET_PRODUCTS:
                break

            log.info(f"  [{phase_label} {idx}/{len(url_list)}] 📄 {url[-70:]}")

            cards = []
            for attempt in range(1, MAX_RETRIES + 2):
                cards = scrape_page(page_obj, url, label, tuple(sleep_range))
                if cards:
                    break
                if attempt <= MAX_RETRIES:
                    log.info(f"    🔄 Retry {attempt}/{MAX_RETRIES}…")
                    time.sleep(random.uniform(3, 6))
                else:
                    retry_queue.append((url, label))

            if not cards:
                empty_streak += 1
                if empty_streak >= 3:
                    # Back off delays after 3 consecutive empty pages
                    sleep_range[0] = min(sleep_range[0] * 1.5, 15)
                    sleep_range[1] = min(sleep_range[1] * 1.5, 30)
                    log.info(f"  ⏱ Adaptive delay → {sleep_range[0]:.0f}–{sleep_range[1]:.0f}s")
                    empty_streak = 0
                log.info(f"    → 0 cards (vide)")
                continue

            empty_streak = 0
            added = absorb(cards, url)
            log.info(
                f"    → {len(cards)} cards  +{added} new  "
                f"| total: {len(all_results):,}/{TARGET_PRODUCTS:,}  "
                f"ETA: {eta.estimate(len(all_results))}"
            )
            save(all_results)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page_obj = browser.new_page()
        page_obj.set_extra_http_headers({
            "User-Agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
        })

        # ════════════════════════════════════════════════════════════════════
        # PHASE 1 — Search-based catalog
        # ════════════════════════════════════════════════════════════════════
        log.info(f"\n{'='*60}")
        log.info(f"PHASE 1 — {len(SEARCH_TERMS)} termes × {MAX_PAGES_PER_SEARCH} pages")
        log.info(f"{'='*60}")

        phase1_urls = [
            (f"https://www.jumia.ma/catalog/?q={urllib.parse.quote_plus(term)}&page={pnum}#catalog-listing", label)
            for term, label in SEARCH_TERMS
            for pnum in range(1, MAX_PAGES_PER_SEARCH + 1)
        ]
        run_pages(phase1_urls, "P1")

        # ════════════════════════════════════════════════════════════════════
        # PHASE 2 — Direct category slugs
        # ════════════════════════════════════════════════════════════════════
        if len(all_results) < TARGET_PRODUCTS:
            log.info(f"\n{'='*60}")
            log.info(f"PHASE 2 — {len(DIRECT_CATEGORIES)} catégories × {MAX_PAGES_PER_DIRECT} pages")
            log.info(f"{'='*60}")

            phase2_urls = []
            for slug, label in DIRECT_CATEGORIES:
                phase2_urls.append((f"https://www.jumia.ma/{slug}", label))
                for pnum in range(2, MAX_PAGES_PER_DIRECT + 1):
                    phase2_urls.append((f"https://www.jumia.ma/{slug}?page={pnum}#catalog-listing", label))
            run_pages(phase2_urls, "P2")

        # ════════════════════════════════════════════════════════════════════
        # PHASE 3 — Retry queue
        # ════════════════════════════════════════════════════════════════════
        if retry_queue and len(all_results) < TARGET_PRODUCTS:
            log.info(f"\n{'='*60}")
            log.info(f"PHASE 3 — Retry {len(retry_queue)} URLs échouées")
            log.info(f"{'='*60}")
            time.sleep(random.uniform(10, 20))
            run_pages(retry_queue, "Retry")

        browser.close()

    return all_results


# ─── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    log.info("🚀 Jumia Maroc Scraper — v2 (UML model)")
    log.info(f"   Objectif : {TARGET_PRODUCTS:,} produits uniques")
    log.info(f"   Fichier  : {OUTPUT_FILE}")
    log.info(f"   Log      : {LOG_FILE}")
    log.info(f"   Phase 1  : {len(SEARCH_TERMS)} termes × {MAX_PAGES_PER_SEARCH} pages ≈ {len(SEARCH_TERMS)*MAX_PAGES_PER_SEARCH*40:,} cibles")
    log.info(f"   Phase 2  : {len(DIRECT_CATEGORIES)} catégories × {MAX_PAGES_PER_DIRECT} pages ≈ {len(DIRECT_CATEGORIES)*MAX_PAGES_PER_DIRECT*40:,} bonus\n")

    try:
        results = scrape_jumia()
    except KeyboardInterrupt:
        log.info("\n⚠️  Interrompu — données partielles déjà sauvegardées.")
        sys.exit(0)

    log.info(f"\n🎉 Terminé ! {len(results):,} produits → {OUTPUT_FILE}")

    with_offer  = [r for r in results if r.get("offre")]
    pct_offers  = [r for r in with_offer if any(o["typeOffre"] == "pourcentage" for o in r["offre"])]
    flat_offers = [r for r in with_offer if any(o["typeOffre"] == "forfaite"    for o in r["offre"])]

    log.info(f"\n📊 Statistiques :")
    log.info(f"   % réduction : {len(pct_offers):,}")
    log.info(f"   Forfait     : {len(flat_offers):,}")
    log.info(f"   Sans offre  : {len(results) - len(with_offer):,}")
    if pct_offers:
        log.info("\n📦 Exemple :")
        log.info(json.dumps(pct_offers[:2], ensure_ascii=False, indent=2))
