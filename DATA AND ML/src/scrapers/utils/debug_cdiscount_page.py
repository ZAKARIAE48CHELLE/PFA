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
        
        print("Navigating to search page 1...")
        response = page.goto("https://www.cdiscount.com/search/10/smartphone.html", wait_until="domcontentloaded", timeout=60000)
        time.sleep(3)
        html1 = page.content()
        
        print("Navigating to search page 2...")
        response = page.goto("https://www.cdiscount.com/search/10/smartphone.html?page=2", wait_until="domcontentloaded", timeout=60000)
        time.sleep(3)
        html2 = page.content()
        
        import re
        from bs4 import BeautifulSoup
        s1 = BeautifulSoup(html1, 'html.parser')
        s2 = BeautifulSoup(html2, 'html.parser')
        
        p1 = [a.get_text(strip=True) for a in s1.select("h2.fpProductBlockTitle, [class*='ProductTitle']")][:5]
        p2 = [a.get_text(strip=True) for a in s2.select("h2.fpProductBlockTitle, [class*='ProductTitle']")][:5]
        
        print("Page 1 products:")
        for p in p1: print("-", p)
        print("Page 2 products:")
        for p in p2: print("-", p)
        
        browser.close()

if __name__ == "__main__":
    test()
