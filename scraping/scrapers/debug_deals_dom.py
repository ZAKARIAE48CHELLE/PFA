"""
Debug: what's actually in the 1.5MB Amazon deals HTML?
Dumps the first 200 div class names and any asin/deal attributes found.
"""
import re, time, random
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth
from bs4 import BeautifulSoup
from collections import Counter

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
URL = "https://www.amazon.fr/-/en/deals?ref_=nav_cs_gb&promotionsSearchPageSize=60&promotionsSearchStartIndex=0"

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=False, slow_mo=50, args=[
        "--disable-blink-features=AutomationControlled",
        "--no-sandbox",
    ])
    ctx = browser.new_context(
        viewport={"width": 1366, "height": 768},
        locale="fr-FR",
        timezone_id="Europe/Paris",
        user_agent=UA,
    )
    page = ctx.new_page()
    Stealth().use_sync(page)

    print(f"Navigating to {URL}")
    page.goto(URL, wait_until="load", timeout=90_000)
    print("Page loaded. Sleeping 8s for React hydration...")
    time.sleep(8)

    # Try dismissing cookies
    for sel in ["#sp-cc-accept", "input[name='accept']"]:
        try:
            page.click(sel, timeout=3_000)
            print("Cookie banner dismissed")
            time.sleep(1.5)
            break
        except Exception:
            pass

    # Scroll to trigger lazy loading
    for y in [500, 1000, 1500, 2000]:
        page.evaluate(f"window.scrollTo(0, {y})")
        time.sleep(1)

    time.sleep(3)
    html = page.content()
    print(f"\nHTML length: {len(html):,} bytes")

    soup = BeautifulSoup(html, "html.parser")

    # 1. Count all div class snippets
    print("\n--- TOP 40 DIV CLASS PREFIXES ---")
    class_counter = Counter()
    for div in soup.find_all("div", class_=True):
        for cls in div.get("class", []):
            # Take first 40 chars of class name as key
            class_counter[cls[:50]] += 1
    for cls, count in class_counter.most_common(40):
        print(f"  {count:4d}x  {cls}")

    # 2. Any elements with data-asin
    asin_els = soup.find_all(attrs={"data-asin": True})
    print(f"\n--- data-asin elements: {len(asin_els)} ---")
    for el in asin_els[:5]:
        print(f"  tag={el.name}  asin={el.get('data-asin')}  classes={el.get('class')}")

    # 3. Any elements with data-deal-asin
    deal_els = soup.find_all(attrs={"data-deal-asin": True})
    print(f"\n--- data-deal-asin elements: {len(deal_els)} ---")
    for el in deal_els[:5]:
        print(f"  tag={el.name}  deal-asin={el.get('data-deal-asin')}  classes={el.get('class')}")

    # 4. Search for known strings
    for keyword in ["ProductCard", "DealCard", "GridItem", "deal-card", "s-search-result", "grid-card"]:
        count = html.count(keyword)
        print(f"  '{keyword}' appears {count} times in HTML")

    # 5. Look for price patterns (€ followed by digits)
    prices = re.findall(r'€\s*[\d,\.]+', html)
    print(f"\n--- Price patterns found: {len(prices)} ---")
    print(f"  First 5: {prices[:5]}")

    # 6. Dump a raw sample of the main content area HTML
    main = soup.select_one("main") or soup.select_one("#a-page") or soup.select_one("body")
    if main:
        text_sample = main.get_text(" ", strip=True)[:500]
        print(f"\n--- Page text snippet ---\n{text_sample}")

    browser.close()
    print("\nDone.")
