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
        print("Navigating...")
        response = page.goto("https://www.cdiscount.com/recherche.html#search=smartphone", wait_until="domcontentloaded", timeout=60000)
        print("Status:", response.status)
        time.sleep(5)
        html = page.content()
        
        with open("debug_cdiscount.html", "w", encoding="utf-8") as f:
            f.write(html)
            
        print("Page title:", page.title())
        print("Lengths:", len(html))
        
        # checks
        if "DataDome" in html or "captcha" in html.lower():
            print("BLOCKED BY DATADOME")
            
        browser.close()

if __name__ == "__main__":
    test()
