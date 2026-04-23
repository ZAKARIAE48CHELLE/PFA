"""
=============================================================================
  PRETREATMENT PIPELINE — AuraMarket Data Warehouse
=============================================================================
  Sources  : Amazon (amazon_data.json)
             CDiscount (cDiscount_data.json)
             Avito (avito_data.json)
             Jumia (jumia_data.json)

  Output   : data/cleaned/
               ├── amazon_clean.csv / .json
               ├── cdiscount_clean.csv / .json
               ├── avito_clean.csv / .json
               ├── jumia_clean.csv / .json
               └── unified_dataset.csv / .json

  Steps per source:
    1.  Load raw JSON
    2.  Normalize field names  → unified schema
    3.  Clean & parse prices   → float (original currency)
    4.  EUR → MAD conversion   → price_initial_mad / price_offre_mad
    5.  If price_initial is missing but price_offre exists →
          move price_offre → price_initial, clear price_offre
          (product has one listed price, no real discount offer)
    6.  Compute discount %     (scraper value → fallback computation)
          discount_pct column is ALWAYS present (null when no discount)
    7.  Parse / normalize dates
    8.  Clean ratings          → float [0, 5]
    9.  Clean titles           → strip extra whitespace
    10. Drop / flag duplicates
    11. Drop rows with no price at all
    12. Save individual + unified outputs
=============================================================================
"""

import json
import re
import math
import hashlib
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

# ─────────────────────────────────────────────
#  CONFIGURATION
# ─────────────────────────────────────────────
ROOT_DIR   = Path(__file__).parent.parent.parent
DATA_DIR   = ROOT_DIR / "data"
RAW_DIR    = DATA_DIR / "raw"
OUTPUT_DIR = DATA_DIR / "processed"
OUTPUT_DIR.mkdir(exist_ok=True)

RAW_FILES = {
    #"amazon"    : RAW_DIR / "amazon_full.json",
    #"cdiscount" : RAW_DIR / "cdiscount_full.json",
    # "avito"     : RAW_DIR / "avito_full.json",
    #"jumia"     : RAW_DIR / "jumia_full.json",
    #"steam"     : RAW_DIR / "steam_products.json",
    "jumia"     : RAW_DIR / "jumia_full2.json"

}

# Exchange rate: 1 EUR = X MAD  (update as needed)
EUR_TO_MAD = 10.85


# ─────────────────────────────────────────────
#  HELPER FUNCTIONS
# ─────────────────────────────────────────────

def load_json(path: Path) -> list:
    """Load a JSON file and return a list of records."""
    print(f"  Loading {path.name} …", end=" ")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    print(f"{len(data):,} records")
    return data


def parse_price(raw) -> float | None:
    """
    Convert a messy price string to a float.
    Examples:
        "95,66 €"            →  95.66
        "1 715,06 €"         →  1715.06
        "1 500 DH"           →  1500.0
        "9 727 DH / mois DH" →  9727.0   (monthly instalment — kept as number)
        ""                   →  None
        1500.0               →  1500.0
    """
    if raw is None or (isinstance(raw, float) and math.isnan(raw)):
        return None
    if isinstance(raw, (int, float)):
        return float(raw) if raw == raw else None        # NaN guard
    raw = str(raw).strip()
    if not raw:
        return None
    raw = raw.split("/")[0]                              # drop " / mois" suffix
    raw = re.sub(r"[€$£DH\s]", "", raw)                 # strip currency symbols
    raw = raw.replace(",", ".")                          # French decimal comma
    raw = re.sub(r"[^\d.]", "", raw)                     # keep digits & dot only
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def eur_to_mad(value: float | None) -> float | None:
    """Convert a price in EUR to MAD."""
    if value is None:
        return None
    return round(value * EUR_TO_MAD, 2)


def convert_prices_to_mad(
    price_initial: float | None,
    price_offre:   float | None,
    currency:      str,
) -> tuple[float | None, float | None]:
    """
    Return (price_initial_mad, price_offre_mad).
    - MAD sources: returned as-is.
    - EUR sources: multiplied by EUR_TO_MAD.
    """
    if currency == "EUR":
        return eur_to_mad(price_initial), eur_to_mad(price_offre)
    # MAD (Avito, Jumia) — already in MAD
    return price_initial, price_offre


def parse_rating(raw) -> float | None:
    """Parse a rating value to a float in [0, 5]."""
    if raw is None or raw == "":
        return None
    try:
        v = float(str(raw).strip())
        return round(v, 2) if 0 <= v <= 5 else None
    except ValueError:
        return None


def parse_steam_rating(raw) -> float | None:
    """
    Extract percentage from Steam rating (e.g. "très positives 91%")
    and map it to [0, 5].
    """
    if not raw or not isinstance(raw, str):
        return None
    match = re.search(r"(\d+)\s*%", raw)
    if match:
        pct = float(match.group(1))
        return round((pct / 100) * 5, 2)
    return None


def parse_discount_pct(offre_list) -> float | None:
    """
    Extract percentage discount from the 'offre' array.
    Works for both field-naming conventions:
      {"type_offre": "pourcentage", "valeur_offre": "24%"}   (Amazon / cDiscount)
      {"typeOffre":  "pourcentage", "valeurOffre":  24.0}    (Jumia)
    """
    if not offre_list:
        return None
    for item in offre_list:
        type_key  = item.get("type_offre") or item.get("typeOffre", "")
        value_key = item.get("valeur_offre") or item.get("valeurOffre")
        if str(type_key).lower() == "pourcentage" and value_key is not None:
            val = re.sub(r"[^\d.]", "", str(value_key))
            try:
                return float(val)
            except ValueError:
                pass
    return None


def compute_discount_pct(
    price_initial: float | None,
    price_offre:   float | None,
) -> float | None:
    """Compute % discount from initial and offer prices."""
    if price_initial and price_offre and price_initial > 0:
        pct = (price_initial - price_offre) / price_initial * 100
        return round(pct, 2) if pct > 0 else None
    return None


def clean_title(raw) -> str:
    if not raw:
        return ""
    return re.sub(r"\s+", " ", str(raw)).strip()


def parse_date_str(raw) -> str | None:
    """
    Normalise various date representations to ISO 'YYYY-MM-DD'.
    Handles:
        "2026-03-29"         → keep as-is
        1774656000000        → Unix-ms timestamp (Avito)
        "il y a 1 heure"     → today (best-effort)
    """
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        try:
            dt = datetime.fromtimestamp(raw / 1000, tz=timezone.utc)
            return dt.strftime("%Y-%m-%d")
        except Exception:
            return None
    raw = str(raw).strip()
    if re.match(r"^\d{4}-\d{2}-\d{2}$", raw):
        return raw
    if re.match(r"^\d{10,}$", raw):
        try:
            dt = datetime.fromtimestamp(int(raw) / 1000, tz=timezone.utc)
            return dt.strftime("%Y-%m-%d")
        except Exception:
            return None
    if any(k in raw.lower() for k in ("il y a", "heure", "minute", "jour")):
        return datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    return None


def make_row_id(source: str, link: str) -> str:
    """Stable unique ID from source + link."""
    h = hashlib.md5(f"{source}|{link}".encode()).hexdigest()[:12]
    return f"{source[:3].upper()}_{h}"


def _first_offre_type(offre_list) -> str:
    """Return the type_offre of the first offer, or empty string."""
    if not offre_list:
        return ""
    item = offre_list[0]
    return (item.get("type_offre") or item.get("typeOffre") or "").strip()


def flag_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """Mark duplicate rows based on (title_clean, price_offre, source)."""
    df = df.copy()
    df["is_duplicate"] = df.duplicated(
        subset=["title_clean", "price_offre", "source"], keep="first"
    )
    return df


# ─────────────────────────────────────────────
#  CORE ROW BUILDER
# ─────────────────────────────────────────────

def build_row(
    *,
    row_id:      str,
    source:      str,
    title:       str,
    p_init:      float | None,
    p_offre:     float | None,
    currency:    str,
    disc_pct:    float | None,
    seller:      str,
    location:    str,
    category:    str,
    rating,
    date,
    link:        str,
    offre_type:  str,
) -> dict:
    """
    Assemble a unified row.

    Price-normalisation rules
    ──────────────────────────
    Case A  price_initial AND price_offre both exist AND are different
            → real discount situation, keep both, compute discount_pct

    Case B  price_initial is missing, price_offre exists
            → only one listed price, no real discount
            → move price_offre into price_initial, clear price_offre
            → discount_pct = null

    Case C  price_initial == price_offre
            → identical prices, no discount at all
            → clear price_offre, discount_pct = null

    Case D  price_initial exists, price_offre is missing
            → single full price, no discount
            → price_offre = null, discount_pct = null

    EUR → MAD conversion applied after the above.
    """
    # ── Case B: no initial price → promote offre price to initial
    if p_init is None and p_offre is not None:
        p_init   = p_offre
        p_offre  = None
        disc_pct = None   # no real discount reference existed

    # ── Case C: both prices exist but are identical → no real discount
    elif p_init is not None and p_offre is not None and p_init == p_offre:
        p_offre  = None
        disc_pct = None

    # ── Case A: both prices exist and differ → compute discount if missing
    elif disc_pct is None and p_init is not None and p_offre is not None:
        disc_pct = compute_discount_pct(p_init, p_offre)

    # ── EUR → MAD
    p_init_mad, p_offre_mad = convert_prices_to_mad(p_init, p_offre, currency)

    return {
        "id"                : row_id,
        "source"            : source,
        "title_clean"       : clean_title(title),
        # ── Original-currency prices
        "price_initial"     : p_init,
        "price_offre"       : p_offre,
        "currency"          : currency,
        # ── MAD-normalised prices (all sources comparable)
        "price_initial_mad" : p_init_mad,
        "price_offre_mad"   : p_offre_mad,
        "eur_to_mad_rate"   : EUR_TO_MAD if currency == "EUR" else None,
        # ── Discount % (always present, null when no discount)
        "discount_pct"      : disc_pct,
        # ── Meta
        "seller"            : seller,
        "location"          : location,
        "category"          : category,
        "rating"            : parse_rating(rating),
        "date"              : parse_date_str(date),
        "link"              : link,
        "offre_type"        : offre_type,
    }


# ─────────────────────────────────────────────
#  PER-SOURCE NORMALISERS
# ─────────────────────────────────────────────

def normalise_amazon(records: list) -> pd.DataFrame:
    rows = []
    for r in records:
        p_init  = parse_price(r.get("price_initial"))
        p_offre = parse_price(r.get("price_offre"))
        rows.append(build_row(
            row_id     = make_row_id("amazon", r.get("link", "")),
            source     = "Amazon",
            title      = r.get("title", ""),
            p_init     = p_init,
            p_offre    = p_offre,
            currency   = "EUR",
            disc_pct   = parse_discount_pct(r.get("offre")),
            seller     = (r.get("seller") or "").strip(),
            location   = (r.get("location") or "Amazon.fr").strip(),
            category   = (r.get("category") or "").strip(),
            rating     = r.get("rating"),
            date       = r.get("date"),
            link       = (r.get("link") or "").strip(),
            offre_type = _first_offre_type(r.get("offre")),
        ))
    return pd.DataFrame(rows)


def normalise_cdiscount(records: list) -> pd.DataFrame:
    rows = []
    for r in records:
        p_init  = parse_price(r.get("price_initial"))
        p_offre = parse_price(r.get("price_offre"))
        rows.append(build_row(
            row_id     = make_row_id("cdiscount", r.get("link", "")),
            source     = "CDiscount",
            title      = r.get("title", ""),
            p_init     = p_init,
            p_offre    = p_offre,
            currency   = "EUR",
            disc_pct   = parse_discount_pct(r.get("offre")),
            seller     = (r.get("seller") or "").strip(),
            location   = (r.get("location") or "France").strip(),
            category   = (r.get("category") or "").strip(),
            rating     = r.get("rating"),
            date       = r.get("date"),
            link       = (r.get("link") or "").strip(),
            offre_type = _first_offre_type(r.get("offre")),
        ))
    return pd.DataFrame(rows)


def normalise_avito(records: list) -> pd.DataFrame:
    """
    Avito note: `location` field contains a relative time string
    ("il y a 1 heure"), not a place — we default to "Maroc".
    `date` is a Unix-ms timestamp.
    """
    rows = []
    for r in records:
        p_init  = parse_price(r.get("price_initial"))
        p_offre = parse_price(r.get("price_offre"))
        rows.append(build_row(
            row_id     = make_row_id("avito", r.get("link", "")),
            source     = "Avito",
            title      = r.get("title", ""),
            p_init     = p_init,
            p_offre    = p_offre,
            currency   = "MAD",
            disc_pct   = parse_discount_pct(r.get("offre")),
            seller     = (r.get("seller") or "").strip(),
            location   = "Maroc",
            category   = (r.get("category") or "").strip(),
            rating     = r.get("rating"),
            date       = r.get("date"),
            link       = (r.get("link") or "").strip(),
            offre_type = _first_offre_type(r.get("offre")),
        ))
    return pd.DataFrame(rows)


def normalise_jumia(records: list) -> pd.DataFrame:
    """
    Jumia uses different field names:
      titre / prixInitial / prixBase / prixOffre / categorie / monnaie
    """
    rows = []
    for r in records:
        p_init  = parse_price(r.get("prixInitial"))
        p_offre = parse_price(r.get("prixOffre") or r.get("prixBase"))
        rows.append(build_row(
            row_id     = make_row_id("jumia", r.get("link", "")),
            source     = "Jumia",
            title      = r.get("titre") or r.get("title", ""),
            p_init     = p_init,
            p_offre    = p_offre,
            currency   = (r.get("monnaie") or "MAD").strip(),
            disc_pct   = parse_discount_pct(r.get("offre")),
            seller     = (r.get("seller") or "").strip(),
            location   = (r.get("location") or "Maroc").strip(),
            category   = (r.get("categorie") or r.get("category") or "").strip(),
            rating     = r.get("rating"),
            date       = r.get("date"),
            link       = (r.get("link") or "").strip(),
            offre_type = _first_offre_type(r.get("offre")),
        ))
    return pd.DataFrame(rows)


def normalise_steam(records: list) -> pd.DataFrame:
    rows = []
    for r in records:
        p_init  = parse_price(r.get("prixInitial"))
        p_offre = parse_price(r.get("prixOffre"))
        rows.append(build_row(
            row_id     = make_row_id("steam", r.get("link", "")),
            source     = "Steam",
            title      = r.get("titre", ""),
            p_init     = p_init,
            p_offre    = p_offre,
            currency   = (r.get("monnaie") or "EUR").strip(),
            disc_pct   = r.get("discountPercentage"),
            seller     = (r.get("seller") or "Valve").strip(),
            location   = (r.get("location") or "Steam").strip(),
            category   = f"Steam {r.get('source', 'Games')}".strip(),
            rating     = parse_steam_rating(r.get("rating")),
            date       = r.get("date"),
            link       = (r.get("link") or "").strip(),
            offre_type = _first_offre_type(r.get("offre")),
        ))
    return pd.DataFrame(rows)


# ─────────────────────────────────────────────
#  QUALITY RULES
# ─────────────────────────────────────────────

def apply_quality_rules(df: pd.DataFrame, source: str) -> pd.DataFrame:
    """Apply cleaning rules and print a QA summary."""
    initial_count = len(df)

    # 1. Drop empty titles
    df = df[df["title_clean"].str.len() > 0].copy()

    # 2. Drop rows with absolutely no price (neither original nor MAD)
    has_price = (
        df["price_offre"].notna()
        | df["price_initial"].notna()
        | df["price_offre_mad"].notna()
        | df["price_initial_mad"].notna()
    )
    df = df[has_price].copy()

    # 3. Sanity-cap unrealistic prices (negative or > 1 000 000)
    for col in ["price_initial", "price_offre", "price_initial_mad", "price_offre_mad"]:
        df[col] = df[col].where(
            df[col].isna() | ((df[col] >= 0) & (df[col] <= 1_000_000))
        )

    # 4. Clip discount to [0, 99]
    df["discount_pct"] = df["discount_pct"].clip(0, 99)

    # 5. Mark duplicates and drop them
    df = flag_duplicates(df)
    dup_count = df["is_duplicate"].sum()
    df = df[~df["is_duplicate"]].copy()

    # ── QA report
    kept_count    = len(df)
    dropped_count = initial_count - kept_count
    # dup_count computed above
    has_disc      = df["discount_pct"].notna().sum()
    no_offre      = df["price_offre"].isna().sum()

    print(f"    [{source}]  {initial_count:>7,} raw  ->  {kept_count:>7,} kept")
    print(f"              dropped (no price)    : {dropped_count:,}")
    print(f"              rows without price_offre (single price): {no_offre:,}")
    print(f"              rows with discount_pct : {has_disc:,}")
    print(f"              duplicate rows flagged : {dup_count:,}")

    return df


# ─────────────────────────────────────────────
#  OUTPUT SCHEMA
# ─────────────────────────────────────────────

FINAL_COLUMNS = [
    "id",
    "source",
    "title_clean",
    # Original-currency prices
    "price_initial",     # always present (was price_offre if only one price existed)
    "price_offre",       # null when no real discount offer
    "currency",
    # MAD-normalised prices (all sources comparable)
    "price_initial_mad",
    "price_offre_mad",
    "eur_to_mad_rate",
    # Discount % — always present, null when there is no discount
    "discount_pct",
    # Metadata
    "seller",
    "location",
    "category",
    "rating",
    "date",
    "link",
    "offre_type",
    "is_duplicate",
]


def save(df: pd.DataFrame, name: str):
    """Save DataFrame as both CSV and JSON (only the final schema columns)."""
    df = df[FINAL_COLUMNS]
    csv_path  = OUTPUT_DIR / f"{name}.csv"
    json_path = OUTPUT_DIR / f"{name}.json"
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    df.to_json(json_path, orient="records", force_ascii=False, indent=2)
    print(f"    ✓  {name}.csv   ({len(df):,} rows)")
    print(f"    ✓  {name}.json")


# ─────────────────────────────────────────────
#  MAIN PIPELINE
# ─────────────────────────────────────────────

def run():
    print("\n" + "=" * 62)
    print("  AuraMarket — Data Pretreatment Pipeline")
    print(f"  EUR → MAD rate : 1 EUR = {EUR_TO_MAD} MAD")
    print("=" * 62 + "\n")

    frames = {}

    # ── Amazon (EUR)
    print("▶ Amazon")
    frames["amazon"] = apply_quality_rules(
        normalise_amazon(load_json(RAW_FILES["amazon"])), "Amazon"
    )
    save(frames["amazon"], "amazon_clean")

    # ── CDiscount (EUR)
    print("\n▶ CDiscount")
    frames["cdiscount"] = apply_quality_rules(
        normalise_cdiscount(load_json(RAW_FILES["cdiscount"])), "CDiscount"
    )
    save(frames["cdiscount"], "cdiscount_clean")

    # ── Avito (MAD)
    # print("\n▶ Avito")
    # frames["avito"] = apply_quality_rules(
    #     normalise_avito(load_json(RAW_FILES["avito"])), "Avito"
    # )
    # save(frames["avito"], "avito_clean")

    # ── Jumia (MAD)
    print("\n▶ Jumia")
    frames["jumia"] = apply_quality_rules(
        normalise_jumia(load_json(RAW_FILES["jumia"])), "Jumia"
    )
    save(frames["jumia"], "jumia_clean")

    # ── Steam (EUR)
    print("\n▶ Steam")
    frames["steam"] = apply_quality_rules(
        normalise_steam(load_json(RAW_FILES["steam"])), "Steam"
    )
    save(frames["steam"], "steam_clean")

    # ── Unified
    print("\n▶ Unified dataset")
    unified = pd.concat(list(frames.values()), ignore_index=True)
    unified["is_duplicate"] = unified.duplicated(
        subset=["title_clean", "price_offre_mad", "source"], keep="first"
    )
    save(unified, "unified_dataset")

    # ── Final summary
    print("\n" + "=" * 64)
    print(f"  {'SOURCE':<12} {'TOTAL':>7}  {'UNIQUE':>7}  {'W/DISCOUNT':>10}  {'W/OFFRE':>8}  {'DUPS':>6}")
    print("  " + "-" * 58)
    for src, df in frames.items():
        total      = len(df)
        unique     = total - df["is_duplicate"].sum()
        w_disc     = df["discount_pct"].notna().sum()
        w_offre    = df["price_offre"].notna().sum()
        dups       = df["is_duplicate"].sum()
        print(f"  {src:<12} {total:>7,}  {unique:>7,}  {w_disc:>10,}  {w_offre:>8,}  {dups:>6,}")
    print("  " + "-" * 58)
    u_total  = len(unified)
    u_unique = u_total - unified["is_duplicate"].sum()
    u_disc   = unified["discount_pct"].notna().sum()
    u_offre  = unified["price_offre"].notna().sum()
    u_dups   = unified["is_duplicate"].sum()
    print(f"  {'UNIFIED':<12} {u_total:>7,}  {u_unique:>7,}  {u_disc:>10,}  {u_offre:>8,}  {u_dups:>6,}")
    print(f"\n  Output → {OUTPUT_DIR.resolve()}")
    print("=" * 62 + "\n")


if __name__ == "__main__":
    run()
