# 🏛️ Data Warehouse Models — E-Commerce Aggregator

Based on your scraping project (Amazon · Jumia · Avito), here are **3 DW model suggestions**, going from simple to advanced.

---

## Your Source Data at a Glance

| Field | Amazon | Jumia | Avito |
|---|---|---|---|
| `title` | ✅ | ✅ | ✅ |
| `price_initial` | ✅ | ✅ | ✅ |
| `price_offre` | ✅ | ✅ | ✅ |
| `seller` | ✅ | ✅ | ✅ |
| `location` | ✅ | ✅ | ✅ |
| `category` | ✅ | ✅ | ❌ (from link) |
| `rating` | ✅ | ✅ | ❌ |
| `offre` (deal detail) | ✅ | ✅ | ❌ |
| `date` | ✅ | ✅ | ✅ |
| `link` | ✅ | ✅ | ✅ |

---

## Option 1 — ⭐ Star Schema (Simple, Recommended for Beginners)

The classic DW pattern. One central **fact table** surrounded by flat **dimension tables**.

```mermaid
erDiagram
    FACT_LISTING {
        int     listing_id      PK
        int     dim_product_id  FK
        int     dim_source_id   FK
        int     dim_seller_id   FK
        int     dim_category_id FK
        int     dim_location_id FK
        int     dim_date_id     FK
        float   price_initial
        float   price_offre
        float   discount_pct
        float   rating
        string  offer_type
        string  offer_value
    }

    DIM_PRODUCT {
        int     product_id   PK
        string  title
        string  link
        string  currency
    }

    DIM_SOURCE {
        int     source_id  PK
        string  name
        string  country
        string  base_url
    }

    DIM_SELLER {
        int     seller_id  PK
        string  seller_name
    }

    DIM_CATEGORY {
        int     category_id   PK
        string  category_name
        string  category_icon
    }

    DIM_LOCATION {
        int     location_id PK
        string  city
        string  region
        string  country
    }

    DIM_DATE {
        int     date_id   PK
        date    full_date
        int     day
        int     month
        int     year
        string  day_of_week
        string  quarter
    }

    FACT_LISTING ||--|| DIM_PRODUCT   : "describes"
    FACT_LISTING ||--|| DIM_SOURCE    : "comes from"
    FACT_LISTING ||--|| DIM_SELLER    : "sold by"
    FACT_LISTING ||--|| DIM_CATEGORY  : "belongs to"
    FACT_LISTING ||--|| DIM_LOCATION  : "located in"
    FACT_LISTING ||--|| DIM_DATE      : "scraped on"
```

> [!TIP]
> **Best for:** Simple reporting (avg price per category, listings per source, best sellers). Easy to query with SQL. Great for tools like Power BI / Tableau.

---

## Option 2 — ❄️ Snowflake Schema (Normalized, Cleaner)

Extends the star by normalizing dimensions that have their own hierarchy. For example, `Location → Region → Country`.

```mermaid
erDiagram
    FACT_LISTING {
        int     listing_id      PK
        int     dim_product_id  FK
        int     dim_source_id   FK
        int     dim_seller_id   FK
        int     dim_category_id FK
        int     dim_location_id FK
        int     dim_date_id     FK
        float   price_initial
        float   price_offre
        float   discount_pct
        float   rating
    }

    DIM_PRODUCT {
        int     product_id   PK
        string  title
        string  link
        int     currency_id  FK
    }

    DIM_CURRENCY {
        int     currency_id  PK
        string  code
        string  symbol
        string  name
    }

    DIM_CATEGORY {
        int     category_id      PK
        string  category_name
        int     super_category_id FK
    }

    DIM_SUPER_CATEGORY {
        int     super_category_id PK
        string  name
        string  icon
    }

    DIM_LOCATION {
        int     location_id PK
        string  city
        int     region_id   FK
    }

    DIM_REGION {
        int     region_id  PK
        string  region_name
        int     country_id FK
    }

    DIM_COUNTRY {
        int     country_id   PK
        string  country_name
        string  iso_code
    }

    DIM_DATE {
        int     date_id   PK
        date    full_date
        int     day
        int     month
        int     year
        string  quarter
    }

    DIM_SOURCE {
        int     source_id  PK
        string  name
        string  base_url
    }

    DIM_SELLER {
        int     seller_id   PK
        string  seller_name
        int     source_id   FK
    }

    FACT_LISTING ||--|| DIM_PRODUCT       : "describes"
    FACT_LISTING ||--|| DIM_SOURCE        : "comes from"
    FACT_LISTING ||--|| DIM_SELLER        : "sold by"
    FACT_LISTING ||--|| DIM_CATEGORY      : "belongs to"
    FACT_LISTING ||--|| DIM_LOCATION      : "located in"
    FACT_LISTING ||--|| DIM_DATE          : "scraped on"
    DIM_PRODUCT   ||--|| DIM_CURRENCY     : "priced in"
    DIM_CATEGORY  ||--|| DIM_SUPER_CATEGORY : "grouped under"
    DIM_LOCATION  ||--|| DIM_REGION       : "in"
    DIM_REGION    ||--|| DIM_COUNTRY      : "in"
    DIM_SELLER    ||--|| DIM_SOURCE       : "on platform"
```

> [!TIP]
> **Best for:** Data integrity and storage efficiency. Reduces redundancy (e.g., "Casablanca" is stored once). Slightly slower queries because of more JOINs.

---

## Option 3 — 🌌 Galaxy / Constellation Schema (Advanced, Multi-Fact)

The most powerful model. Multiple fact tables share dimensions. Split by business process: **listings**, **price changes over time**, and **deal/offer events**.

```mermaid
erDiagram
    FACT_LISTING {
        int     listing_id      PK
        int     product_id      FK
        int     source_id       FK
        int     seller_id       FK
        int     category_id     FK
        int     location_id     FK
        int     date_id         FK
        float   price_initial
        float   price_offre
        float   rating
    }

    FACT_PRICE_SNAPSHOT {
        int     snapshot_id     PK
        int     product_id      FK
        int     source_id       FK
        int     date_id         FK
        float   price_recorded
        float   pct_change_vs_prev
    }

    FACT_OFFER_EVENT {
        int     offer_event_id  PK
        int     listing_id      FK
        int     date_id         FK
        string  offer_type
        string  offer_value
        float   estimated_savings
    }

    DIM_PRODUCT {
        int     product_id   PK
        string  title
        string  link
        string  currency
    }

    DIM_SOURCE {
        int     source_id  PK
        string  name
        string  country
    }

    DIM_SELLER {
        int     seller_id   PK
        string  seller_name
    }

    DIM_CATEGORY {
        int     category_id   PK
        string  name
        string  super_category
    }

    DIM_LOCATION {
        int     location_id PK
        string  city
        string  region
        string  country
    }

    DIM_DATE {
        int     date_id   PK
        date    full_date
        int     year
        int     month
        int     day
        string  quarter
    }

    FACT_LISTING        ||--|| DIM_PRODUCT  : "product"
    FACT_LISTING        ||--|| DIM_SOURCE   : "source"
    FACT_LISTING        ||--|| DIM_SELLER   : "seller"
    FACT_LISTING        ||--|| DIM_CATEGORY : "category"
    FACT_LISTING        ||--|| DIM_LOCATION : "location"
    FACT_LISTING        ||--|| DIM_DATE     : "date"
    FACT_PRICE_SNAPSHOT ||--|| DIM_PRODUCT  : "tracks"
    FACT_PRICE_SNAPSHOT ||--|| DIM_SOURCE   : "on"
    FACT_PRICE_SNAPSHOT ||--|| DIM_DATE     : "on date"
    FACT_OFFER_EVENT    ||--|| FACT_LISTING : "related to"
    FACT_OFFER_EVENT    ||--|| DIM_DATE     : "on date"
```

> [!TIP]
> **Best for:** Advanced analytics — tracking price evolution over time, deal frequency analysis, cross-platform price comparisons. Suitable for a full BI dashboard with a proper ETL pipeline (Pentaho/Talend).

---

## Comparison Table

| | ⭐ Star | ❄️ Snowflake | 🌌 Galaxy |
|---|---|---|---|
| **Complexity** | Low | Medium | High |
| **Query speed** | Fast | Medium | Fast (fact-to-fact) |
| **Storage efficiency** | Low | High | Medium |
| **Redundancy** | High | Low | Low |
| **Best BI tool fit** | Power BI, Tableau | SQL-heavy tools | Pentaho, Talend |
| **Good for your PFA?** | ✅ Yes | ✅ Yes | ⚠️ Advanced |

---

## ✅ My Recommendation

> [!IMPORTANT]
> For your PFA, go with **Option 2 (Snowflake Schema)**. It shows academic rigor (normalization, hierarchy levels), maps perfectly to your Pentaho ETL lab, and is straightforward to implement. Use the `DIM_DATE` table to enable time-series analysis per scraping run, and add a `FACT_PRICE_SNAPSHOT` from Option 3 if you want to showcase price tracking as a bonus feature.

### Suggested ETL Flow (Pentaho)
```
JSON Files (Avito, Jumia, Amazon)
        ↓
  [Extract] JSON Input Step
        ↓
  [Transform] Field normalizer + Type conversion + Lookup / Surrogate key
        ↓
  [Load] Dimension Tables first → then FACT_LISTING
        ↓
  DW (MySQL / PostgreSQL)
        ↓
  Reporting Layer (Power BI / Metabase)
```
