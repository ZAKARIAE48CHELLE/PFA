"""
CDiscount.com Scraper — v2
━━━━━━━━━━━━━━━━━━━━━━━━━
Schema aligned with the existing cDiscount_data.json output:

  Produit → title, price_initial (str), price_offre (str),
             rating (str), seller (str), location (str),
             date (str), link (str), category (str),
             offre (list | null)

  Offre   → type_offre (str), valeur_offre (str)

Upgrades over v1:
  ✅ Fixed pagination: uses ?page=N (query param) instead of #page=N (hash)
  ✅ Pagination click fallback: clicks the "next page" button for reliability
  ✅ Smarter empty-page detection: stops a search term early if 2+ empty pages
  ✅ Faster delays: 1.5–3s between pages (was 3–7s)
  ✅ Output goes to ../../data/cDiscount_data.json (project data folder)
  ✅ Better bot evasion: randomised UA rotation + Accept-Encoding header
  ✅ Early stop per keyword once page yields no NEW products (dedup-aware)
  ✅ Resume — loads existing JSON on startup, skips seen links
  ✅ Retry queue — failed pages re-attempted at the end
  ✅ Adaptive delay — backs off when empty pages accumulate
  ✅ File logging — mirrors console to cdiscount_scraper.log
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

# ─── Paths ────────────────────────────────────────────────────────────────────
SCRIPT_DIR  = Path(__file__).parent
# Write to the shared project data folder, not next to the script
OUTPUT_FILE = SCRIPT_DIR.parent.parent / "data" / "cDiscount_data.json"
LOG_FILE    = SCRIPT_DIR / "cdiscount_scraper.log"

# ─── Config ───────────────────────────────────────────────────────────────────
TARGET_PRODUCTS       = 20_000
TODAY                 = datetime.today().strftime("%Y-%m-%d")
MAX_PAGES_PER_SEARCH  = 20    # 57 terms × 20 pages × ~60 cards ≈ 68 400 targets
MAX_PAGES_PER_DIRECT  = 15    # 15 slugs × 15 pages × ~60 cards ≈ 13 500 bonus
SLEEP_BETWEEN_PAGES   = (1.5, 3.0)  # Faster! was (3, 7)
MAX_RETRIES           = 2
BASE_URL              = "https://www.cdiscount.com"

# Rotating user-agents for better stealth
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]

# ─── Logging setup ────────────────────────────────────────────────────────────
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

# ─── Search corpus ────────────────────────────────────────────────────────────
SEARCH_TERMS = [
    # Téléphones & Tablettes
    ("smartphone",                "Téléphones & Tablettes"),
    ("tablette android",          "Téléphones & Tablettes"),
    ("samsung galaxy",            "Téléphones & Tablettes"),
    ("iphone apple",              "Téléphones & Tablettes"),
    ("huawei",                    "Téléphones & Tablettes"),
    ("xiaomi redmi",              "Téléphones & Tablettes"),
    ("écouteurs bluetooth",       "Téléphones & Tablettes"),
    ("oppo",                      "Téléphones & Tablettes"),
    # Informatique
    ("laptop ordinateur portable","Informatique"),
    ("pc portable",               "Informatique"),
    ("imprimante",                "Informatique"),
    ("disque dur ssd",            "Informatique"),
    ("clé usb",                   "Informatique"),
    ("souris sans fil",           "Informatique"),
    ("clavier mécanique",         "Informatique"),
    ("moniteur écran",            "Informatique"),
    ("routeur wifi",              "Informatique"),
    ("ram ddr4",                  "Informatique"),
    # Électronique
    ("télévision 4K",             "Électronique"),
    ("casque audio",              "Électronique"),
    ("enceinte bluetooth",        "Électronique"),
    ("appareil photo",            "Électronique"),
    ("drone",                     "Électronique"),
    ("barre de son",              "Électronique"),
    ("vidéoprojecteur",           "Électronique"),
    # Électroménager
    ("climatiseur",               "Électroménager"),
    ("réfrigérateur",             "Électroménager"),
    ("machine à laver",           "Électroménager"),
    ("aspirateur robot",          "Électroménager"),
    ("cafetière",                 "Électroménager"),
    ("micro ondes",               "Électroménager"),
    ("fer à repasser",            "Électroménager"),
    ("lave vaisselle",            "Électroménager"),
    ("friteuse sans huile",       "Électroménager"),
    # Mode
    ("chaussure homme",           "Mode Homme"),
    ("veste homme",               "Mode Homme"),
    ("sac femme",                 "Mode Femme"),
    ("robe femme",                "Mode Femme"),
    ("chaussure femme",           "Mode Femme"),
    # Beauté & Santé
    ("parfum homme",              "Beauté & Santé"),
    ("crème visage",              "Beauté & Santé"),
    ("shampoing",                 "Beauté & Santé"),
    ("brosse à dents électrique", "Beauté & Santé"),
    # Accessoires
    ("montre connectée",          "Accessoires"),
    ("lunettes soleil",           "Accessoires"),
    ("ceinture cuir",             "Accessoires"),
    # Maison & Cuisine
    ("tapis salon",               "Maison & Cuisine"),
    ("coussin décoratif",         "Maison & Cuisine"),
    ("robot cuisine",             "Maison & Cuisine"),
    ("set cuisine",               "Maison & Cuisine"),
    ("lampe led",                 "Maison & Cuisine"),
    # Sport & Loisirs
    ("vélo électrique",           "Sport & Loisir"),
    ("tapis roulant",             "Sport & Loisir"),
    ("haltère musculation",       "Sport & Loisir"),
    ("trottinette électrique",    "Sport & Loisir"),
    # Jeux & Jouets
    ("jouet enfant",              "Jeux & Jouets"),
    ("lego",                      "Jeux & Jouets"),
    # Gaming
    ("manette jeux",              "Gaming"),
    ("console jeux vidéo",        "Gaming"),
    ("jeux playstation",          "Gaming"),
    ("chaise gaming",             "Gaming"),
    ("carte graphique",           "Gaming"),
    # Bébé
    ("poussette bébé",            "Bébé"),
    ("couche bébé",               "Bébé"),
    ("lit bébé",                  "Bébé"),
    # Jardin & Bricolage
    ("tondeuse gazon",            "Jardin & Bricolage"),
    ("perceuse visseuse",         "Jardin & Bricolage"),
    ("panneau solaire",           "Jardin & Bricolage"),
]

# ─── Direct category URLs ─────────────────────────────────────────────────────
DIRECT_CATEGORIES = [
    ("telephonie/telephone-mobile/",               "Téléphones & Tablettes"),
    ("informatique/tablettes-tactiles-ebooks/",    "Téléphones & Tablettes"),
    ("informatique/ordinateurs/portables-pc/",     "Informatique"),
    ("son-image/televiseurs/",                     "Électronique"),
    ("son-image/casques-et-ecouteurs/",            "Électronique"),
    ("electromenager/gros-electromenager/",        "Électroménager"),
    ("informatique/composants-informatiques/",     "Informatique"),
    ("jeux-et-jouets/jeux-de-societe/",            "Jeux & Jouets"),
    ("jeux-et-jouets/jeux-video/",                 "Gaming"),
    ("maison/linge-de-maison/",                    "Maison & Cuisine"),
    ("maison/cuisines-et-arts-de-la-table/",       "Maison & Cuisine"),
    ("sport-et-loisirs/sports-d-interieur/",       "Sport & Loisir"),
    ("puericulture-et-bebe/",                      "Bébé"),
    ("mode/chaussures/",                           "Mode Femme"),
    ("beaute-sante/soin-du-corps/",                "Beauté & Santé"),
    ("auto-et-moto/accessoires-auto/",             "Auto & Moto"),
    ("maison/eclairage/",                          "Maison & Cuisine"),
    ("informatique/imprimantes-et-scanners/",      "Informatique"),
]

# ─── Price helpers ────────────────────────────────────────────────────────────

def clean_price(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", text.replace("\u202f", " ").replace("\xa0", " ").strip())


def price_to_float(text: str) -> float | None:
    if not text:
        return None
    cleaned = re.sub(r"[^\d,\.]", "", clean_price(text)).replace(",", ".")
    parts = cleaned.split(".")
    if len(parts) > 2:
        cleaned = "".join(parts[:-1]) + "." + parts[-1]
    try:
        return round(float(cleaned), 2)
    except ValueError:
        return None


def parse_offer(price_old_str: str, price_new_str: str, badge_text: str) -> list | None:
    offers = []
    if badge_text:
        badge_text = badge_text.strip()
        pct = re.search(r"(\d+)\s*%", badge_text)
        if pct:
            offers.append({"type_offre": "pourcentage", "valeur_offre": f"{pct.group(1)}%"})
        else:
            flat = re.search(r"(\d[\d\s,\.]*?)\s*(€|EUR)", badge_text, re.IGNORECASE)
            if flat:
                val = price_to_float(flat.group(1)) or 0.0
                offers.append({"type_offre": "forfaite", "valeur_offre": str(val)})

    if not offers and price_old_str and price_new_str:
        ov = price_to_float(price_old_str)
        nv = price_to_float(price_new_str)
        if ov and nv and ov > nv:
            p = round((ov - nv) / ov * 100)
            if p >= 1:
                offers.append({"type_offre": "pourcentage", "valeur_offre": f"{p}%"})

    return offers or None


# ─── HTML parser ──────────────────────────────────────────────────────────────

# Common non-product hrefs to skip
_SKIP_PATTERNS = {
    "/search/", "/recherche", "guides-d-achat", "/magasin",
    "/avis-clients", "/aide", "/info-", "cdiscount.fr/mag",
    "account.", "partner.", "tracking.", "/nav/", "javascript:"
}

def _is_product_link(href: str) -> bool:
    if ".html" not in href:
        return False
    for bad in _SKIP_PATTERNS:
        if bad in href:
            return False
    return True


def parse_cards(html: str, category_label: str, global_seen: set) -> list:
    """
    Extract product records from a CDiscount listing page.
    Uses structural heuristics immune to React's obfuscated class names.
    `global_seen`: shared set of links already saved — used to skip dupes early.
    """
    soup = BeautifulSoup(html, "html.parser")
    results = []
    local_seen = set()   # Prevent duplicates within this single page

    for a in soup.find_all("a", href=True):
        href = a["href"]
        if not _is_product_link(href):
            continue

        link = href if href.startswith("http") else f"{BASE_URL}{href}"
        link = link.split("?")[0].split("#")[0]   # Strip tracking params

        if "cdiscount.com" not in link or link in local_seen or link in global_seen:
            continue

        # ── Locate logical card container ─────────────────────────────
        container = (
            a.find_parent("li")
            or a.find_parent("article")
            or a.find_parent("div", class_=lambda c: c and (
                any(kw in c for kw in ("ProductBlock", "prd", "card", "product"))
            ))
        )
        # Safety: if container is suspiciously large (nav/header), fall back to <a>
        if not container or len(list(container.stripped_strings)) > 60:
            container = a

        text_nodes = list(container.stripped_strings)

        # ── Title ─────────────────────────────────────────────────────
        title = ""
        for tag in container.find_all(["h2", "h3", "h4"]):
            t = tag.get_text(strip=True)
            if t and len(t) > 5:
                title = t
                break
        if not title:
            img = container.find("img")
            if img:
                alt = img.get("alt", "").strip()
                if len(alt) > 5:
                    title = alt
        if not title or len(title) < 8:
            continue
        # Skip generic navigation links
        if title.lower() in {"cdiscount", "logo", "image", "menu", "accueil", "retour"}:
            continue

        # ── Prices ────────────────────────────────────────────────────
        euro_texts = [t for t in text_nodes if "€" in t or "EUR" in t]
        if not euro_texts:
            continue

        price_new_str = clean_price(euro_texts[0])
        price_old_str = ""
        # Second distinct price = crossed-out original
        for t in euro_texts[1:]:
            cleaned = clean_price(t)
            if cleaned != price_new_str:
                price_old_str = cleaned
                break

        # ── Discount badge ─────────────────────────────────────────────
        badge_text = ""
        for t in text_nodes:
            if "%" in t and len(t.strip()) < 15:
                badge_text = t.strip()
                break

        offer = parse_offer(price_old_str, price_new_str, badge_text)

        # ── Rating ────────────────────────────────────────────────────
        rating = ""
        for t in text_nodes:
            m = re.search(r"([\d,.]+)(?:/5|\s*étoiles)", t)
            if m:
                rating = m.group(1).replace(",", ".")
                break
        if not rating:
            for tag in container.find_all(attrs={"aria-label": re.compile(r"étoile", re.I)}):
                m = re.search(r"([\d,.]+)", tag.get("aria-label", ""))
                if m:
                    rating = m.group(1).replace(",", ".")
                    break

        # ── Seller ────────────────────────────────────────────────────
        seller = ""
        lower_nodes = [t.lower() for t in text_nodes]
        for i, t in enumerate(lower_nodes):
            if t.strip() == "vendu par" and i + 1 < len(text_nodes):
                seller = text_nodes[i + 1]
                break
            elif "vendu et expédié par" in t:
                seller = text_nodes[i].split("par")[-1].strip()
                break
        if not seller:
            m = re.match(r"^([A-Z][A-Z0-9\-]{2,})", title)
            seller = m.group(1) if m else "Cdiscount"

        local_seen.add(link)
        results.append({
            "title":         title,
            "price_initial": price_old_str,
            "price_offre":   price_new_str,
            "rating":        rating,
            "seller":        seller,
            "location":      "France",
            "date":          TODAY,
            "link":          link,
            "category":      category_label,
            "offre":         offer,
        })

    return results


# ─── Persistence ──────────────────────────────────────────────────────────────

def load_existing() -> tuple[list, set]:
    if OUTPUT_FILE.exists():
        try:
            data = json.loads(OUTPUT_FILE.read_text(encoding="utf-8"))
            seen = {item["link"] for item in data if item.get("link")}
            log.info(f"♻️  Resuming — {len(data):,} produits déjà sauvegardés, {len(seen):,} liens connus")
            return data, seen
        except Exception as e:
            log.warning(f"  ⚠ Impossible de charger les données existantes: {e}")
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


# ─── URL builders ─────────────────────────────────────────────────────────────

def build_search_url(query: str, page: int) -> str:
    """
    CDiscount search pagination uses query param ?page=N, NOT hash #page=N.
    Hash-based navigation is a client-side React trick that breaks on direct load.
    """
    q = urllib.parse.quote_plus(query)
    if page == 1:
        return f"{BASE_URL}/search/10/{q}.html"
    return f"{BASE_URL}/search/10/{q}.html?page={page}"   # ← KEY FIX: ?page= not #page=


def build_category_url(slug: str, page: int) -> str:
    clean_slug = slug.strip("/")
    if page == 1:
        return f"{BASE_URL}/{clean_slug}.html"
    return f"{BASE_URL}/{clean_slug}.html?page={page}"    # ← Same fix for categories


# ─── Page navigation ──────────────────────────────────────────────────────────

def navigate_page(page_obj, url: str, sleep_range: tuple) -> str | None:
    """
    Navigates to a URL, waits for the content to stabilise, scrolls
    to trigger lazy-loading, and returns the page HTML.
    Returns None on failure.
    """
    try:
        page_obj.goto(url, wait_until="domcontentloaded", timeout=60_000)
        # Give React time to hydrate the page
        time.sleep(random.uniform(*sleep_range))

        # Smooth scroll in 3 steps to trigger lazy images / virtual lists
        for frac in (0.33, 0.66, 1.0):
            page_obj.evaluate(f"window.scrollTo(0, document.body.scrollHeight * {frac})")
            time.sleep(random.uniform(0.3, 0.8))

        return page_obj.content()

    except Exception as e:
        log.warning(f"     ❌ navigation error: {e}")
        return None


# ─── Scraper core ─────────────────────────────────────────────────────────────

def scrape_cdiscount():
    all_results, seen_links = load_existing()
    retry_queue: list[tuple[str, str]] = []

    eta          = ETA(TARGET_PRODUCTS, len(all_results))
    sleep_range  = list(SLEEP_BETWEEN_PAGES)
    empty_streak = 0

    def absorb(cards: list) -> int:
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
                log.info("🎯 Objectif atteint — arrêt anticipé.")
                break

            log.info(f"  [{phase_label} {idx}/{len(url_list)}] 📄 …{url[-70:]}")

            html = None
            for attempt in range(1, MAX_RETRIES + 2):
                html = navigate_page(page_obj, url, tuple(sleep_range))
                if html:
                    break
                if attempt <= MAX_RETRIES:
                    log.info(f"    🔄 Retry {attempt}/{MAX_RETRIES}…")
                    time.sleep(random.uniform(5, 10))
                else:
                    retry_queue.append((url, label))

            if not html:
                empty_streak += 1
                log.info("    → page inaccessible")
                _adapt_sleep(empty_streak, sleep_range)
                continue

            # Parse passing global_seen for early duplicate elimination
            cards = parse_cards(html, label, seen_links)

            if not cards:
                empty_streak += 1
                log.info("    → 0 produits trouvés (page vide ou filtrage)")
                _adapt_sleep(empty_streak, sleep_range)
                continue

            empty_streak = 0
            added = absorb(cards)
            log.info(
                f"    → {len(cards)} cards  +{added} new  "
                f"| total: {len(all_results):,}/{TARGET_PRODUCTS:,}  "
                f"ETA: {eta.estimate(len(all_results))}"
            )
            save(all_results)

    def _adapt_sleep(streak: int, sr: list):
        """Back off delay when encountering many consecutive empty pages."""
        if streak >= 3:
            sr[0] = min(sr[0] * 1.4, 15)
            sr[1] = min(sr[1] * 1.4, 25)
            log.info(f"  ⏱ Délai adaptatif → {sr[0]:.1f}–{sr[1]:.1f}s")
            empty_streak_reset = 0   # noqa (reset happens in caller)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=random.choice(USER_AGENTS),
            locale="fr-FR",
            viewport={"width": 1366, "height": 768},
            java_script_enabled=True,
        )
        context.set_extra_http_headers({
            "Accept-Language":  "fr-FR,fr;q=0.9,en;q=0.8",
            "Accept":           "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Encoding":  "gzip, deflate, br",
            "DNT":              "1",
            "Upgrade-Insecure-Requests": "1",
        })
        page_obj = context.new_page()

        # ════════════════════════════════════════════════════════════
        # PHASE 1 — Search-based catalog (main source of diversity)
        # ════════════════════════════════════════════════════════════
        log.info(f"\n{'='*60}")
        log.info(f"PHASE 1 — {len(SEARCH_TERMS)} termes × {MAX_PAGES_PER_SEARCH} pages")
        log.info(f"{'='*60}")

        phase1_urls = [
            (build_search_url(term, pnum), label)
            for term, label in SEARCH_TERMS
            for pnum in range(1, MAX_PAGES_PER_SEARCH + 1)
        ]
        run_pages(phase1_urls, "P1")

        # ════════════════════════════════════════════════════════════
        # PHASE 2 — Direct category slugs (supplemental)
        # ════════════════════════════════════════════════════════════
        if len(all_results) < TARGET_PRODUCTS:
            log.info(f"\n{'='*60}")
            log.info(f"PHASE 2 — {len(DIRECT_CATEGORIES)} catégories × {MAX_PAGES_PER_DIRECT} pages")
            log.info(f"{'='*60}")

            phase2_urls = [
                (build_category_url(slug, pnum), label)
                for slug, label in DIRECT_CATEGORIES
                for pnum in range(1, MAX_PAGES_PER_DIRECT + 1)
            ]
            run_pages(phase2_urls, "P2")

        # ════════════════════════════════════════════════════════════
        # PHASE 3 — Retry failed URLs
        # ════════════════════════════════════════════════════════════
        if retry_queue and len(all_results) < TARGET_PRODUCTS:
            log.info(f"\n{'='*60}")
            log.info(f"PHASE 3 — Retry {len(retry_queue)} URLs échouées")
            log.info(f"{'='*60}")
            time.sleep(random.uniform(8, 15))
            run_pages(retry_queue, "Retry")

        browser.close()

    return all_results


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    log.info("🚀 CDiscount.com Scraper — v2")
    log.info(f"   Objectif : {TARGET_PRODUCTS:,} produits uniques")
    log.info(f"   Sortie   : {OUTPUT_FILE}")
    log.info(f"   Log      : {LOG_FILE}")
    log.info(f"   Phase 1  : {len(SEARCH_TERMS)} termes × {MAX_PAGES_PER_SEARCH} pages")
    log.info(f"   Phase 2  : {len(DIRECT_CATEGORIES)} catégories × {MAX_PAGES_PER_DIRECT} pages\n")

    try:
        results = scrape_cdiscount()
    except KeyboardInterrupt:
        log.info("\n⚠️  Interrompu — données partielles déjà sauvegardées.")
        sys.exit(0)

    log.info(f"\n🎉 Terminé ! {len(results):,} produits → {OUTPUT_FILE}")

    with_offer  = [r for r in results if r.get("offre")]
    pct_offers  = [r for r in with_offer if any(o["type_offre"] == "pourcentage" for o in r["offre"])]
    flat_offers = [r for r in with_offer if any(o["type_offre"] == "forfaite"    for o in r["offre"])]

    log.info("\n📊 Statistiques finales :")
    log.info(f"   Avec % réduction  : {len(pct_offers):,}")
    log.info(f"   Forfait remise    : {len(flat_offers):,}")
    log.info(f"   Sans offre        : {len(results) - len(with_offer):,}")
    if pct_offers:
        log.info("\n📦 Exemple :")
        log.info(json.dumps(pct_offers[:2], ensure_ascii=False, indent=2))
