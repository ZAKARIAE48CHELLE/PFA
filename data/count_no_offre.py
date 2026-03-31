"""
Count elements WITHOUT an offre (offer), broken down by source and category.
Reads raw JSON files directly — no cleaned data required.
"""
import json
from pathlib import Path
from collections import defaultdict

DATA_DIR = Path(__file__).parent

FILES = {
    "Amazon"    : ("amazon_data.json",    "category", "offre"),
    "CDiscount" : ("cDiscount_data.json", "category", "offre"),
    "Jumia"     : ("jumia_data.json",     "categorie","offre"),
}

SEP   = "=" * 74
SEPM  = "-" * 74
HDR   = f"  {'SOURCE / CATEGORY':<44} {'NO OFFRE':>9} {'TOTAL':>7} {'  %':>5}"

print()
print(SEP)
print(HDR)
print(SEP)

grand_no = 0
grand_tt = 0

for source, (fname, cat_key, offre_key) in FILES.items():
    path = DATA_DIR / fname
    with open(path, encoding="utf-8") as f:
        records = json.load(f)

    by_cat_total = defaultdict(int)
    by_cat_no    = defaultdict(int)

    for r in records:
        cat   = (r.get(cat_key) or "Unknown").strip() or "Unknown"
        offre = r.get(offre_key)
        has   = offre is not None and offre != [] and offre != ""
        by_cat_total[cat] += 1
        if not has:
            by_cat_no[cat] += 1

    src_total = sum(by_cat_total.values())
    src_no    = sum(by_cat_no.values())
    grand_no  += src_no
    grand_tt  += src_total

    print(f"  {source}")
    for cat in sorted(by_cat_total):
        t   = by_cat_total[cat]
        n   = by_cat_no[cat]
        pct = n / t * 100 if t else 0
        label = cat[:42]
        print(f"    {label:<42} {n:>9,} {t:>7,} {pct:>5.1f}%")

    pct_src = src_no / src_total * 100 if src_total else 0
    print(f"  {'  SUBTOTAL':<44} {src_no:>9,} {src_total:>7,} {pct_src:>5.1f}%")
    print(SEPM)

pct_grand = grand_no / grand_tt * 100 if grand_tt else 0
print(f"  {'GRAND TOTAL':<44} {grand_no:>9,} {grand_tt:>7,} {pct_grand:>5.1f}%")
print(SEP)
print()
