"""
Amazon.fr Deals Page Scraper — v4 (Scroll-based, single-session)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ROOT CAUSE OF v3 FAILURE:
  • Amazon deals page is a React SPA with infinite scroll
  • The `promotionsSearchStartIndex` URL param is IGNORED past ~page 3
  • Every URL past that returns the SAME initial viewport (15 cards)
  • Fix: Load the page ONCE, then scroll incrementally to trigger
    React's virtual list to render new batches — collect all ASINs
    in one long session.

STRATEGY:
  • One browser session, one URL load
  • Scroll in small steps (~400px), pause, extract newly appeared cards
  • Track seen ASINs to detect when we've hit the end (no new cards
    after N consecutive scrolls)
  • Rotate context every ~500 cards to avoid detection
  • Resume support via JSON output file
"""

import json
import logging
import random
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

from bs4 import BeautifulSoup
from playwright.sync_api import TimeoutError as PWTimeout
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

# ─── Paths ────────────────────────────────────────────────────────────────────
SCRIPT_DIR  = Path(__file__).parent
OUTPUT_FILE = SCRIPT_DIR / "amazon_deals_data.json"
LOG_FILE    = SCRIPT_DIR / "amazon_deals_scraper.log"

# ─── Config ───────────────────────────────────────────────────────────────────
TARGET_PRODUCTS     = 5_000
TODAY               = datetime.today().strftime("%Y-%m-%d")
SCROLL_STEP_PX      = random.randint(380, 520)   # randomised scroll distance
SCROLL_PAUSE_S      = (1.8, 3.2)                 # pause between scrolls
MAX_EMPTY_SCROLLS   = 18    # stop session if no new cards for this many scrolls
CARDS_PER_ROTATION  = 500   # rotate browser context after this many new cards
MAX_SESSIONS        = 20    # safety cap on browser sessions

DEALS_URL = "https://www.amazon.fr/-/en/deals?ref_=nav_cs_gb"

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
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
]

CAPTCHA_MARKERS = [
    "validatecaptcha", "ap-captcha", "captchacharacters",
    "type the characters", "enter the characters",
    "verify you are human", "unusual traffic", "automated access",
    "auth-workflow",
]

ASIN_REGEX = re.compile(r"/dp/([A-Z0-9]{10})")


# ─── Browser helpers ──────────────────────────────────────────────────────────

def new_page(browser):
    ctx = browser.new_context(
        viewport={"width": random.randint(1280, 1440), "height": random.randint(768, 900)},
        locale="fr-FR",
        timezone_id="Europe/Paris",
        user_agent=random.choice(UA_POOL),
    )
    page = ctx.new_page()
    Stealth().use_sync(page)
    return page


def close_page(page):
    try:
        page.context.close()
    except Exception:
        pass


def get_block_marker(html: str) -> str | None:
    low = html.lower()
    for m in CAPTCHA_MARKERS:
        if m in low:
            return m
    return None


def dismiss_cookies(page):
    for sel in ["#sp-cc-accept", "input[name='accept']", "[data-action='accept-essential']"]:
        try:
            page.click(sel, timeout=3_000)
            log.info("  🍪 Cookie banner dismissed")
            time.sleep(1)
            return
        except Exception:
            pass


# ─── Price helpers ────────────────────────────────────────────────────────────

def clean_price(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", text.replace("\u202f", " ").replace("\xa0", " ").strip())


def price_to_float(text: str):
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


def build_offer(pct_val, price_old: str, price_new: str):
    if pct_val and pct_val > 0:
        return [{"typeOffre": "pourcentage", "valeurOffre": round(pct_val, 2),
                 "monnaie": "EUR", "dateCreation": TODAY, "statut": "active"}]
    ov, nv = price_to_float(price_old), price_to_float(price_new)
    if ov and nv and ov > nv:
        p = round((ov - nv) / ov * 100, 2)
        if p >= 1:
            return [{"typeOffre": "pourcentage", "valeurOffre": p,
                     "monnaie": "EUR", "dateCreation": TODAY, "statut": "active"}]
    return None


# ─── Card parser ──────────────────────────────────────────────────────────────

def parse_cards(html: str, already_seen_asins: set) -> list[tuple]:
    """
    Parse all div[data-asin] cards from HTML.
    Returns list of (asin, record) for cards NOT already in already_seen_asins.
    """
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.find_all(attrs={"data-asin": True})

    if not cards:
        # Fallback: look for ProductCard class
        cards = soup.select("div[class*='ProductCard-module__card']")

    new_records = []

    for card in cards:
        try:
            asin = card.get("data-asin", "").strip()

            # ── Link ──────────────────────────────────────────────────────
            a = card.select_one("a[href*='/dp/']") or card.find("a", href=True)
            link = ""
            if a and a.get("href"):
                href = a["href"]
                link = href if href.startswith("http") else f"https://www.amazon.fr{href}"
                m = ASIN_REGEX.search(link)
                if m:
                    asin = asin or m.group(1)
                    link = f"https://www.amazon.fr/dp/{m.group(1)}"

            if not asin or asin in already_seen_asins:
                continue

            # ── Title ─────────────────────────────────────────────────────
            title_el = (
                card.select_one("span.a-truncate-full") or
                card.select_one("[class*='ProductCard-module__title']") or
                card.select_one("h2 span") or
                card.select_one("p span") or
                card.select_one("p")
            )
            title = title_el.get_text(strip=True) if title_el else ""
            if not title or len(title) < 5:
                continue

            # ── Current price ─────────────────────────────────────────────
            price_el = (
                card.select_one("[data-testid='price-section'] .a-price .a-offscreen") or
                card.select_one("span.a-price > span.a-offscreen") or
                card.select_one(".a-price .a-offscreen") or
                card.select_one("span.a-price")
            )
            raw_p = price_el.get_text() if price_el else ""
            price_new_s = clean_price(re.sub(r"(?:Deal|Lowest|Price|List):\s*", "", raw_p, flags=re.I))

            # ── Original price ────────────────────────────────────────────
            orig_el = (
                card.select_one("span.a-text-price > span.a-offscreen") or
                card.select_one("span.a-text-price") or
                card.select_one(".a-text-strike")
            )
            raw_o = orig_el.get_text() if orig_el else ""
            price_old_s = clean_price(re.sub(r"(?:Deal|Lowest|Price|List):\s*", "", raw_o, flags=re.I))

            # ── Discount badge ────────────────────────────────────────────
            badge_el = (
                card.select_one("[class*='filledRoundedBadgeLabel']") or
                card.select_one("[class*='BadgeLabel']") or
                card.select_one("span.a-badge-label")
            )
            badge_text = badge_el.get_text(strip=True) if badge_el else ""
            pct_val = None
            if badge_text:
                m2 = re.search(r"(\d+)\s*%", badge_text)
                if m2:
                    pct_val = float(m2.group(1))

            # ── Rating ────────────────────────────────────────────────────
            rating_el = (
                card.select_one("span[aria-label*='étoile']") or
                card.select_one("span[aria-label*='star']") or
                card.select_one("span.a-icon-alt")
            )
            rating = ""
            if rating_el:
                raw = rating_el.get("aria-label") or rating_el.get_text(strip=True)
                m3 = re.search(r"([\d,\.]+)\s*(?:sur|out|étoile|star)", raw, re.IGNORECASE)
                if m3:
                    rating = m3.group(1).replace(",", ".")

            new_records.append((asin, {
                "asin":        asin,
                "titre":       title,
                "prixInitial": price_to_float(price_old_s),
                "prixBase":    price_to_float(price_new_s) or price_to_float(price_old_s),
                "prixOffre":   price_to_float(price_new_s),
                "categorie":   "Deals",
                "location":    "Amazon.fr",
                "statut":      "actif",
                "monnaie":     "EUR",
                "offre":       build_offer(pct_val, price_old_s, price_new_s),
                "seller":      "",
                "rating":      rating,
                "link":        link,
                "date":        TODAY,
                "source":      "deals_page",
            }))

        except Exception as e:
            log.debug(f"  Card parse error: {e}")

    return new_records


# ─── Core scroll session ──────────────────────────────────────────────────────

def run_scroll_session(browser, seen_asins: set, target_new: int) -> list:
    """
    Open the deals page once and scroll to the bottom, harvesting cards
    as they appear. Stops when:
      - target_new new cards collected, OR
      - MAX_EMPTY_SCROLLS consecutive scrolls yield nothing new
    Returns list of (asin, record).
    """
    page = new_page(browser)
    collected = []
    empty_streak = 0
    scroll_count = 0

    try:
        log.info(f"  🌐 Loading deals page…")
        page.goto(DEALS_URL, wait_until="load", timeout=90_000)
        time.sleep(4)

        html = page.content()
        if get_block_marker(html):
            log.warning("  🔴 Blocked on page load!")
            close_page(page)
            return []

        dismiss_cookies(page)
        time.sleep(2)

        # ── Initial parse (above-the-fold cards) ──────────────────────────
        initial = parse_cards(page.content(), seen_asins)
        for asin, rec in initial:
            seen_asins.add(asin)
            collected.append((asin, rec))
        log.info(f"  📦 Initial cards: {len(initial)} new")

        # ── Scroll loop ───────────────────────────────────────────────────
        while len(collected) < target_new and empty_streak < MAX_EMPTY_SCROLLS:
            scroll_count += 1

            # Scroll down by one step
            try:
                page.evaluate(f"window.scrollBy(0, {random.randint(350, 550)})")
            except Exception:
                break

            # Randomised pause — lets React render the next batch
            time.sleep(random.uniform(*SCROLL_PAUSE_S))

            # Occasionally do a small upward jitter (looks human, resets lazy-load triggers)
            if scroll_count % 7 == 0:
                page.evaluate(f"window.scrollBy(0, -{random.randint(80, 200)})")
                time.sleep(0.5)
                page.evaluate(f"window.scrollBy(0, {random.randint(200, 400)})")
                time.sleep(1)

            # Move mouse randomly every 10 scrolls
            if scroll_count % 10 == 0:
                try:
                    page.mouse.move(random.randint(200, 900), random.randint(200, 600))
                except Exception:
                    pass

            # Check for block
            html = page.content()
            if get_block_marker(html):
                log.warning("  🔴 Block detected mid-scroll!")
                break

            # Parse new cards
            new_cards = parse_cards(html, seen_asins)
            if new_cards:
                empty_streak = 0
                for asin, rec in new_cards:
                    seen_asins.add(asin)
                    collected.append((asin, rec))
                log.info(
                    f"    scroll={scroll_count:4d}  "
                    f"+{len(new_cards):2d} new  "
                    f"session_total={len(collected)}"
                )
            else:
                empty_streak += 1
                # Every 5 empty scrolls, try a bigger jump to escape stale zone
                if empty_streak % 5 == 0:
                    log.info(f"    ↕  Empty streak={empty_streak} — trying big jump…")
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    time.sleep(3)
                    page.evaluate(f"window.scrollBy(0, -{random.randint(500, 1200)})")
                    time.sleep(2)

        reason = "target reached" if len(collected) >= target_new else f"empty streak={empty_streak}"
        log.info(f"  ✅ Session done ({reason}) — {len(collected)} new cards, {scroll_count} scrolls")

    except PWTimeout:
        log.warning("  ❌ Page load timeout")
    except Exception as e:
        log.warning(f"  ❌ Session error ({type(e).__name__}): {e}")
    finally:
        close_page(page)

    return collected


# ─── Persistence ──────────────────────────────────────────────────────────────

def load_existing():
    if OUTPUT_FILE.exists():
        try:
            data = json.loads(OUTPUT_FILE.read_text(encoding="utf-8"))
            seen = set()
            for item in data:
                asin = item.get("asin") or ""
                if not asin and "/dp/" in item.get("link", ""):
                    asin = item["link"].split("/dp/")[1].split("/")[0]
                if asin:
                    seen.add(asin)
                else:
                    seen.add(item.get("titre", ""))
            log.info(f"♻️  Resume — {len(data):,} products, {len(seen):,} known ASINs")
            return data, seen
        except Exception as e:
            log.warning(f"  ⚠ Could not load existing data: {e}")
    return [], set()


def save(data: list):
    OUTPUT_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


# ─── ETA ──────────────────────────────────────────────────────────────────────

class ETA:
    def __init__(self, target, start_count):
        self.target = target
        self.start  = start_count
        self.t0     = time.time()

    def estimate(self, current):
        added   = current - self.start
        elapsed = time.time() - self.t0
        if added <= 0 or elapsed <= 0:
            return "—"
        rate = added / elapsed  # cards/sec
        remaining = self.target - current
        return str(timedelta(seconds=int(remaining / rate)))


# ─── Main ─────────────────────────────────────────────────────────────────────

def scrape_deals():
    all_results, seen_asins = load_existing()
    eta = ETA(TARGET_PRODUCTS, len(all_results))

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=False,
            slow_mo=30,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--window-size=1366,768",
                "--start-maximized",
            ],
        )

        log.info("🌐 Browser ready\n")

        for session_num in range(1, MAX_SESSIONS + 1):
            if len(all_results) >= TARGET_PRODUCTS:
                break

            remaining = TARGET_PRODUCTS - len(all_results)
            log.info(
                f"━━━ Session {session_num}/{MAX_SESSIONS} ━━━  "
                f"total={len(all_results):,}/{TARGET_PRODUCTS:,}  "
                f"ETA={eta.estimate(len(all_results))}"
            )

            # Each session targets up to CARDS_PER_ROTATION new cards
            session_target = min(remaining, CARDS_PER_ROTATION)
            new_cards = run_scroll_session(browser, seen_asins, session_target)

            if not new_cards:
                log.warning(f"  ⚠ Session {session_num} returned 0 cards — pausing 60s then retrying…")
                time.sleep(60)
                continue

            for _, rec in new_cards:
                all_results.append(rec)

            save(all_results)
            log.info(
                f"  💾 Saved {len(all_results):,} total  "
                f"ETA={eta.estimate(len(all_results))}"
            )

            if len(all_results) < TARGET_PRODUCTS:
                # Inter-session pause (Amazon deals don't rotate that fast,
                # but a pause helps avoid fingerprinting)
                wait = random.uniform(20, 45)
                log.info(f"  😴 Inter-session pause {wait:.0f}s…\n")
                time.sleep(wait)

        browser.close()

    return all_results


# ─── Entry point ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    log.info("🚀 Amazon.fr Deals Scraper — v4 (scroll-based)")
    log.info(f"   URL    : {DEALS_URL}")
    log.info(f"   Target : {TARGET_PRODUCTS:,} unique deals")
    log.info(f"   Output : {OUTPUT_FILE}")
    log.info(f"   Log    : {LOG_FILE}\n")

    try:
        results = scrape_deals()
    except KeyboardInterrupt:
        log.info("\n⚠️  Interrupted — data already saved incrementally.")
        sys.exit(0)

    log.info(f"\n🎉 Done! {len(results):,} unique deals → {OUTPUT_FILE}")
    with_offer = [r for r in results if r.get("offre")]
    pct_offers = [r for r in with_offer if any(o["typeOffre"] == "pourcentage" for o in r["offre"])]
    log.info(f"   With % discount : {len(pct_offers):,}")
    log.info(f"   No offer        : {len(results) - len(with_offer):,}")
    if pct_offers:
        log.info("\n📦 Sample:")
        log.info(json.dumps(pct_offers[:2], ensure_ascii=False, indent=2))