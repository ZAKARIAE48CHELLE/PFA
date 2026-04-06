# Reverse-Engineered Offer Formulas From `data/raw`

This note describes how the `offre` field appears to be generated in the raw datasets under `data/raw`, using:

- direct inspection of the raw JSON files
- the scraper implementations in `src/scrapers/...`
- consistency checks between `offre`, `price_initial` / `price_offre`, and site-specific discount fields

It is a reverse-engineering report, not a statement of each website's internal business logic.

## Mathematical Formulas Only

Let:

- \( P_i \) = initial price
- \( P_o \) = offer price
- \( D \) = percentage discount
- \( B_\% \) = percentage badge already shown by the website
- \( B_f \) = flat badge amount already shown by the website

### General percentage formula

\[
D = \frac{P_i - P_o}{P_i} \times 100
\]

### Amazon `amazon_full.json`

\[
D_{amazon} =
\begin{cases}
B_\% & \text{if a percentage badge exists} \\
\operatorname{round}\left(\frac{P_i - P_o}{P_i}\times 100,\ 2\right) & \text{if } P_i > P_o \text{ and no usable badge exists} \\
\text{none} & \text{otherwise}
\end{cases}
\]

Flat/text promo case:

\[
F_{amazon} = B_f
\]

### Amazon `amazon_deals.json`

\[
D_{amazon\_deals} =
\begin{cases}
B_\% & \text{if the deals badge exists} \\
\operatorname{round}\left(\frac{P_i - P_o}{P_i}\times 100,\ 2\right) & \text{if } P_i > P_o \\
\text{none} & \text{otherwise}
\end{cases}
\]

### Jumia `jumia_full.json`

\[
D_{jumia} =
\begin{cases}
B_\% & \text{if a percentage badge exists} \\
\operatorname{round}\left(\frac{P_i - P_o}{P_i}\times 100,\ 2\right) & \text{if } P_i > P_o \text{ and no badge percent exists} \\
\text{none} & \text{otherwise}
\end{cases}
\]

Flat badge case:

\[
F_{jumia} = B_f
\]

### CDiscount `cdiscount_full.json`

\[
D_{cdiscount} =
\begin{cases}
B_\% & \text{if a percentage badge exists} \\
\operatorname{round}\left(\frac{P_i - P_o}{P_i}\times 100\right) & \text{if } P_i > P_o \text{ and no badge percent exists} \\
\text{none} & \text{otherwise}
\end{cases}
\]

Important difference: the fallback is rounded to a whole number, not 2 decimals.

### Steam `steam_products.json` and `steam_deals.json`

\[
D_{steam} = B_\%
\]

where \( B_\% \) is the discount already exposed by Steam in the page discount field.

Equivalent price relation:

\[
D_{steam} \approx \frac{P_i - P_o}{P_i} \times 100
\]

### Electroplanet `electroplanet_full.json`

\[
D_{electroplanet} =
\begin{cases}
\operatorname{round}\left(\frac{P_i - P_o}{P_i}\times 100,\ 2\right) & \text{if } P_i > P_o \text{ and } D \ge 0.1 \\
\text{none} & \text{otherwise}
\end{cases}
\]

### Avito

The current raw Avito snapshot does not let us validate a price-based formula.

Code-level badge parsing formula:

\[
D_{avito} = B_\%
\]

for percentage badges, and

\[
F_{avito} = B_f
\]

for flat badges in DH.

## Shared Percentage Formula

When a scraper computes a percentage offer from prices, the common formula is:

```text
discount_pct = ((price_initial - price_offre) / price_initial) * 100
```

The main differences across websites are:

- whether the scraper trusts a badge already shown by the site
- whether the result is rounded to an integer or to 2 decimals
- whether flat/text badges are stored as `forfaite`
- whether there is any fallback computation from prices

## Quick Summary

| Website / file | Main rule used for `offre` | Validation from raw data |
| --- | --- | --- |
| Amazon `amazon_full.json` | Badge-first; fallback to computed percent from prices | 2,462 percentage offers, 397 `forfaite`, 7,175 without offer |
| Amazon `amazon_deals.json` | Badge percent first; fallback to computed percent from prices | 473 / 473 offers are percentage-based |
| Jumia `jumia_full.json` | Badge-first; fallback to computed percent from prices | 6,894 percentage offers, 3,109 without offer |
| CDiscount `cdiscount_full.json` | Badge-first; fallback to computed integer percent from prices | 370 percentage offers, 19,651 without offer |
| Steam `steam_products.json`, `steam_deals.json` | Copy the site's `discountPercentage` / `.discount_pct` badge directly | 100 percent of offer rows match the site discount field |
| Electroplanet `electroplanet_full.json` | Always computed from old/new prices | 1,289 computed offers, 182 without offer |
| Avito `avito_old.json` | No offer field present in current raw snapshot | Cannot validate from raw file alone |

## Amazon

### Files

- `data/raw/amazon_full.json`
- `data/raw/amazon_deals.json`

### Inferred formula

Best matching scraper logic:

- `src/scrapers/amazon/amazone2.py`
- `src/scrapers/amazon/amazon_deals.py`

For the regular catalog-style data, the logic is:

```text
if badge contains N%:
    offre = [{"type_offre/typeOffre": "pourcentage", "valeur_offre/valeurOffre": N}]
elif badge contains an amount in EUR:
    offre = [{"type_offre/typeOffre": "forfaite", "valeur_offre/valeurOffre": amount}]
elif badge is non-empty text:
    offre = [{"type_offre/typeOffre": "forfaite", "valeur_offre/valeurOffre": raw_badge_text_or_0}]
elif price_initial > price_offre:
    offre_pct = round(((price_initial - price_offre) / price_initial) * 100, 2)
    if offre_pct >= 1:
        offre = percentage offer
else:
    offre = None
```

For the deals page:

```text
if explicit badge percent exists:
    offre_pct = badge_percent
elif price_initial > price_offre:
    offre_pct = round(((price_initial - price_offre) / price_initial) * 100, 2)
    if offre_pct >= 1:
        offre = percentage offer
else:
    offre = None
```

### Explanation

- Amazon is badge-first. If the page already exposes a discount or promo badge, the scraper keeps that badge as the offer.
- If there is no usable badge but both prices exist, the scraper computes the percentage from the old and new prices.
- `amazon_full.json` also stores non-discount promotional text as `forfaite`, for example `Exclusivite Amazon` and `Offre a duree limitee`.

### Raw-data validation

- `amazon_full.json`: 10,034 rows total
- 2,462 rows contain percentage offers
- 397 rows contain `forfaite` offers
- 7,175 rows have no offer
- 2,320 of the 2,462 percentage offers are within 1 point of the price-difference formula
- The remaining mismatches are mostly caused by textual promo badges or noisy price extraction

- `amazon_deals.json`: 473 rows total
- 473 of 473 rows contain percentage offers
- 473 of 473 are within 1 point of the price-difference formula

## Jumia

### File

- `data/raw/jumia_full.json`

### Inferred formula

Matching scraper logic:

- `src/scrapers/jumia/jumia_scraping.py`

```text
if badge contains N%:
    offre = [{"typeOffre": "pourcentage", "valeurOffre": float(N)}]
elif badge contains amount in Dhs / MAD / DH:
    offre = [{"typeOffre": "forfaite", "valeurOffre": amount}]
elif badge is non-empty but not parseable:
    offre = [{"typeOffre": "forfaite", "valeurOffre": 0.0}]
elif price_initial > price_offre:
    offre_pct = round(((price_initial - price_offre) / price_initial) * 100, 2)
    if offre_pct >= 1:
        offre = percentage offer
else:
    offre = None
```

### Explanation

- Jumia also uses badge-first logic.
- If the discount badge is already present, the scraper stores it directly.
- If there is no badge, it computes the percentage from `prixInitial` and `prixOffre`.
- In the current raw file, almost all offers are percentage offers; no meaningful flat offers are present in practice.

### Raw-data validation

- 10,003 rows total
- 6,894 rows contain percentage offers
- 3,109 rows have no offer
- 6,863 of the 6,894 percentage offers are within 1 point of the price-difference formula
- The small mismatch set is mostly explained by malformed raw price strings in some cards

## CDiscount

### File

- `data/raw/cdiscount_full.json`

### Inferred formula

Matching scraper logic:

- `src/scrapers/cdiscount/cdiscount_scraping.py`

```text
if badge contains N%:
    offre = [{"type_offre": "pourcentage", "valeur_offre": f"{N}%"}]
elif badge contains amount in EUR:
    offre = [{"type_offre": "forfaite", "valeur_offre": amount}]
elif price_initial > price_offre:
    offre_pct = round(((price_initial - price_offre) / price_initial) * 100)
    if offre_pct >= 1:
        offre = [{"type_offre": "pourcentage", "valeur_offre": f"{offre_pct}%"}]
else:
    offre = None
```

### Explanation

- CDiscount is also badge-first.
- The important difference is the fallback rounding: it rounds to a whole percent, not 2 decimals.
- In many rows the scraper captures a discount badge even when the raw old price is missing or unreliable, so the badge and the price fields do not always line up cleanly.

### Raw-data validation

- 20,021 rows total
- 370 rows contain percentage offers
- 19,651 rows have no offer
- 344 of the 370 offer rows also have both prices available
- 189 of those 344 rows are within 1 point of the price-difference formula
- This lower agreement strongly suggests the badge is often the real source of truth, while the captured old price is incomplete or noisy

## Steam

### Files

- `data/raw/steam_products.json`
- `data/raw/steam_deals.json`

### Inferred formula

Matching scraper logic:

- `src/scrapers/steam/scraper_steam_deals.py`

```text
discount_pct = numeric value read from the site's ".discount_pct" element

if discount_pct exists:
    offre = [{"typeOffre": "pourcentage", "valeurOffre": discount_pct}]
else:
    offre = []
```

Equivalent arithmetic relation when both prices exist:

```text
discount_pct ~= ((prixInitial - prixOffre) / prixInitial) * 100
```

### Explanation

- Steam does not really generate the offer inside the scraper. The scraper mostly copies the discount already exposed by the page.
- The computed percentage from prices matches the stored `discountPercentage` very closely, with tiny differences only from price rounding to cents.
- There is no fallback branch that invents a discount when `.discount_pct` is missing.

### Raw-data validation

- `steam_products.json`: 5,657 rows, 1,296 percentage offers, 4,361 without offer
- `steam_products.json`: all 1,296 offer rows are within 1 point of the price-difference formula
- `steam_products.json`: `discountPercentage` matches `offre.valeurOffre` in all 1,296 offer rows

- `steam_deals.json`: 1,000 rows, 528 percentage offers, 472 without offer
- `steam_deals.json`: all 528 offer rows are within 1 point of the price-difference formula
- `steam_deals.json`: `discountPercentage` matches `offre.valeurOffre` in all 528 offer rows

## Electroplanet

### File

- `data/raw/electroplanet_full.json`

### Inferred formula

Matching scraper logic:

- `src/scrapers/electroplanet/electroplanet_scraper.py`

```text
if price_initial and price_offre and price_initial > price_offre:
    offre_pct = round(((price_initial - price_offre) / price_initial) * 100, 2)
    if offre_pct >= 0.1:
        offre = [{"typeOffre": "pourcentage", "valeurOffre": offre_pct}]
    else:
        offre = []
else:
    offre = []
```

### Explanation

- Electroplanet is the cleanest case in this repo.
- The scraper does not parse a badge first; it computes the offer directly from the old and new prices.
- The threshold is lower than the other sites: any discount of at least `0.1%` is kept.

### Raw-data validation

- 1,471 rows total
- 1,289 rows contain percentage offers
- 182 rows have no offer
- 1,289 of 1,289 offer rows match the price-difference formula exactly

## Avito

### Raw files present

- `data/raw/avito_old.json`
- `data/raw/avito_full.json`

### Important caveat

`avito_full.json` is not actually a raw Avito file.

It contains processed mixed-source rows with these `source` counts:

- `Jumia`: 10,003
- `Amazon`: 7,468
- `CDiscount`: 638

So it should not be used as evidence for Avito offer generation.

### What the Avito scraper would do

Matching scraper logic:

- `src/scrapers/avito/avito_scraping.py`

```text
if badge text contains N%:
    offre = {"type_offre": "pourcentage", "valeur_offre": f"{N}%"}
elif badge text contains amount in DH / MAD / Dhs:
    offre = {"type_offre": "forfaite", "valeur_offre": f"{amount} DH"}
elif badge text is non-empty:
    offre = {"type_offre": "forfaite", "valeur_offre": raw_badge_text}
else:
    offre = None
```

### What the current raw Avito data shows

- `avito_old.json` has 6,133 rows
- it contains only `title`, `price`, `seller`, `location`, `category`, and `link`
- it contains no `offre`, no `price_initial`, and no discount badge snapshot

Conclusion: the current raw Avito snapshot does not let us validate an offer formula from data alone. We can only document the formula implemented in the scraper code.

## Downstream Note: Processed `discount_pct`

After raw scraping, `src/processing/pretreatment.py` can compute a unified `discount_pct` when:

```text
price_initial is present
and price_offre is present
and the scraper did not already provide a usable percentage
```

The processing formula is:

```text
discount_pct = round(((price_initial - price_offre) / price_initial) * 100, 2)
```

That is post-processing logic, not raw `offre` generation.

## Final Takeaways

- Amazon, Jumia, and CDiscount are primarily badge-first scrapers with a price-based fallback.
- Steam copies the site's discount field directly.
- Electroplanet computes the percentage directly from prices every time.
- Avito's implemented logic is text-badge parsing only, but the current raw Avito file does not contain enough fields to validate it.
- `avito_full.json` is mislabeled and should not be treated as raw Avito evidence.
