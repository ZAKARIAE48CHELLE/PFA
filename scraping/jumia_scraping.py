from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import json, time, random, re
from datetime import datetime

# ─── Configuration ─────────────────────────────────────────────────────────────
# Strategy: use Jumia's search catalog (/catalog/?q=keyword) which ALWAYS works,
# combined with verified direct category slugs.
# 25 keywords × 5 pages × ~40 products/page ≈ 5,000 potential products.

SEARCH_TERMS = [
    ("smartphone",          "Téléphones & Tablettes"),
    ("tablette",            "Téléphones & Tablettes"),
    ("samsung",             "Téléphones & Tablettes"),
    ("iphone",              "Téléphones & Tablettes"),
    ("laptop",              "Informatique"),
    ("ordinateur",          "Informatique"),
    ("imprimante",          "Informatique"),
    ("television",          "Électronique"),
    ("casque",              "Électronique"),
    ("enceinte",            "Électronique"),
    ("climatiseur",         "Électroménager"),
    ("refrigerateur",       "Électroménager"),
    ("machine a laver",     "Électroménager"),
    ("aspirateur",          "Électroménager"),
    ("chaussure homme",     "Mode Homme"),
    ("sac femme",           "Mode Femme"),
    ("robe",                "Mode Femme"),
    ("parfum",              "Beauté & Santé"),
    ("creme visage",        "Beauté & Santé"),
    ("tapis",               "Maison & Cuisine"),
    ("coussin",             "Maison & Cuisine"),
    ("huile cuisson",       "Épicerie"),
    ("velo",                "Sport & Loisir"),
    ("jouet enfant",        "Jeux & Jouets"),
    ("montre",              "Accessoires"),
]

# Also try verified direct category slugs as bonus
DIRECT_CATEGORIES = [
    ("phones-tablets--smartphones/",           "Téléphones & Tablettes"),
    ("tvs-audio-video/",                        "TV & Audio"),
    ("computing/",                              "Informatique"),
    ("home-living/",                            "Maison"),
    ("fashion-men-shoes/",                      "Chaussures Homme"),
    ("fashion-women-bags/",                     "Sacs Femme"),
    ("health-beauty/",                          "Beauté & Santé"),
    ("sporting-goods/",                         "Sport"),
    ("baby-products/",                          "Bébé"),
    ("garden-outdoors/",                        "Jardin"),
]

MAX_PAGES_PER_SEARCH   = 5    # 25 terms × 5 pages × ~40 = ~5,000 targets
MAX_PAGES_PER_DIRECT   = 3    # bonus from direct category URLs
SLEEP_BETWEEN_PAGES   = (2, 4)
OUTPUT_FILE           = "jumia_data.json"

TODAY = datetime.today().strftime("%Y-%m-%d")

# ─── Helpers ───────────────────────────────────────────────────────────────────

def clean_price(text: str) -> str:
    """Normalize price text: remove currency junk, keep digits + spaces + DH."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", text.replace("\u202f", " ").replace("\xa0", " ").strip())


def parse_offer(badge_text: str) -> dict:
    """
    Given a Jumia discount badge text such as '-38%' or '-50 Dhs',
    return:
      {
        "type_offre":  "pourcentage" | "forfaite",
        "valeur_offre": "38%"          | "50 Dhs"
      }
    Returns None if no offer badge found.
    """
    if not badge_text:
        return None
    badge_text = badge_text.strip()
    # Percentage  e.g. "-38%" or "38%"
    pct = re.search(r"(\d+)\s*%", badge_text)
    if pct:
        return {"type_offre": "pourcentage", "valeur_offre": f"{pct.group(1)}%"}
    # Flat deduction  e.g. "-50 Dhs" or "-200DH"
    flat = re.search(r"(\d[\d\s]*)\s*(Dhs?|MAD|DH)", badge_text, re.IGNORECASE)
    if flat:
        return {"type_offre": "forfaite", "valeur_offre": f"{flat.group(1).strip()} Dhs"}
    # If badge exists but pattern doesn't match → return raw value
    return {"type_offre": "forfaite", "valeur_offre": badge_text}


def parse_cards(html: str, category_label: str) -> list:
    """Extract all product cards from a Jumia listing page."""
    soup = BeautifulSoup(html, "html.parser")
    # Jumia uses <article class="prd _fb col c-prd"> with <a class="core"> inside
    articles = soup.select("article.prd")
    results  = []

    for art in articles:
        try:
            a_tag = art.select_one("a.core")
            link  = ""
            if a_tag and a_tag.get("href"):
                href = a_tag["href"]
                link = href if href.startswith("http") else f"https://www.jumia.ma{href}"

            # Title
            title_el = art.select_one("h3.name") or art.select_one(".name")
            title    = title_el.get_text(strip=True) if title_el else ""

            # Current price (offer price)
            price_offer_el = art.select_one("div.prc")
            price_offer    = clean_price(price_offer_el.get_text()) if price_offer_el else ""

            # Original price
            price_old_el = art.select_one("div.old")
            price_old    = clean_price(price_old_el.get_text()) if price_old_el else ""

            # Seller – shown inside the card as "Vendu par X" or in a span
            seller_el = (
                art.select_one(".aut")          # brand/seller tag
                or art.select_one("[class*='aut']")
                or art.select_one(".shps")       # shipped by
            )
            seller = seller_el.get_text(strip=True) if seller_el else ""

            # Location – Jumia rarely exposes location on listing card;
            # use seller/shipping text if present
            loc_el   = art.select_one(".loc") or art.select_one("[class*='loc']")
            location = loc_el.get_text(strip=True) if loc_el else "Maroc"

            # Discount badge  e.g. <div class="bdg _dsct _sm">-38%</div>
            badge_el   = art.select_one(".bdg._dsct") or art.select_one("[class*='dsct']")
            badge_text = badge_el.get_text(strip=True) if badge_el else ""
            offer      = parse_offer(badge_text)

            # Rating (bonus field)
            rating_el = art.select_one(".stars._s")
            stars     = ""
            if rating_el:
                style = rating_el.get("style", "")
                stars_match = re.search(r"width:\s*(\d+(?:\.\d+)?)", style)
                stars = stars_match.group(1) + "%" if stars_match else ""

            if not title:
                continue   # skip empty / ad cards

            entry = {
                "title":         title,
                "price_initial": price_old,
                "price_offre":   price_offer,
                "seller":        seller,
                "location":      location,
                "category":      category_label,
                "link":          link,
                "date":          TODAY,
                "rating":        stars,
                "offre":         offer,   # None if no discount
            }
            results.append(entry)

        except Exception as e:
            print(f"  ⚠ Card parse error: {e}")

    return results


# ─── Scraper core ──────────────────────────────────────────────────────────────

def scrape_page(page_obj, url: str, label: str) -> list:
    """Navigate to url and return parsed cards, or [] on failure."""
    try:
        page_obj.goto(url, wait_until="domcontentloaded", timeout=60000)
        time.sleep(random.uniform(*SLEEP_BETWEEN_PAGES))
        page_obj.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(1)
        return parse_cards(page_obj.content(), label)
    except Exception as e:
        print(f"     ❌ {e}")
        return []


def scrape_jumia():
    all_results = []
    seen_links  = set()

    def absorb(cards):
        new = 0
        for item in cards:
            if item["link"] and item["link"] not in seen_links:
                seen_links.add(item["link"])
                all_results.append(item)
                new += 1
        return new

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        pg = browser.new_page()
        pg.set_extra_http_headers({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
        })

        # ── Phase 1: Search-based catalog (always returns results) ──────────────
        total_terms = len(SEARCH_TERMS)
        print(f"\n{'='*55}")
        print(f"  PHASE 1 – Recherche ({total_terms} termes × {MAX_PAGES_PER_SEARCH} pages)")
        print(f"{'='*55}")

        for idx, (term, label) in enumerate(SEARCH_TERMS, 1):
            import urllib.parse
            q = urllib.parse.quote_plus(term)
            print(f"\n  [{idx}/{total_terms}] 🔍 '{term}' → {label}")

            for pnum in range(1, MAX_PAGES_PER_SEARCH + 1):
                url = f"https://www.jumia.ma/catalog/?q={q}&page={pnum}#catalog-listing"
                print(f"    📄 Page {pnum}: {url[:80]}…")
                cards = scrape_page(pg, url, label)
                print(f"         → {len(cards)} cards", end="")
                if not cards:
                    print("  (vide – arrêt)")
                    break
                new = absorb(cards)
                print(f"  +{new} nouveaux  | total: {len(all_results)}")
                _save(all_results)

                if len(all_results) >= 3000:
                    print("\n  ✅ Objectif 3000 atteint, passage à la Phase 2.")
                    break
            if len(all_results) >= 3000:
                break

        # ── Phase 2: Direct category URLs (bonus) ───────────────────────────────
        print(f"\n{'='*55}")
        print(f"  PHASE 2 – Catégories directes ({len(DIRECT_CATEGORIES)} slugs × {MAX_PAGES_PER_DIRECT} pages)")
        print(f"{'='*55}")

        for idx, (slug, label) in enumerate(DIRECT_CATEGORIES, 1):
            print(f"\n  [{idx}/{len(DIRECT_CATEGORIES)}] 🛍  {label}")
            for pnum in range(1, MAX_PAGES_PER_DIRECT + 1):
                if pnum == 1:
                    url = f"https://www.jumia.ma/{slug}"
                else:
                    url = f"https://www.jumia.ma/{slug}?page={pnum}#catalog-listing"
                print(f"    📄 Page {pnum}: {url[:80]}")
                cards = scrape_page(pg, url, label)
                print(f"         → {len(cards)} cards", end="")
                if not cards:
                    print("  (vide – arrêt)")
                    break
                new = absorb(cards)
                print(f"  +{new} nouveaux  | total: {len(all_results)}")
                _save(all_results)

        browser.close()

    return all_results


def _save(data: list):
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ─── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("🚀 Jumia Maroc Scraper – Objectif : 1 000+ produits uniques")
    print(f"   Phase 1 : {len(SEARCH_TERMS)} termes × {MAX_PAGES_PER_SEARCH} pages (~{len(SEARCH_TERMS)*MAX_PAGES_PER_SEARCH*40} cibles)")
    print(f"   Phase 2 : {len(DIRECT_CATEGORIES)} catégories × {MAX_PAGES_PER_DIRECT} pages (bonus)")
    print(f"   Fichier : {OUTPUT_FILE}")
    print()

    results = scrape_jumia()

    print(f"\n🎉 Terminé ! {len(results)} produits uniques → {OUTPUT_FILE}")

    with_offer   = [r for r in results if r.get("offre")]
    pct_offers   = [r for r in with_offer if r["offre"]["type_offre"] == "pourcentage"]
    flat_offers  = [r for r in with_offer if r["offre"]["type_offre"] == "forfaite"]

    print(f"\n📊 Statistiques :")
    print(f"   Produits avec offre %    : {len(pct_offers)}")
    print(f"   Produits avec forfait    : {len(flat_offers)}")
    print(f"   Produits sans offre      : {len(results) - len(with_offer)}")

    print("\n📦 Exemples avec offre pourcentage :")
    print(json.dumps(pct_offers[:2], ensure_ascii=False, indent=2))

