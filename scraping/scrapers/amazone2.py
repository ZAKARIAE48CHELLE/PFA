"""
Amazon.fr Scraper — stealth edition v2
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Upgrades over v1:
  Resume  — loads existing JSON on startup, skips already-seen ASINs
  Fixed output path — saves next to this script, not the CWD
  Smart CAPTCHA recovery — rotates context immediately, 3-strike rotation
  Retry queue — failed/empty pages re-attempted at the end
  Adaptive delays — backs off when block-rate is high
  File logging — mirrors console output to amazon_scraper.log
  Live stats — shows ETA and block-rate every page
  Graceful Ctrl-C — saves partial data before exit
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
from playwright.sync_api import TimeoutError as PWTimeout
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

# ─── Paths (always relative to this script, not CWD) ──────────────────────────
SCRIPT_DIR   = Path(__file__).parent
OUTPUT_FILE  = SCRIPT_DIR / "amazon_data.json"
LOG_FILE     = SCRIPT_DIR / "amazon_scraper.log"

# ─── Config ────────────────────────────────────────────────────────────────────
TARGET_PRODUCTS  = 10_000
TODAY            = datetime.today().strftime("%Y-%m-%d")

MAX_PAGES_SEARCH = 20     # per search term
MAX_PAGES_CAT    = 10     # per direct category
MAX_RETRIES      = 2      # retry attempts per failed page

# Delay ranges (seconds) — adaptive: widens if blocking increases
SLEEP_PAGE_BASE  = (5, 10)
SLEEP_CAPTCHA    = 60        # per-strike wait before rotating context
BLOCK_BACKOFF    = 1.5       # multiply sleep range by this after each block spike

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
    ("smartphone",          "Smartphones"),
    ("iphone",              "Smartphones"),
    ("samsung galaxy",      "Smartphones"),
    ("tablette android",    "Tablettes"),
    ("ipad",                "Tablettes"),
    ("laptop",              "Informatique"),
    ("ordinateur portable", "Informatique"),
    ("disque dur externe",  "Informatique"),
    ("clé usb",             "Informatique"),
    ("imprimante",          "Informatique"),
    ("television 4k",       "TV & Vidéo"),
    ("casque bluetooth",    "Audio"),
    ("enceinte bluetooth",  "Audio"),
    ("ecouteurs sans fil",  "Audio"),
    ("appareil photo",      "Photo & Caméra"),
    ("drone camera",        "Photo & Caméra"),
    ("montre connectée",    "Montres"),
    ("manette gaming",      "Gaming"),
    ("console jeux",        "Gaming"),
    ("souris sans fil",     "Informatique"),
    ("cafetiere",           "Électroménager"),
    ("aspirateur",          "Électroménager"),
    ("robot cuisine",       "Électroménager"),
    ("machine nespresso",   "Électroménager"),
    ("lampe led",           "Maison"),
    ("coussin canapé",      "Maison"),
    ("tapis salon",         "Maison"),
    ("parfum homme",        "Beauté"),
    ("crème visage",        "Beauté"),
    ("soin cheveux",        "Beauté"),
    ("chaussure homme",     "Mode Homme"),
    ("chaussure femme",     "Mode Femme"),
    ("sac à main",          "Mode Femme"),
    ("vélo électrique",     "Sport"),
    ("tapis roulant",       "Sport"),
    ("jouet enfant",        "Jouets"),
    ("livre roman",         "Livres"),
    ("montre homme",        "Accessoires"),
    ("lunettes soleil",     "Accessoires"),
    ("coque iphone",        "Accessoires"),
] 

DIRECT_CATEGORIES = [
    ("s?i=electronics",    "Électronique"),
    ("s?i=computers",      "Informatique"),
    ("s?i=photo",          "Photo & Caméra"),
    ("s?i=videogames",     "Jeux Vidéo"),
    ("s?i=toys-and-games", "Jouets"),
    ("s?i=kitchen",        "Cuisine"),
    ("s?i=garden",         "Jardin"),
    ("s?i=sports",         "Sports"),
    ("s?i=beauty",         "Beauté"),
    ("s?i=apparel",        "Mode"),
    ("s?i=shoes",          "Chaussures"),
    ("s?i=books",          "Livres"),
    ("s?i=home-garden",    "Maison"),
]

# ─── Bot-check markers (conservative set — avoids false positives) ─────────────
CAPTCHA_MARKERS = [
    "validatecaptcha",
    "ap-captcha",
    "captchacharacters",
    "type the characters",
    "enter the characters",
    "verify you are human",
    "unusual traffic",
    "automated access",
    "auth-workflow",
    "javascript is disabled",
    "enable javascript",
]

def is_blocked(html: str) -> bool:
    low = html.lower()
    return any(m in low for m in CAPTCHA_MARKERS)


# ─── User-agent pool ───────────────────────────────────────────────────────────
UA_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]


# ─── Browser / page factory ────────────────────────────────────────────────────
# Matches the exact setup used in the working debug_amazon.py:
#   - Minimal context (no extra headers that can fingerprint as a bot)
#   - Stealth().use_sync() after page creation

def new_page(browser):
    """Create a fresh stealth context+page — mirrors debug_amazon.py."""
    ctx = browser.new_context(
        viewport={"width": random.randint(1280, 1440), "height": random.randint(768, 900)},
        locale="fr-FR",
        timezone_id="Europe/Paris",
        user_agent=random.choice(UA_POOL),
    )
    page = ctx.new_page()
    Stealth().use_sync(page)   # same call as debug_amazon.py
    return page


def safe_new_page(browser, old_page=None):
    """Close old page gracefully, return a new stealth page."""
    if old_page:
        try:
            old_page.context.close()
        except Exception:
            pass
    pg = new_page(browser)
    time.sleep(random.uniform(3, 6))
    return pg


def human_scroll(page):
    """Gradual scroll to simulate human reading."""
    for frac in [0.25, 0.5, 0.75, 1.0]:
        try:
            page.evaluate(f"window.scrollTo(0, document.body.scrollHeight * {frac})")
            time.sleep(random.uniform(0.4, 0.9))
        except Exception:
            break
    try:
        page.mouse.move(random.randint(200, 900), random.randint(200, 600))
    except Exception:
        pass


def dismiss_cookies(page):
    """Try to click Amazon.fr cookie accept buttons."""
    for sel in ["#sp-cc-accept", "input[name='accept']", "[data-action='accept-essential']"]:
        try:
            page.click(sel, timeout=3_000)
            time.sleep(1)
            return
        except Exception:
            pass


def wait_for_content(page):
    """
    Wait strategy copied from debug_amazon.py:
      1. Fixed 6-second sleep so JS has time to render product cards.
      2. If the page is suspiciously short (< 2 000 chars), wait 4 more seconds.
    This replaces the wait_for_selector approach which would time-out and
    return a JS-disabled fallback page that triggered false-positive CAPTCHA detection.
    """
    time.sleep(6)   # ← the exact technique from the working debug script
    html = page.content()
    if len(html) < 2000:
        log.warning("  ⏳ Page seems too short — waiting 4 more seconds…")
        time.sleep(4)
        html = page.content()
    return html


# ─── Price / offer helpers ─────────────────────────────────────────────────────

def clean_price(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", text.replace("\u202f", " ").replace("\xa0", " ").strip())


def price_to_float(text: str) -> float | None:
    """Convert a raw price string (e.g. '1\u202f299,99\u00a0€') to a float."""
    if not text:
        return None
    cleaned = re.sub(r"[^\d,\.]", "", clean_price(text)).replace(",", ".")
    # Handle cases like '1.299.99' (thousand sep + decimal)
    parts = cleaned.split(".")
    if len(parts) > 2:
        cleaned = "".join(parts[:-1]) + "." + parts[-1]
    try:
        return round(float(cleaned), 2)
    except ValueError:
        return None


def parse_offer(price_old_str: str, price_new_str: str, badge: str) -> list | None:
    """
    Build Offre objects matching the UML model:
      typeOffre    : str   ('pourcentage' | 'forfaite')
      valeurOffre  : float (numeric value of the discount)
      monnaie      : str   ('EUR')
      dateCreation : str   (ISO date)
      statut       : str   ('active')
    """
    offers = []

    if badge:
        pct = re.search(r"(\d+)\s*%", badge)
        if pct:
            offers.append({
                "typeOffre":    "pourcentage",
                "valeurOffre":  float(pct.group(1)),
                "monnaie":      "EUR",
                "dateCreation": TODAY,
                "statut":       "active",
            })
        else:
            flat = re.search(r"([\d][\d\s,\.]*?)\s*(EUR|€)", badge, re.IGNORECASE)
            if flat:
                val = price_to_float(flat.group(1)) or 0.0
                offers.append({
                    "typeOffre":    "forfaite",
                    "valeurOffre":  val,
                    "monnaie":      "EUR",
                    "dateCreation": TODAY,
                    "statut":       "active",
                })
            elif badge.strip():
                offers.append({
                    "typeOffre":    "forfaite",
                    "valeurOffre":  0.0,
                    "monnaie":      "EUR",
                    "dateCreation": TODAY,
                    "statut":       "active",
                })

    # Fallback: compute % discount from price difference
    if not offers and price_old_str and price_new_str:
        ov = price_to_float(price_old_str)
        nv = price_to_float(price_new_str)
        if ov and nv and ov > nv:
            p = round((ov - nv) / ov * 100, 2)
            if p >= 1:
                offers.append({
                    "typeOffre":    "pourcentage",
                    "valeurOffre":  p,
                    "monnaie":      "EUR",
                    "dateCreation": TODAY,
                    "statut":       "active",
                })

    return offers or None


# ─── HTML card parser ──────────────────────────────────────────────────────────

def parse_cards(html: str, category: str) -> list:
    soup = BeautifulSoup(html, "html.parser")

    items = (
        soup.select("div[data-component-type='s-search-result']") or
        soup.select("div[data-asin][data-index]") or
        soup.select(".s-result-item[data-asin]")
    )

    if not items:
        snippet = soup.get_text(" ", strip=True)[:200]
        log.warning(f"  ⚠ No cards. Snippet: {snippet!r}")
        return []

    out = []
    for item in items:
        try:
            asin = item.get("data-asin", "")
            if not asin:
                continue

            # Link
            a = item.select_one("h2 a.a-link-normal") or item.select_one("a[href*='/dp/']")
            link = ""
            if a and a.get("href"):
                href = a["href"]
                link = href if href.startswith("http") else f"https://www.amazon.fr{href}"
                m = re.search(r"/dp/([A-Z0-9]{10})", link)
                if m:
                    link = f"https://www.amazon.fr/dp/{m.group(1)}"

            # Title
            t = (
                item.select_one("h2 span.a-text-normal") or
                item.select_one("[data-cy='title-recipe'] span") or
                item.select_one(".a-size-medium.a-color-base.a-text-normal") or
                item.select_one("h2 span")
            )
            title = t.get_text(strip=True) if t else ""
            if not title:
                continue

            # Prices
            pe = item.select_one("span.a-price > span.a-offscreen")
            price_offer = clean_price(pe.get_text()) if pe else ""

            oe = item.select_one("span.a-price.a-text-price > span.a-offscreen")
            price_old = clean_price(oe.get_text()) if oe else ""

            # Seller / brand
            se = (
                item.select_one(".a-size-base.s-underline-text") or
                item.select_one("[data-csa-c-slot-id*='brand']")
            )
            seller = se.get_text(strip=True) if se else ""

            # Rating
            rating = ""
            re_ = item.select_one("span[aria-label*='étoile']") or item.select_one("span.a-icon-alt")
            if re_:
                raw = re_.get("aria-label") or re_.get_text(strip=True)
                m2 = re.search(r"([\d,\.]+)\s*(?:sur|étoile|out)", raw, re.IGNORECASE)
                if m2:
                    rating = m2.group(1).replace(",", ".")

            # Discount badge
            be = (
                item.select_one(".s-coupon-highlight-color") or
                item.select_one(".a-badge-label") or
                item.select_one("[class*='deal']")
            )
            badge = be.get_text(strip=True) if be else ""
            offer = parse_offer(price_old, price_offer, badge)

            # ── Convert prices to floats as required by the Produit model ──
            prix_initial = price_to_float(price_old)
            prix_offre   = price_to_float(price_offer)
            # prixBase = best available price (offre if present, else initial)
            prix_base    = prix_offre if prix_offre else prix_initial

            out.append((asin, {
                # ─── Produit (UML model) ────────────────────────────────
                "titre":         title,
                "prixInitial":   prix_initial,   # float | None
                "prixBase":      prix_base,       # float | None  (pre-offer reference)
                "prixOffre":     prix_offre,      # float | None  (price after discount)
                "categorie":     category,
                "location":      "Amazon.fr",
                "statut":        "actif",
                "monnaie":       "EUR",
                # ─── Offre list (UML model) ─────────────────────────────
                "offre":         offer,           # list[Offre] | None
                # ─── Extra metadata (kept for frontend / debug) ─────────────
                "seller":        seller,
                "rating":        rating,
                "link":          link,
                "date":          TODAY,
            }))

        except Exception as e:
            log.warning(f"  ⚠ Card parse error: {e}")

    return out


# ─── Per-page navigator ────────────────────────────────────────────────────────

def scrape_url(page, url: str, category: str, sleep_range: tuple):
    """
    Navigate to url, scrape cards — uses debug_amazon.py's proven wait strategy.
    Returns:
      list[tuple]  — parsed cards (may be empty if page has no products)
      None         — page object died (caller must recreate)
      "blocked"    — CAPTCHA / bot-wall detected
    """
    try:
        page.goto(url, wait_until="load", timeout=90_000)

        # ── Wait for JS to render (debug_amazon.py technique) ──────────────
        html = wait_for_content(page)
        # ───────────────────────────────────────────────────────────────────

        if is_blocked(html):
            return "blocked"

        human_scroll(page)
        cards = parse_cards(html, category)
        time.sleep(random.uniform(*sleep_range))
        return cards

    except PWTimeout:
        log.warning("  ❌ Page timeout")
        return []
    except Exception as e:
        log.warning(f"  ❌ Error ({type(e).__name__}): {e}")
        return None  # signals dead page


# ─── Persistence ──────────────────────────────────────────────────────────────

def load_existing() -> tuple[list, set]:
    """Load saved data to enable resuming interrupted runs."""
    if OUTPUT_FILE.exists():
        try:
            data = json.loads(OUTPUT_FILE.read_text(encoding="utf-8"))
            seen = {item.get("link", "").split("/dp/")[-1].split("/")[0] for item in data if "/dp/" in item.get("link", "")}
            log.info(f"♻️  Resuming — loaded {len(data):,} products, {len(seen):,} known ASINs")
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
        added = current - self.start_count
        if added <= 0:
            return "—"
        elapsed = time.time() - self.start_time
        rate    = added / elapsed            # products/second
        remaining = self.target - current
        if rate <= 0:
            return "—"
        eta_sec = remaining / rate
        return str(timedelta(seconds=int(eta_sec)))


# ─── Main scraper ─────────────────────────────────────────────────────────────

def scrape():
    all_results, seen = load_existing()
    retry_queue: list[tuple[str, str]] = []   # (url, category) pairs to retry

    eta = ETA(TARGET_PRODUCTS, len(all_results))

    # Adaptive delay — widens when we get blocked frequently
    sleep_range   = list(SLEEP_PAGE_BASE)
    block_streak  = 0   # consecutive blocks
    page_counter  = 0

    def absorb(cards) -> int:
        added = 0
        for uid, item in cards:
            if uid not in seen:
                seen.add(uid)
                all_results.append(item)
                added += 1
        return added

    def handle_block(pg, browser, url_for_retry=None):
        """Rotate context on block. Returns fresh page."""
        nonlocal block_streak, sleep_range
        block_streak += 1
        log.warning(f"  🔴 BLOCKED (streak={block_streak}) — rotating context in {SLEEP_CAPTCHA}s…")
        time.sleep(SLEEP_CAPTCHA)
        if block_streak % 2 == 0:
            # Back off delays after every 2 consecutive blocks
            sleep_range[0] = min(sleep_range[0] * BLOCK_BACKOFF, 30)
            sleep_range[1] = min(sleep_range[1] * BLOCK_BACKOFF, 60)
            log.info(f"  ⏱ Adaptive delay now: {sleep_range[0]:.0f}–{sleep_range[1]:.0f}s")
        if url_for_retry:
            retry_queue.append(url_for_retry)
        return safe_new_page(browser, pg)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=False,
            slow_mo=50,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--window-size=1366,768",
                "--start-maximized",
            ],
        )

        pg = new_page(browser)

        # ── No homepage warm-up — debug_amazon.py goes directly to search ──
        # The homepage warm-up was causing an early block because Amazon
        # detects rapid homepage → search navigation as bot behaviour.
        # Instead we go straight to the first search URL (same as debug script).
        log.info("🌐 Browser ready — going directly to search pages (debug_amazon.py style)…")
        time.sleep(random.uniform(2, 4))   # brief pause before first request

        # ── Inner scrape loop (shared by Phase 1, Phase 2, and retry) ────────
        def run_pages(url_list: list[tuple[str, str]], phase_label: str):
            nonlocal pg, page_counter, block_streak, sleep_range

            total = len(url_list)
            for idx, (url, category) in enumerate(url_list, 1):
                if len(all_results) >= TARGET_PRODUCTS:
                    break

                log.info(f"  [{phase_label} {idx}/{total}] 📄 {url[-60:]}  ", )

                for attempt in range(1, MAX_RETRIES + 2):
                    result = scrape_url(pg, url, category, tuple(sleep_range))
                    page_counter += 1

                    if result == "blocked":
                        pg = handle_block(pg, browser, url_for_retry=(url, category) if attempt == MAX_RETRIES + 1 else None)
                        if attempt <= MAX_RETRIES:
                            log.info(f"    🔄 Retry {attempt}/{MAX_RETRIES}…")
                            continue
                        break

                    if result is None:
                        log.info("    🔄 Dead page — recreating…")
                        pg = safe_new_page(browser, pg)
                        if attempt <= MAX_RETRIES:
                            continue
                        break

                    block_streak = 0  # reset on success
                    added = absorb(result)
                    log.info(
                        f"    → {len(result)} cards  +{added} new  "
                        f"| total: {len(all_results):,}/{TARGET_PRODUCTS:,}  "
                        f"ETA: {eta.estimate(len(all_results))}"
                    )
                    save(all_results)
                    break

                # Rotate context every 25 pages regardless
                if page_counter > 0 and page_counter % 25 == 0:
                    log.info("  🔄 Scheduled context rotation…")
                    pg = safe_new_page(browser, pg)

        # ════════════════════════════════════════════════════════════════════
        # PHASE 1 — Search terms
        # ════════════════════════════════════════════════════════════════════
        log.info(f"\n{'='*60}")
        log.info(f"PHASE 1 — {len(SEARCH_TERMS)} terms × {MAX_PAGES_SEARCH} pages")
        log.info(f"{'='*60}")

        phase1_urls = [
            (f"https://www.amazon.fr/s?k={urllib.parse.quote_plus(term)}&page={pnum}", category)
            for term, category in SEARCH_TERMS
            for pnum in range(1, MAX_PAGES_SEARCH + 1)
        ]
        run_pages(phase1_urls, "P1")

        # ════════════════════════════════════════════════════════════════════
        # PHASE 2 — Direct categories
        # ════════════════════════════════════════════════════════════════════
        if len(all_results) < TARGET_PRODUCTS:
            log.info(f"\n{'='*60}")
            log.info(f"PHASE 2 — {len(DIRECT_CATEGORIES)} categories × {MAX_PAGES_CAT} pages")
            log.info(f"{'='*60}")

            phase2_urls = [
                (f"https://www.amazon.fr/{slug}&page={pnum}", category)
                for slug, category in DIRECT_CATEGORIES
                for pnum in range(1, MAX_PAGES_CAT + 1)
            ]
            run_pages(phase2_urls, "P2")

        # ════════════════════════════════════════════════════════════════════
        # PHASE 3 — Retry queue (URLs that failed after MAX_RETRIES)
        # ════════════════════════════════════════════════════════════════════
        if retry_queue and len(all_results) < TARGET_PRODUCTS:
            log.info(f"\n{'='*60}")
            log.info(f"PHASE 3 — Retrying {len(retry_queue)} previously-failed URLs")
            log.info(f"{'='*60}")
            # Extra long wait before retries
            time.sleep(random.uniform(30, 60))
            pg = safe_new_page(browser, pg)
            run_pages(retry_queue, "Retry")

        browser.close()

    return all_results


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    log.info("🚀 Amazon.fr Scraper — stealth edition v2")
    log.info(f"   Target  : {TARGET_PRODUCTS:,} unique products")
    log.info(f"   Output  : {OUTPUT_FILE}")
    log.info(f"   Log     : {LOG_FILE}")
    log.info(f"   Phase 1 : {len(SEARCH_TERMS)} terms × {MAX_PAGES_SEARCH} pages ≈ {len(SEARCH_TERMS)*MAX_PAGES_SEARCH*16:,} targets")
    log.info(f"   Phase 2 : {len(DIRECT_CATEGORIES)} cats  × {MAX_PAGES_CAT}  pages ≈ {len(DIRECT_CATEGORIES)*MAX_PAGES_CAT*16:,} bonus\n")

    try:
        results = scrape()
    except KeyboardInterrupt:
        log.info("\n⚠️  Interrupted by user — partial data already saved.")
        sys.exit(0)

    log.info(f"\n🎉 Done! {len(results):,} products → {OUTPUT_FILE}")

    with_offer  = [r for r in results if r.get("offre")]
    pct_offers  = [r for r in with_offer if any(o["type_offre"] == "pourcentage" for o in r["offre"])]
    flat_offers = [r for r in with_offer if any(o["type_offre"] == "forfaite"    for o in r["offre"])]

    log.info(f"\n📊 Final stats:")
    log.info(f"   % discount : {len(pct_offers):,}")
    log.info(f"   Flat deal  : {len(flat_offers):,}")
    log.info(f"   No offer   : {len(results) - len(with_offer):,}")
    if pct_offers:
        log.info("\n📦 Sample:")
        log.info(json.dumps(pct_offers[:2], ensure_ascii=False, indent=2))