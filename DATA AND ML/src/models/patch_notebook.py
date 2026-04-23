"""
patch_notebook.py
=================
Injects the 6 model upgrades directly into big_bang_offer_model.ipynb.
Run once:  python patch_notebook.py

What it does:
  1. Reads the existing notebook with nbformat
  2. Patches the imports cell  → adds xgboost, lightgbm, cross_val_score
  3. Patches build_base_dataframe → price clipping + temporal features
  4. Patches feature_columns list → adds 3 new columns
  5. Patches ExtraTrees cell    → n_jobs=1 → n_jobs=-1
  6. Inserts a new "XGBoost + LightGBM" markdown + code cell
  7. Inserts a new "Cross-validation" markdown + code cell
  8. Patches the comparison cell → includes new models
  9. Patches the metrics-save cell → stores all model results
  10. Writes the patched notebook back  (overwrites the original)
"""

import copy
import json
import re
from pathlib import Path

import nbformat

NB_PATH = Path(__file__).parent / "big_bang_offer_model.ipynb"

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def source_str(cell) -> str:
    return "".join(cell["source"])


def find_cell(nb, snippet: str) -> int:
    """Return index of the first cell whose source contains *snippet*."""
    for i, cell in enumerate(nb.cells):
        if snippet in source_str(cell):
            return i
    raise ValueError(f"Cell containing {snippet!r} not found")


def code_cell(src: str) -> nbformat.NotebookNode:
    return nbformat.v4.new_code_cell(src)


def md_cell(src: str) -> nbformat.NotebookNode:
    return nbformat.v4.new_markdown_cell(src)


# ──────────────────────────────────────────────────────────────────────────────
# Load
# ──────────────────────────────────────────────────────────────────────────────
nb = nbformat.read(NB_PATH, as_version=4)
print(f"Loaded notebook: {NB_PATH}  ({len(nb.cells)} cells)")

# ──────────────────────────────────────────────────────────────────────────────
# 1. Patch imports cell
# ──────────────────────────────────────────────────────────────────────────────
idx_imports = find_cell(nb, "from sklearn.linear_model import Ridge")
cell = nb.cells[idx_imports]

new_imports_src = """\
from pathlib import Path
import json

import joblib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.compose import ColumnTransformer
from sklearn.decomposition import TruncatedSVD
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder, StandardScaler

# ── Upgrade 1: boosting models ─────────────────────────────────────────
import xgboost as xgb
import lightgbm as lgbm

sns.set_theme(style='whitegrid')
plt.rcParams['figure.figsize'] = (8, 5)

ROOT = Path.cwd()
if not (ROOT / 'data').exists():
    ROOT = Path(r'd:/EMSI/S8/PFA/PFA')

DATA_PATH = ROOT / 'data' / 'processed' / 'unified_dataset.csv'
ARTIFACTS_DIR = ROOT / 'artifacts' / 'big_bang_discount_model'
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

print('ROOT =', ROOT)
print('DATA_PATH =', DATA_PATH)
"""
cell["source"] = new_imports_src
cell.pop("outputs", None)
cell["outputs"] = []
cell["execution_count"] = None
print(f"  [1] Patched imports cell (idx={idx_imports})")

# ──────────────────────────────────────────────────────────────────────────────
# 2. Patch build_base_dataframe cell
# ──────────────────────────────────────────────────────────────────────────────
idx_fe = find_cell(nb, "def build_base_dataframe")
cell = nb.cells[idx_fe]

new_fe_src = """\
def squeeze_text_column(frame):
    squeezed = frame.squeeze()
    if isinstance(squeezed, str):
        return pd.Series([squeezed])
    return squeezed


def build_base_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    base = df.copy()
    base['title_clean'] = base['title_clean'].fillna('')
    base['seller']   = base['seller'].fillna('unknown')
    base['category'] = base['category'].fillna('unknown')
    base['source']   = base['source'].fillna('unknown')
    base['currency'] = base['currency'].fillna('unknown')
    base['location'] = base['location'].fillna('unknown')

    base['price_initial_mad'] = pd.to_numeric(base['price_initial_mad'], errors='coerce')
    base['rating'] = pd.to_numeric(base['rating'], errors='coerce').clip(lower=0, upper=5)

    # ── Upgrade 3: clip extreme price outliers at the 99th percentile ──────
    price_cap = base['price_initial_mad'].quantile(0.99)
    n_clipped = int((base['price_initial_mad'] > price_cap).sum())
    if n_clipped:
        print(f'  [clip] {n_clipped} rows capped at price_initial_mad ≤ {price_cap:,.0f} MAD')
    base['price_initial_mad'] = base['price_initial_mad'].clip(upper=price_cap)

    base['log_price_initial_mad'] = np.log1p(base['price_initial_mad'].clip(lower=0))
    base['rating_missing']  = base['rating'].isna().astype(int)
    base['rating_filled']   = (
        base['rating']
        .fillna(base.groupby('source')['rating'].transform('median'))
        .fillna(4.0)
    )
    base['rating_gap_to_5'] = (5.0 - base['rating_filled']).clip(lower=0)
    base['source_category'] = base['source'].astype(str) + ' :: ' + base['category'].astype(str)
    base['seller_source']   = base['seller'].astype(str)  + ' :: ' + base['source'].astype(str)

    # ── Upgrade 4: temporal features from the 'date' column ───────────────
    if 'date' in base.columns:
        dates = pd.to_datetime(base['date'], errors='coerce')
        base['day_of_week']        = dates.dt.dayofweek.fillna(-1).astype(int)
        base['month']              = dates.dt.month.fillna(-1).astype(int)
        base['days_since_earliest'] = (dates - dates.min()).dt.days.fillna(0).astype(int)
    else:
        base['day_of_week'] = 0
        base['month'] = 0
        base['days_since_earliest'] = 0

    return base


def build_sparse_preprocessor(max_features=10000, include_source=True):
    numeric_features = [
        'price_initial_mad', 'log_price_initial_mad',
        'rating_filled', 'rating_gap_to_5', 'rating_missing',
        'day_of_week', 'month', 'days_since_earliest',   # ← Upgrade 4
    ]
    categorical_features = ['category', 'currency', 'location', 'source_category', 'seller_source']
    if include_source:
        categorical_features = ['source'] + categorical_features

    return ColumnTransformer([
        ('num', Pipeline([
            ('imputer', SimpleImputer(strategy='median')),
            ('scaler',  StandardScaler(with_mean=False)),
        ]), numeric_features),
        ('cat', Pipeline([
            ('imputer', SimpleImputer(strategy='most_frequent')),
            ('onehot',  OneHotEncoder(handle_unknown='ignore')),
        ]), categorical_features),
        ('txt', Pipeline([
            ('selector', FunctionTransformer(squeeze_text_column, validate=False)),
            ('tfidf',    TfidfVectorizer(max_features=max_features, ngram_range=(1, 2),
                                         min_df=2, strip_accents='unicode')),
        ]), ['title_clean']),
    ])


def build_dense_preprocessor(max_features=10000, include_source=True):
    return Pipeline([
        ('preprocess', build_sparse_preprocessor(max_features=max_features,
                                                  include_source=include_source)),
        ('svd', TruncatedSVD(n_components=256, random_state=42)),
    ])


base_reg_df = build_base_dataframe(reg_df)
base_reg_df.head(2)
"""
cell["source"] = new_fe_src
cell["outputs"] = []
cell["execution_count"] = None
print(f"  [2] Patched feature-engineering cell (idx={idx_fe})")

# ──────────────────────────────────────────────────────────────────────────────
# 3. Patch feature_columns + train/test split cell
# ──────────────────────────────────────────────────────────────────────────────
idx_fc = find_cell(nb, "feature_columns = [")
cell = nb.cells[idx_fc]

new_fc_src = """\
feature_columns = [
    'title_clean', 'seller', 'category', 'source', 'currency', 'location',
    'price_initial_mad', 'log_price_initial_mad', 'rating_filled',
    'rating_gap_to_5', 'rating_missing', 'source_category', 'seller_source',
    'day_of_week', 'month', 'days_since_earliest',   # ← Upgrade 4
]

X = base_reg_df[feature_columns]
y = base_reg_df['discount_pct'].astype(float)

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42,
)

print(X_train.shape, X_test.shape)
"""
cell["source"] = new_fc_src
cell["outputs"] = []
cell["execution_count"] = None
print(f"  [3] Patched feature_columns cell (idx={idx_fc})")

# ──────────────────────────────────────────────────────────────────────────────
# 4. Patch Ridge cell (unchanged, but clear output so it re-runs cleanly)
# ──────────────────────────────────────────────────────────────────────────────
idx_ridge = find_cell(nb, "ridge_model = Pipeline")
nb.cells[idx_ridge]["outputs"] = []
nb.cells[idx_ridge]["execution_count"] = None
print(f"  [4] Cleared Ridge cell (idx={idx_ridge})")

# ──────────────────────────────────────────────────────────────────────────────
# 5. Patch ExtraTrees cell  →  n_jobs=-1
# ──────────────────────────────────────────────────────────────────────────────
idx_et = find_cell(nb, "ExtraTreesRegressor(")
cell = nb.cells[idx_et]
cell["source"] = source_str(cell).replace("n_jobs=1,", "n_jobs=-1,  # ← Upgrade 2")
cell["outputs"] = []
cell["execution_count"] = None
print(f"  [5] Patched ExtraTrees n_jobs (idx={idx_et})")

# ──────────────────────────────────────────────────────────────────────────────
# 6. Insert XGBoost + LightGBM cells  (after ExtraTrees cell)
# ──────────────────────────────────────────────────────────────────────────────
new_md_boost = """\
## Upgrade 1 — XGBoost et LightGBM

Ces deux modèles gradient-boosted sont souvent plus performants qu'ExtraTrees sur les données tabulaires.  
Ils utilisent eux aussi le préprocesseur dense (sparse → SVD 256 composantes).
"""

new_code_boost = """\
# ── XGBoost ────────────────────────────────────────────────────────────────
xgboost_model = Pipeline([
    ('preprocess', build_dense_preprocessor(max_features=10000, include_source=True)),
    ('model', xgb.XGBRegressor(
        n_estimators=500,
        learning_rate=0.05,
        max_depth=6,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        n_jobs=-1,
        verbosity=0,
        eval_metric='mae',
    )),
])

xgboost_model.fit(X_train, y_train)
xgboost_pred = np.clip(xgboost_model.predict(X_test), 0, 99)

xgboost_metrics = {
    'MAE':  mean_absolute_error(y_test, xgboost_pred),
    'RMSE': float(np.sqrt(mean_squared_error(y_test, xgboost_pred))),
    'R2':   r2_score(y_test, xgboost_pred),
}

print('XGBoost →', xgboost_metrics)

# ── LightGBM ────────────────────────────────────────────────────────────────
lightgbm_model = Pipeline([
    ('preprocess', build_dense_preprocessor(max_features=10000, include_source=True)),
    ('model', lgbm.LGBMRegressor(
        n_estimators=500,
        learning_rate=0.05,
        max_depth=7,
        num_leaves=63,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        n_jobs=-1,
        verbosity=-1,
    )),
])

lightgbm_model.fit(X_train, y_train)
lightgbm_pred = np.clip(lightgbm_model.predict(X_test), 0, 99)

lightgbm_metrics = {
    'MAE':  mean_absolute_error(y_test, lightgbm_pred),
    'RMSE': float(np.sqrt(mean_squared_error(y_test, lightgbm_pred))),
    'R2':   r2_score(y_test, lightgbm_pred),
}

print('LightGBM →', lightgbm_metrics)
"""

nb.cells.insert(idx_et + 1, md_cell(new_md_boost))
nb.cells.insert(idx_et + 2, code_cell(new_code_boost))
print(f"  [6] Inserted XGBoost + LightGBM cells after idx={idx_et}")

# ──────────────────────────────────────────────────────────────────────────────
# 7. Patch comparison cell  →  include 4 models + CV column
# ──────────────────────────────────────────────────────────────────────────────
# After our insertions, the comparison cell has shifted
idx_cmp = find_cell(nb, "'modele': 'Ridge'")
cell = nb.cells[idx_cmp]

# 7a. Insert cross-validation markdown + code just before the comparison cell
new_md_cv = """\
## Upgrade 5 — Validation croisée 5-fold

Au lieu d'un seul split 80/20, nous calculons la MAE en validation croisée 5 plis pour chaque modèle.  
Cela donne une estimation plus robuste de la performance réelle.
"""

new_code_cv = """\
# ── 5-fold CV MAE pour chaque modèle ─────────────────────────────────────

def cv_mae(pipeline, X, y, cv=5):
    scores = cross_val_score(pipeline, X, y,
                             cv=cv, scoring='neg_mean_absolute_error', n_jobs=-1)
    return float(-scores.mean())

print('Calcul des CV MAE (patient, chaque modèle fait 5 fits)...')
cv_results = {
    'Ridge':      cv_mae(ridge_model,     X_train, y_train),
    'ExtraTrees': cv_mae(extra_trees_model, X_train, y_train),
    'XGBoost':    cv_mae(xgboost_model,   X_train, y_train),
    'LightGBM':   cv_mae(lightgbm_model,  X_train, y_train),
}
print('CV MAE (5-fold):')
for name, v in cv_results.items():
    print(f'  {name:<12} {v:.3f}')
"""

nb.cells.insert(idx_cmp, md_cell(new_md_cv))
nb.cells.insert(idx_cmp + 1, code_cell(new_code_cv))
# idx_cmp has shifted by +2
idx_cmp += 2
print(f"  [7] Inserted CV cells before comparison (new idx_cmp={idx_cmp})")

# 7b. Replace the comparison cell itself
cell = nb.cells[idx_cmp]

new_cmp_src = """\
comparison = pd.DataFrame([
    {'modele': 'Ridge',       **ridge_metrics,      'CV_MAE_5fold': cv_results['Ridge']},
    {'modele': 'ExtraTrees',  **extra_trees_metrics, 'CV_MAE_5fold': cv_results['ExtraTrees']},
    {'modele': 'XGBoost',     **xgboost_metrics,    'CV_MAE_5fold': cv_results['XGBoost']},
    {'modele': 'LightGBM',    **lightgbm_metrics,   'CV_MAE_5fold': cv_results['LightGBM']},
])
comparison.sort_values('MAE')
"""
cell["source"] = new_cmp_src
cell["outputs"] = []
cell["execution_count"] = None
print(f"  [7b] Patched comparison DataFrame (idx={idx_cmp})")

# ──────────────────────────────────────────────────────────────────────────────
# 8. Patch "best model" selection cell  →  pick winner dynamically
# ──────────────────────────────────────────────────────────────────────────────
idx_best = find_cell(nb, "best_pred = extra_trees_pred")
cell = nb.cells[idx_best]

new_best_src = """\
# Pick the model with the lowest hold-out MAE
_all_models = {
    'Ridge':      (ridge_pred,      ridge_metrics,      ridge_model),
    'ExtraTrees': (extra_trees_pred, extra_trees_metrics, extra_trees_model),
    'XGBoost':    (xgboost_pred,    xgboost_metrics,    xgboost_model),
    'LightGBM':   (lightgbm_pred,   lightgbm_metrics,   lightgbm_model),
}

best_name = min(_all_models, key=lambda n: _all_models[n][1]['MAE'])
best_pred, best_metrics, best_model = _all_models[best_name]
print(f'Best model selected: {best_name}')
best_metrics
"""
cell["source"] = new_best_src
cell["outputs"] = []
cell["execution_count"] = None
print(f"  [8] Patched best-model selection (idx={idx_best})")

# ──────────────────────────────────────────────────────────────────────────────
# 9. Patch metrics-save cell  →  store all model results
# ──────────────────────────────────────────────────────────────────────────────
idx_save = find_cell(nb, "discount_model_metrics.json")
cell = nb.cells[idx_save]

new_save_src = """\
metrics = {
    'dataset': {
        'rows_total_regression': int(len(base_reg_df)),
        'sources': base_reg_df['source'].value_counts().to_dict(),
    },
    'models': {
        'Ridge':      {**{k.lower(): float(v) for k, v in ridge_metrics.items()},
                       'cv_mae_5fold': cv_results['Ridge']},
        'ExtraTrees': {**{k.lower(): float(v) for k, v in extra_trees_metrics.items()},
                       'cv_mae_5fold': cv_results['ExtraTrees']},
        'XGBoost':    {**{k.lower(): float(v) for k, v in xgboost_metrics.items()},
                       'cv_mae_5fold': cv_results['XGBoost']},
        'LightGBM':   {**{k.lower(): float(v) for k, v in lightgbm_metrics.items()},
                       'cv_mae_5fold': cv_results['LightGBM']},
    },
    'best_model': {
        'name':         best_name,
        'mae':          float(best_metrics['MAE']),
        'rmse':         float(best_metrics['RMSE']),
        'r2':           float(best_metrics['R2']),
        'cv_mae_5fold': float(cv_results[best_name]),
        'mae_by_source': {k: float(v) for k, v in source_mae.to_dict().items()},
    },
}

(ARTIFACTS_DIR / 'discount_model_metrics.json').write_text(
    json.dumps(metrics, indent=2, ensure_ascii=False), encoding='utf-8'
)
joblib.dump(best_model, ARTIFACTS_DIR / 'discount_pct_model.joblib')
metrics
"""
cell["source"] = new_save_src
cell["outputs"] = []
cell["execution_count"] = None
print(f"  [9] Patched metrics-save cell (idx={idx_save})")

# ──────────────────────────────────────────────────────────────────────────────
# Write back
# ──────────────────────────────────────────────────────────────────────────────
nbformat.write(nb, NB_PATH)
print(f"\n✓ Notebook written back to {NB_PATH}  ({len(nb.cells)} cells total)")
print("  Run it normally in Jupyter or with:")
print("  jupyter nbconvert --to notebook --execute src/models/big_bang_offer_model.ipynb")
