"""
big_bang_offer_model_v2.py
==========================
Upgraded version of the big_bang discount-prediction pipeline.

Upgrades vs v1 (notebook):
  1.  XGBoost + LightGBM added alongside Ridge and ExtraTrees
  2.  ExtraTrees now uses n_jobs=-1  (parallel, much faster)
  3.  Price outlier clipping at the 99th percentile
  4.  Temporal features: day_of_week, month, days_since_earliest
  5.  5-fold cross-validation MAE for every model
  6.  requirements.txt updated with new deps

Run from the repo root:
    python src/models/big_bang_offer_model_v2.py
"""

from __future__ import annotations

import json
from pathlib import Path

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

import xgboost as xgb
import lightgbm as lgbm

# ─────────────────────────────────────────────
#  Paths
# ─────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / "data" / "processed" / "unified_dataset.csv"
ARTIFACTS_DIR = ROOT / "artifacts" / "big_bang_discount_model"
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

print(f"ROOT        = {ROOT}")
print(f"DATA_PATH   = {DATA_PATH}")
print(f"ARTIFACTS   = {ARTIFACTS_DIR}")

sns.set_theme(style="whitegrid")
plt.rcParams["figure.figsize"] = (8, 5)

# ─────────────────────────────────────────────
#  1. Load data
# ─────────────────────────────────────────────
raw_df = pd.read_csv(DATA_PATH)
print(f"\nDataset shape: {raw_df.shape}")

# Keep only rows that have a measurable discount
reg_df = raw_df[raw_df["discount_pct"].notna()].copy()
print(f"Rows with discount_pct: {len(reg_df)}")
print("Source distribution:")
print(reg_df["source"].value_counts().to_string())

# ─────────────────────────────────────────────
#  2. Feature Engineering
# ─────────────────────────────────────────────

def squeeze_text_column(frame: pd.DataFrame) -> pd.Series:
    squeezed = frame.squeeze()
    if isinstance(squeezed, str):
        return pd.Series([squeezed])
    return squeezed


def build_base_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Mirrors the v1 feature engineering, plus:
      - Upgrade 3: outlier clipping on price_initial_mad (99th percentile)
      - Upgrade 4: temporal features from the 'date' column
    """
    base = df.copy()

    # ── fill categoricals ──────────────────────────────────
    base["title_clean"] = base["title_clean"].fillna("")
    base["seller"] = base["seller"].fillna("unknown")
    base["category"] = base["category"].fillna("unknown")
    base["source"] = base["source"].fillna("unknown")
    base["currency"] = base["currency"].fillna("unknown")
    base["location"] = base["location"].fillna("unknown")

    # ── numeric features ───────────────────────────────────
    base["price_initial_mad"] = pd.to_numeric(base["price_initial_mad"], errors="coerce")
    base["rating"] = pd.to_numeric(base["rating"], errors="coerce").clip(lower=0, upper=5)

    # Upgrade 3 ▶ clip extreme price outliers at the 99th percentile
    price_cap = base["price_initial_mad"].quantile(0.99)
    clipped_count = (base["price_initial_mad"] > price_cap).sum()
    if clipped_count:
        print(f"  [clip] Capping {clipped_count} rows at price_initial_mad ≤ {price_cap:,.0f} MAD")
    base["price_initial_mad"] = base["price_initial_mad"].clip(upper=price_cap)

    base["log_price_initial_mad"] = np.log1p(base["price_initial_mad"].clip(lower=0))
    base["rating_missing"] = base["rating"].isna().astype(int)
    base["rating_filled"] = (
        base["rating"]
        .fillna(base.groupby("source")["rating"].transform("median"))
        .fillna(4.0)
    )
    base["rating_gap_to_5"] = (5.0 - base["rating_filled"]).clip(lower=0)

    # ── interaction categoricals ──────────────────────────
    base["source_category"] = base["source"].astype(str) + " :: " + base["category"].astype(str)
    base["seller_source"] = base["seller"].astype(str) + " :: " + base["source"].astype(str)

    # Upgrade 4 ▶ temporal features from the 'date' column
    if "date" in base.columns:
        dates = pd.to_datetime(base["date"], errors="coerce")
        base["day_of_week"] = dates.dt.dayofweek.fillna(-1).astype(int)   # 0=Mon … 6=Sun
        base["month"] = dates.dt.month.fillna(-1).astype(int)              # 1–12
        min_date = dates.min()
        base["days_since_earliest"] = (dates - min_date).dt.days.fillna(0).astype(int)
    else:
        base["day_of_week"] = 0
        base["month"] = 0
        base["days_since_earliest"] = 0

    return base


def build_sparse_preprocessor(max_features: int = 10_000, include_source: bool = True) -> ColumnTransformer:
    numeric_features = [
        "price_initial_mad",
        "log_price_initial_mad",
        "rating_filled",
        "rating_gap_to_5",
        "rating_missing",
        "day_of_week",       # ← Upgrade 4
        "month",             # ← Upgrade 4
        "days_since_earliest",  # ← Upgrade 4
    ]
    categorical_features = ["category", "currency", "location", "source_category", "seller_source"]
    if include_source:
        categorical_features = ["source"] + categorical_features

    return ColumnTransformer([
        ("num", Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler(with_mean=False)),
        ]), numeric_features),
        ("cat", Pipeline([
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]), categorical_features),
        ("txt", Pipeline([
            ("selector", FunctionTransformer(squeeze_text_column, validate=False)),
            ("tfidf", TfidfVectorizer(
                max_features=max_features,
                ngram_range=(1, 2),
                min_df=2,
                strip_accents="unicode",
            )),
        ]), ["title_clean"]),
    ])


def build_dense_preprocessor(max_features: int = 10_000, include_source: bool = True) -> Pipeline:
    return Pipeline([
        ("preprocess", build_sparse_preprocessor(max_features=max_features, include_source=include_source)),
        ("svd", TruncatedSVD(n_components=256, random_state=42)),
    ])


# ─────────────────────────────────────────────
#  3. Prepare X / y
# ─────────────────────────────────────────────
print("\n[feature engineering]")
base_reg_df = build_base_dataframe(reg_df)

feature_columns = [
    "title_clean", "seller", "category", "source", "currency", "location",
    "price_initial_mad", "log_price_initial_mad", "rating_filled",
    "rating_gap_to_5", "rating_missing", "source_category", "seller_source",
    "day_of_week", "month", "days_since_earliest",           # ← Upgrade 4
]

X = base_reg_df[feature_columns]
y = base_reg_df["discount_pct"].astype(float)

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
print(f"Train size: {X_train.shape[0]}  |  Test size: {X_test.shape[0]}")

# ─────────────────────────────────────────────
#  4. Model definitions
# ─────────────────────────────────────────────

def make_ridge() -> Pipeline:
    return Pipeline([
        ("preprocess", build_sparse_preprocessor(max_features=8_000)),
        ("model", Ridge(alpha=1.0)),
    ])


def make_extratrees() -> Pipeline:
    return Pipeline([
        ("preprocess", build_dense_preprocessor(max_features=10_000)),
        ("model", ExtraTreesRegressor(
            n_estimators=400,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1,          # ← Upgrade 2 (was n_jobs=1)
        )),
    ])


def make_xgboost() -> Pipeline:
    """Upgrade 1 — XGBoost"""
    return Pipeline([
        ("preprocess", build_dense_preprocessor(max_features=10_000)),
        ("model", xgb.XGBRegressor(
            n_estimators=500,
            learning_rate=0.05,
            max_depth=6,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            n_jobs=-1,
            verbosity=0,
            eval_metric="mae",
        )),
    ])


def make_lightgbm() -> Pipeline:
    """Upgrade 1 — LightGBM"""
    return Pipeline([
        ("preprocess", build_dense_preprocessor(max_features=10_000)),
        ("model", lgbm.LGBMRegressor(
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


# Map of all models to evaluate
MODEL_FACTORIES = {
    "Ridge":          make_ridge,
    "ExtraTrees":     make_extratrees,
    "XGBoost":        make_xgboost,
    "LightGBM":       make_lightgbm,
}

# ─────────────────────────────────────────────
#  5. Train + evaluate every model
# ─────────────────────────────────────────────

def evaluate(pipeline: Pipeline, X_tr, y_tr, X_te, y_te) -> dict:
    # hold-out metrics
    pipeline.fit(X_tr, y_tr)
    pred = np.clip(pipeline.predict(X_te), 0, 99)
    mae  = mean_absolute_error(y_te, pred)
    rmse = float(np.sqrt(mean_squared_error(y_te, pred)))
    r2   = r2_score(y_te, pred)

    # Upgrade 5 — 5-fold CV MAE (negative MAE convention → negate back)
    cv_neg_mae = cross_val_score(
        pipeline, X_tr, y_tr,
        cv=5, scoring="neg_mean_absolute_error", n_jobs=-1,
    )
    cv_mae = float(-cv_neg_mae.mean())

    return {"MAE": mae, "RMSE": rmse, "R2": r2, "CV_MAE_5fold": cv_mae, "pipeline": pipeline, "pred": pred}


results: dict[str, dict] = {}

for name, factory in MODEL_FACTORIES.items():
    print(f"\n[training] {name} …")
    res = evaluate(factory(), X_train, y_train, X_test, y_test)
    results[name] = res
    print(f"  Hold-out  MAE={res['MAE']:.3f}  RMSE={res['RMSE']:.3f}  R²={res['R2']:.4f}")
    print(f"  5-fold CV MAE={res['CV_MAE_5fold']:.3f}")

# ─────────────────────────────────────────────
#  6. Comparison table
# ─────────────────────────────────────────────
print("\n" + "=" * 60)
print("MODEL COMPARISON (hold-out test set)")
print("=" * 60)
rows = []
for name, res in results.items():
    rows.append({
        "Model":        name,
        "MAE":          round(res["MAE"], 3),
        "RMSE":         round(res["RMSE"], 3),
        "R²":           round(res["R2"], 4),
        "CV-MAE (5k)":  round(res["CV_MAE_5fold"], 3),
    })
comparison_df = pd.DataFrame(rows).sort_values("MAE")
print(comparison_df.to_string(index=False))

# ─────────────────────────────────────────────
#  7. Per-source MAE for the best model
# ─────────────────────────────────────────────
best_name = comparison_df.iloc[0]["Model"]
best_res  = results[best_name]
best_pred = best_res["pred"]
best_pipe = best_res["pipeline"]

print(f"\nBest model: {best_name}")

eval_df = X_test.copy()
eval_df["y_true"] = y_test.values
eval_df["y_pred"] = best_pred
eval_df["abs_error"] = (eval_df["y_true"] - eval_df["y_pred"]).abs()

source_mae = eval_df.groupby("source")["abs_error"].mean().sort_values()
print("\nMAE by source:")
print(source_mae.to_string())

# ─────────────────────────────────────────────
#  8. Plots
# ─────────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(14, 4))

# Distribution of target
base_reg_df["discount_pct"].plot(kind="hist", bins=30, ax=axes[0], color="#8da0cb", edgecolor="black")
axes[0].set_title("Distribution de discount_pct")
axes[0].set_xlabel("discount_pct")

# Model comparison bar chart
comp_melt = comparison_df.melt(id_vars="Model", value_vars=["MAE", "RMSE", "R²"],
                                var_name="Metric", value_name="Value")
sns.barplot(data=comp_melt, x="Metric", y="Value", hue="Model", ax=axes[1])
axes[1].set_title("Comparaison des modèles (hold-out)")
plt.tight_layout()
plot_path = ARTIFACTS_DIR / "model_comparison_v2.png"
plt.savefig(plot_path, dpi=120)
print(f"\nPlot saved → {plot_path}")

# ─────────────────────────────────────────────
#  9. Save best model + metrics JSON
# ─────────────────────────────────────────────
metrics_out = {
    "version": "v2",
    "upgrades": [
        "XGBoost + LightGBM added",
        "ExtraTrees n_jobs=-1",
        "Price outlier clipping at 99th percentile",
        "Temporal features: day_of_week, month, days_since_earliest",
        "5-fold cross-validation MAE",
        "requirements.txt updated",
    ],
    "dataset": {
        "rows_total_regression": int(len(base_reg_df)),
        "sources": base_reg_df["source"].value_counts().to_dict(),
    },
    "models": {
        name: {
            "mae":           float(res["MAE"]),
            "rmse":          float(res["RMSE"]),
            "r2":            float(res["R2"]),
            "cv_mae_5fold":  float(res["CV_MAE_5fold"]),
        }
        for name, res in results.items()
    },
    "best_model": {
        "name":         best_name,
        "mae":          float(best_res["MAE"]),
        "rmse":         float(best_res["RMSE"]),
        "r2":           float(best_res["R2"]),
        "cv_mae_5fold": float(best_res["CV_MAE_5fold"]),
        "mae_by_source": {k: float(v) for k, v in source_mae.to_dict().items()},
    },
}

metrics_path = ARTIFACTS_DIR / "discount_model_metrics_v2.json"
metrics_path.write_text(json.dumps(metrics_out, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"Metrics JSON → {metrics_path}")

model_path = ARTIFACTS_DIR / "discount_pct_model_v2.joblib"
joblib.dump(best_pipe, model_path)
print(f"Model saved → {model_path}")

# ─────────────────────────────────────────────
# 10. Convenience: predict a single row
# ─────────────────────────────────────────────
def predict_single_row(row_df: pd.DataFrame, model=None) -> float:
    """
    Predict discount_pct for a single row (or small DataFrame).
    Duplicates the row internally if needed (prevents TF-IDF edge case).
    """
    if model is None:
        model = best_pipe
    row_df = build_base_dataframe(row_df.copy())
    row_df = row_df[feature_columns]
    if len(row_df) == 1:
        row_df = pd.concat([row_df, row_df], ignore_index=True)
    pred = np.clip(model.predict(row_df), 0, 99)
    return float(pred[0])


# Quick smoke-test on the full held-out set (50 rows)
demo = X_test.head(50).copy()
demo["discount_pct_pred"] = np.clip(best_pipe.predict(demo[feature_columns]), 0, 99)
print("\n── Demo predictions (first 5 rows) ──")
print(demo[["source", "category", "price_initial_mad", "rating_filled", "discount_pct_pred"]].head())

print("\n✓ big_bang_offer_model_v2 complete.")
