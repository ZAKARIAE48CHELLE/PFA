from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth
from bs4 import BeautifulSoup
import time

MARKERS = [
    "javascript is disabled", "enable javascript",
    "validatecaptcha", "captchacharacters",
    "unusual traffic", "ap-captcha", "verify you are human",
    "automated access",
]

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, slow_mo=50)
    ctx = browser.new_context(
        locale="fr-FR",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
    page = ctx.new_page()
    Stealth().use_sync(page)

    print("Loading search page...")
    page.goto("https://www.amazon.fr/s?k=smartphone&page=1", wait_until="load", timeout=90000)
    time.sleep(6)
    html = page.content()
    low = html.lower()

    found = [m for m in MARKERS if m in low]
    if found:
        print("BLOCKED:", found)
        idx = low.index(found[0])
        print("Context:", repr(html[max(0, idx-80):idx+300]))
    else:
        soup = BeautifulSoup(html, "html.parser")
        items = soup.select("div[data-component-type='s-search-result']")
        print(f"OK! {len(items)} product cards found")
        if items:
            t = items[0].select_one("h2 span")
            print("First title:", t.get_text(strip=True) if t else "N/A")

    browser.close()
