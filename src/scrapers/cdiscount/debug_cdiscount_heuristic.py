import json
from bs4 import BeautifulSoup

def extract():
    html = open("debug_cdiscount2.html", encoding="utf-8").read()
    soup = BeautifulSoup(html, 'html.parser')
    
    seen = set()
    cards = []
    
    # Method 1: Find all <a> tags that look like product links
    links = soup.find_all('a', href=True)
    for a in links:
        href = a['href']
        # Product links typically have /f-xxxx-sku.html or something similar
        if '.cdiscount.com/' in href and '.html' in href and not '/search/' in href and not '/recherche.html' in href:
            # check if it contains an image inside
            img = a.find('img')
            title = ""
            if img:
                title = img.get('alt', '')
            if not title:
                # try to find first h2/h3/div with substantial text
                for tag in a.find_all(['h2', 'h3']):
                    if tag.text.strip():
                        title = tag.text.strip()
                        break
                        
            if title and len(title) > 10:
                # We probably found a product.
                # Let's find prices inside 'a' or near 'a'.
                # In cdiscount, prices are usually inside the 'a' tag.
                price_text = ""
                for child in a.stripped_strings:
                    if '€' in child:
                        price_text = child
                        break
                        
                if price_text and href not in seen:
                    seen.add(href)
                    cards.append({
                        "title": title,
                        "link": href,
                        "price": price_text
                    })
    print(f"Found {len(cards)} products using <a> tags")
    for c in cards[:5]:
        print(c)

extract()
