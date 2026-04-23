# AuraMarket — E-Commerce Analytics Project

A professional, modular system for scraping and analyzing e-commerce data from major platforms in Morocco (Amazon, CDiscount, Jumia, Avito).

## 📁 Project Structure

```text
/
├── data/
│   ├── raw/                # Original JSON files from scrapers
│   └── processed/          # Cleaned and unified datasets
│
├── src/
│   ├── scrapers/           # Unified scraping logic
│   │   ├── amazon/
│   │   ├── cdiscount/
│   │   ├── jumia/
│   │   └── avito/
│   ├── processing/         # Data cleaning and unification scripts
│   └── dashboard/          # Frontend analytics dashboard
│
├── docs/
│   └── data_models/        # Data architecture and schema documentation
│
├── logs/                   # Centralized scraper logs
├── requirements.txt        # Unified project dependencies
└── README.md               # You are here
```

## 🚀 Getting Started

### 1. Installation
Clone the repository and install dependencies:
```bash
pip install -r requirements.txt
playwright install
```

### 2. Scraping
Run any of the scrapers located in `src/scrapers/`:
```bash
python src/scrapers/amazon/amazon_scraping.py
```

### 3. Data Processing
Clean and unify the raw data into a single dataset:
```bash
python src/processing/pretreatment.py
```

### 4. Dashboard
Open `src/dashboard/index.html` in your browser (use a local server like Live Server for best results) to view the analytics dashboard.

## ⚙️ Configuration
Path management is handled centrally within each script, pointing to the standard `data/raw` and `data/processed` folders.
