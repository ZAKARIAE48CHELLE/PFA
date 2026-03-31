from bs4 import BeautifulSoup
import json

html = open("debug_cdiscount2.html", encoding="utf-8").read()
soup = BeautifulSoup(html, "html.parser")

articles = False
# How does cdiscount wrap products?
# Let's find h2 tags
h2s = soup.find_all("h2")
for i, h2 in enumerate(h2s[:10]):
    print(f"H2 {i}: class={h2.get('class')} text={h2.text[:30]}")
    # find parent a
    parent = h2.parent
    for _ in range(3):
        if parent:
            print(f"  parent {parent.name} class={parent.get('class')}")
            parent = parent.parent

print("------------------")
# Let's find prices
prices = soup.find_all(string=lambda t: "€" in t if t else False)
for p in prices[:10]:
    if p.parent:
        print(f"Price tag: {p.parent.name} class={p.parent.get('class')} string={p}")
