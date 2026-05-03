import sys
import time
from playwright.sync_api import sync_playwright

def test():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            locale="fr-FR"
        )
        page = context.new_page()
        print("Navigating to search...")
        response = page.goto("https://www.cdiscount.com/search/10/smartphone.html", wait_until="domcontentloaded", timeout=60000)
        print("Search Status:", response.status)
        time.sleep(5)
        
        with open("debug_cdiscount2.html", "w", encoding="utf-8") as f:
            f.write(page.content())
            
        print("Page title:", page.title())
        print("Lengths:", len(page.content()))
        browser.close()

if __name__ == "__main__":
    test()
