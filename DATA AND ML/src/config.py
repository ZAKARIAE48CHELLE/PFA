import os

# Project Root Directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Data Directories
DATA_DIR = os.path.join(BASE_DIR, 'data')
RAW_DATA_DIR = os.path.join(DATA_DIR, 'raw')
PROCESSED_DATA_DIR = os.path.join(DATA_DIR, 'processed')

# Log Directory
LOG_DIR = os.path.join(BASE_DIR, 'logs')

# File Paths (Unified Naming)
AMAZON_RAW = os.path.join(RAW_DATA_DIR, 'amazon_full.json')
AVITO_RAW = os.path.join(RAW_DATA_DIR, 'avito_full.json')
CDISCOUNT_RAW = os.path.join(RAW_DATA_DIR, 'cdiscount_full.json')
JUMIA_RAW = os.path.join(RAW_DATA_DIR, 'jumia_full.json')

UNIFIED_DATASET = os.path.join(PROCESSED_DATA_DIR, 'unified_ecommerce_dataset.json')

def get_log_path(filename):
    return os.path.join(LOG_DIR, filename)
