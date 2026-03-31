from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
from bs4 import BeautifulSoup
import time, random, json, urllib.parse

SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_FILE = SCRIPT_DIR.parent.parent.parent / "data" / "raw" / "amazon_full.json"
LOG_FILE    = SCRIPT_DIR.parent.parent.parent / "logs" / "amazon_scraper.log"

SEARCH_TERMS = [
    ("smartphone", "Smartphones"),
    ("laptop", "Informatique"),
    ("casque bluetooth", "Audio"),
]

MAX_PAGES = 5

# ─── Stealth script: mask headless fingerprints ───────────────────────────────
# This is the #1 reason Amazon serves CAPTCHAs — navigator.webdriver = true
STEALTH_JS = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
Object.defineProperty(navigator, 'plugins',   { get: () => [1, 2, 3, 4, 5] });
Object.defineProperty(navigator, 'languages', { get: () => ['fr-FR', 'fr', 'en-US'] });
window.chrome = { runtime: {} };
Object.defineProperty(navigator, 'permissions', {
    get: () => ({ query: () => Promise.resolve({ state: 'granted' }) })
});
const getParameter = WebGLRenderingContext.prototype.getParameter;
WebGLRenderingContext.prototype.getParameter = function(param) {
    if (param === 37445) return 'Intel Open Source Technology Center';
    if (param === 37446) return 'Mesa DRI Intel(R) HD Graphics';
    return getParameter.call(this, param);
};
"""

CAPTCHA_MARKERS = [
    "captcha", "robot", "unusual traffic", "automated access",
    "Enter the characters", "verify you are human", "ap-captcha",
    "Type the characters", "Sorry, we just need to make sure",
]

def is_captcha_page(html: str) -> bool:
    low = html.lower()
    return any(m.lower() in low for m in CAPTCHA_MARKERS)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def random_sleep(a=2, b=5):
    time.sleep(random.uniform(a, b))


def setup_page(browser):
    """Create a browser context with stealth settings."""
    ua = random.choice([
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    ])
    context = browser.new_context(
        viewport={"width": random.randint(1280, 1440), "height": random.randint(768, 900)},
        locale="fr-FR",
        timezone_id="Europe/Paris",
        user_agent=ua,
        extra_http_headers={
            "Accept-Language":           "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept":                    "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Encoding":           "gzip, deflate, br",
            "Upgrade-Insecure-Requests": "1",
            "DNT":                       "1",
        },
    )
    page = context.new_page()
    # Inject stealth patches before EVERY page load
    page.add_init_script(STEALTH_JS)
    return page


def accept_cookies(page):
    try:
        page.click("#sp-cc-accept", timeout=4000)
        random_sleep(1, 2)
    except Exception:
        try:
            page.click("text=Accepter", timeout=3000)
            random_sleep(1, 2)
        except Exception:
            pass


def human_behavior(page):
    """Simulate realistic mouse movement and scrolling."""
    # Random mouse moves
    for _ in range(random.randint(2, 4)):
        page.mouse.move(
            random.randint(200, 1000),
            random.randint(100, 600),
        )
        time.sleep(random.uniform(0.1, 0.3))

    # Gradual scroll down
    for step in [300, 600, 900, 1200]:
        page.evaluate(f"window.scrollTo(0, {step})")
        time.sleep(random.uniform(0.3, 0.7))

    random_sleep(1, 2)


def handle_captcha(page) -> bool:
    """
    Attempt to recover from a CAPTCHA page.
    Returns True if recovered, False if we should give up.

    Strategies used here (without a paid service):
      1. Wait and retry — sometimes Amazon's bot-check clears on its own.
      2. Navigate to the homepage first, then retry the search URL.
      3. If using a paid solver (2captcha / anti-captcha), integrate here.
    """
    print("  🤖 CAPTCHA detected — attempting recovery…")

    # Strategy 1: wait and go back to homepage to reset session
    time.sleep(random.uniform(15, 25))
    try:
        page.goto("https://www.amazon.fr/", wait_until="domcontentloaded", timeout=30_000)
        random_sleep(5, 10)
        accept_cookies(page)
        html = page.content()
        if not is_captcha_page(html):
            print("  ✅ CAPTCHA cleared after homepage reset")
            return True
    except Exception:
        pass

    # Strategy 2: longer wait, then try again
    print("  ⏳ Waiting 60 s before retrying…")
    time.sleep(60)
    try:
        page.goto("https://www.amazon.fr/", wait_until="domcontentloaded", timeout=30_000)
        random_sleep(3, 6)
        html = page.content()
        if not is_captcha_page(html):
            print("  ✅ CAPTCHA cleared after long wait")
            return True
    except Exception:
        pass

    print("  ❌ Could not clear CAPTCHA — skipping this batch")
    return False

    # ── Optional: integrate a paid CAPTCHA solver ─────────────────────────────
    # If you want fully automatic solving, sign up for 2captcha.com (~$3/1000 solves)
    # then uncomment and fill in:
    #
    # import requests
    # API_KEY = "YOUR_2CAPTCHA_KEY"
    #
    # # Find the sitekey from the CAPTCHA iframe
    # sitekey_el = page.query_selector("[data-sitekey]")
    # if sitekey_el:
    #     sitekey = sitekey_el.get_attribute("data-sitekey")
    #     page_url = page.url
    #     # Submit to 2captcha
    #     r = requests.post("http://2captcha.com/in.php", data={
    #         "key": API_KEY, "method": "userrecaptcha",
    #         "googlekey": sitekey, "pageurl": page_url, "json": 1
    #     })
    #     captcha_id = r.json()["request"]
    #     # Poll for result
    #     for _ in range(30):
    #         time.sleep(5)
    #         result = requests.get(
    #             f"http://2captcha.com/res.php?key={API_KEY}&action=get&id={captcha_id}&json=1"
    #         ).json()
    #         if result["status"] == 1:
    #             token = result["request"]
    #             page.evaluate(f'document.getElementById("g-recaptcha-response").value = "{token}"')
    #             page.evaluate('document.querySelector("form").submit()')
    #             random_sleep(3, 5)
    #             return True
    # return False


# ─── Parser ───────────────────────────────────────────────────────────────────

def parse_cards(html, category):
    soup = BeautifulSoup(html, "html.parser")

    # Try multiple selectors — Amazon changes class names frequently
    items = (
        soup.select("div[data-component-type='s-search-result']") or
        soup.select("div[data-asin][data-index]") or
        soup.select(".s-result-item[data-asin]")
    )

    if not items:
        print("  ⚠ No product cards found in HTML")
        return []

    results = []
    for item in items:
        try:
            asin = item.get("data-asin", "")
            if not asin:
                continue  # skip ad placeholders

            title_el = (
                item.select_one("h2 span") or
                item.select_one("[data-cy='title-recipe'] span") or
                item.select_one(".a-size-medium.a-color-base.a-text-normal")
            )
            title = title_el.get_text(strip=True) if title_el else ""
            if not title:
                continue

            price_el = item.select_one("span.a-price span.a-offscreen")
            price = price_el.get_text(strip=True) if price_el else ""

            link_el = item.select_one("h2 a")
            link = ""
            if link_el and link_el.get("href"):
                href = link_el["href"]
                link = href if href.startswith("http") else f"https://www.amazon.fr{href}"

            results.append({
                "asin":     asin,
                "title":    title,
                "price":    price,
                "category": category,
                "link":     link,
            })

        except Exception as e:
            print(f"  Parse error: {e}")

    return results


# ─── Main scraper ─────────────────────────────────────────────────────────────

def scrape():
    all_data  = []
    seen_asin = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,   # keep False while testing — easier to debug
            slow_mo=80,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ],
        )

        page = setup_page(browser)
        captcha_strikes = 0   # stop after 3 unrecoverable CAPTCHAs

        # Homepage warm-up
        print("Opening Amazon.fr…")
        page.goto("https://www.amazon.fr/", timeout=60_000)
        accept_cookies(page)
        random_sleep(3, 6)

        for term, category in SEARCH_TERMS:
            print(f"\n🔍 Searching: '{term}'")

            for page_num in range(1, MAX_PAGES + 1):
                url = f"https://www.amazon.fr/s?k={urllib.parse.quote_plus(term)}&page={page_num}"
                print(f"  📄 Page {page_num}: {url[:80]}")

                try:
                    page.goto(url, timeout=60_000)

                    # Wait for product cards (not just DOM ready)
                    try:
                        page.wait_for_selector(
                            "div[data-component-type='s-search-result'], div[data-asin][data-index]",
                            timeout=15_000,
                        )
                    except PWTimeout:
                        print("  ⚠ Selector timeout — checking for CAPTCHA…")

                    html = page.content()

                    # CAPTCHA handling
                    if is_captcha_page(html):
                        recovered = handle_captcha(page)
                        if not recovered:
                            captcha_strikes += 1
                            if captcha_strikes >= 3:
                                print("❌ Too many CAPTCHAs — stopping")
                                browser.close()
                                return all_data
                            break  # skip to next term
                        # After recovery, re-navigate to the same page
                        page.goto(url, timeout=60_000)
                        try:
                            page.wait_for_selector(
                                "div[data-component-type='s-search-result']",
                                timeout=15_000,
                            )
                        except PWTimeout:
                            break
                        html = page.content()

                    human_behavior(page)

                    cards = parse_cards(html, category)
                    print(f"  → {len(cards)} products found")

                    if not cards:
                        print("  Empty page — moving to next term")
                        break

                    # Deduplicate by ASIN
                    for card in cards:
                        if card["asin"] not in seen_asin:
                            seen_asin.add(card["asin"])
                            all_data.append(card)

                    # Incremental save
                    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                        json.dump(all_data, f, ensure_ascii=False, indent=2)

                    print(f"  Total so far: {len(all_data)}")
                    random_sleep(4, 8)   # polite delay between pages

                except Exception as e:
                    print(f"  ❌ Error on page {page_num}: {e}")
                    break

        browser.close()

    return all_data


if __name__ == "__main__":
    data = scrape()
    print(f"\n✅ Done: {len(data)} unique products saved to {OUTPUT_FILE}")