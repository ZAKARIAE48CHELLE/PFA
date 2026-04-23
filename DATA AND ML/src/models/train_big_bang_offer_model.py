import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder, StandardScaler


ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / "data" / "processed" / "unified_dataset.csv"
ARTIFACTS_DIR = ROOT / "artifacts" / "big_bang_offer_model"

HAS_OFFER_TEXT_FEATURES = 8000
OFFER_TYPE_TEXT_FEATURES = 6000
REGRESSION_TEXT_FEATURES = 6000


def clip_rating(series: pd.Series) -> pd.Series:
    return series.clip(lower=0, upper=5)


def squeeze_text_column(frame):
    return frame.squeeze()


def build_base_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    base = df.copy()

    base["title_clean"] = base["title_clean"].fillna("")
    base["seller"] = base["seller"].fillna("unknown")
    base["category"] = base["category"].fillna("unknown")
    base["source"] = base["source"].fillna("unknown")
    base["currency"] = base["currency"].fillna("unknown")
    base["location"] = base["location"].fillna("unknown")
    base["offre_type"] = base["offre_type"].fillna("")

    base["price_initial_mad"] = pd.to_numeric(base["price_initial_mad"], errors="coerce")
    base["rating"] = pd.to_numeric(base["rating"], errors="coerce")
    base["rating"] = clip_rating(base["rating"])

    base["log_price_initial_mad"] = np.log1p(base["price_initial_mad"].clip(lower=0))
    base["rating_missing"] = base["rating"].isna().astype(int)
    base["rating_filled"] = base["rating"].fillna(base.groupby("source")["rating"].transform("median"))
    base["rating_filled"] = base["rating_filled"].fillna(4.0)
    base["rating_gap_to_5"] = (5.0 - base["rating_filled"]).clip(lower=0)
    base["source_category"] = base["source"].astype(str) + " :: " + base["category"].astype(str)
    base["seller_source"] = base["seller"].astype(str) + " :: " + base["source"].astype(str)
    base["has_offer"] = base["discount_pct"].notna().astype(int)

    return base


def build_preprocessor(*, max_text_features: int, include_source: bool = True) -> ColumnTransformer:
    numeric_features = [
        "price_initial_mad",
        "log_price_initial_mad",
        "rating_filled",
        "rating_gap_to_5",
        "rating_missing",
    ]
    categorical_features = [
        "category",
        "currency",
        "location",
        "source_category",
        "seller_source",
    ]
    if include_source:
        categorical_features = ["source"] + categorical_features

    text_feature = "title_clean"

    numeric_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler(with_mean=False)),
        ]
    )

    categorical_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]
    )

    text_pipeline = Pipeline(
        steps=[
            ("selector", FunctionTransformer(squeeze_text_column, validate=False)),
            (
                "tfidf",
                TfidfVectorizer(
                    max_features=max_text_features,
                    ngram_range=(1, 2),
                    min_df=2,
                    strip_accents="unicode",
                ),
            ),
        ]
    )

    return ColumnTransformer(
        transformers=[
            ("num", numeric_pipeline, numeric_features),
            ("cat", categorical_pipeline, categorical_features),
            ("txt", text_pipeline, [text_feature]),
        ]
    )


def build_has_offer_model() -> Pipeline:
    return Pipeline(
        steps=[
            ("preprocess", build_preprocessor(max_text_features=HAS_OFFER_TEXT_FEATURES, include_source=True)),
            (
                "model",
                LogisticRegression(
                    max_iter=4000,
                    class_weight="balanced",
                    solver="saga",
                    n_jobs=1,
                    C=2.0,
                ),
            ),
        ]
    )


def build_offer_type_model() -> Pipeline:
    return Pipeline(
        steps=[
            ("preprocess", build_preprocessor(max_text_features=OFFER_TYPE_TEXT_FEATURES, include_source=True)),
            (
                "model",
                LogisticRegression(
                    max_iter=4000,
                    solver="saga",
                    n_jobs=1,
                    C=4.0,
                ),
            ),
        ]
    )


def build_source_regressor() -> Pipeline:
    return Pipeline(
        steps=[
            ("preprocess", build_preprocessor(max_text_features=REGRESSION_TEXT_FEATURES, include_source=False)),
            ("model", Ridge(alpha=1.0)),
        ]
    )


def safe_jsonable(report: dict) -> dict:
    out = {}
    for key, value in report.items():
        if isinstance(value, dict):
            out[key] = safe_jsonable(value)
        elif isinstance(value, (np.floating, np.integer)):
            out[key] = float(value)
        else:
            out[key] = value
    return out


def build_balanced_offer_type_trainset(X_train: pd.DataFrame, y_train: pd.Series) -> tuple[pd.DataFrame, pd.Series]:
    train = X_train.copy()
    train["target"] = y_train.values

    majority = train[train["target"] == "pourcentage"]
    minority = train[train["target"] == "forfaite"]

    if minority.empty or majority.empty:
        return X_train, y_train

    minority_upsampled = minority.sample(len(majority), replace=True, random_state=42)
    balanced = pd.concat([majority, minority_upsampled], ignore_index=True).sample(frac=1, random_state=42)
    y_balanced = balanced["target"].copy()
    X_balanced = balanced.drop(columns=["target"])
    return X_balanced, y_balanced


def train_source_regressors(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_test: pd.DataFrame,
    feature_columns_without_source: list[str],
) -> tuple[dict, np.ndarray]:
    regressors = {}
    predictions = pd.Series(index=X_test.index, dtype=float)

    for source_name in sorted(X_train["source"].unique()):
        train_mask = X_train["source"] == source_name
        test_mask = X_test["source"] == source_name
        regressor = build_source_regressor()
        regressor.fit(X_train.loc[train_mask, feature_columns_without_source], y_train.loc[train_mask])
        regressors[source_name] = regressor

        if test_mask.any():
            predictions.loc[X_test.loc[test_mask].index] = np.clip(
                regressor.predict(X_test.loc[test_mask, feature_columns_without_source]),
                0,
                99,
            )

    return regressors, predictions.to_numpy()


def predict_discount_from_source_models(
    regressors: dict,
    X_frame: pd.DataFrame,
    feature_columns_without_source: list[str],
) -> np.ndarray:
    preds = pd.Series(index=X_frame.index, dtype=float)
    for source_name, regressor in regressors.items():
        mask = X_frame["source"] == source_name
        if mask.any():
            preds.loc[X_frame.loc[mask].index] = np.clip(
                regressor.predict(X_frame.loc[mask, feature_columns_without_source]),
                0,
                99,
            )
    return preds.to_numpy()


def main() -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(DATA_PATH)
    df = build_base_dataframe(df)

    feature_columns = [
        "title_clean",
        "seller",
        "category",
        "source",
        "currency",
        "location",
        "price_initial_mad",
        "log_price_initial_mad",
        "rating_filled",
        "rating_gap_to_5",
        "rating_missing",
        "source_category",
        "seller_source",
    ]
    reg_feature_columns = [c for c in feature_columns if c != "source"]

    X = df[feature_columns]
    y_has_offer = df["has_offer"]

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y_has_offer,
        test_size=0.2,
        random_state=42,
        stratify=y_has_offer,
    )

    has_offer_model = build_has_offer_model()
    has_offer_model.fit(X_train, y_train)
    has_offer_pred = has_offer_model.predict(X_test)
    has_offer_proba = has_offer_model.predict_proba(X_test)[:, 1]

    offer_rows = df[df["has_offer"] == 1].copy()
    offer_rows = offer_rows[offer_rows["offre_type"].isin(["pourcentage", "forfaite"])].copy()
    X_offer = offer_rows[feature_columns]
    y_offer_type = offer_rows["offre_type"]

    X_offer_train, X_offer_test, y_offer_train, y_offer_test = train_test_split(
        X_offer,
        y_offer_type,
        test_size=0.2,
        random_state=42,
        stratify=y_offer_type,
    )
    X_offer_balanced, y_offer_balanced = build_balanced_offer_type_trainset(X_offer_train, y_offer_train)

    offer_type_model = build_offer_type_model()
    offer_type_model.fit(X_offer_balanced, y_offer_balanced)
    offer_type_pred = offer_type_model.predict(X_offer_test)

    reg_rows = df[df["discount_pct"].notna()].copy()
    X_reg = reg_rows[feature_columns]
    y_reg = reg_rows["discount_pct"].astype(float)

    X_reg_train, X_reg_test, y_reg_train, y_reg_test = train_test_split(
        X_reg,
        y_reg,
        test_size=0.2,
        random_state=42,
    )

    source_regressors, reg_pred = train_source_regressors(
        X_reg_train,
        y_reg_train,
        X_reg_test,
        reg_feature_columns,
    )

    sample_bundle = X_test.copy()
    sample_bundle["pred_has_offer_proba"] = has_offer_proba
    sample_bundle["pred_has_offer"] = has_offer_pred

    positive_mask = sample_bundle["pred_has_offer"] == 1
    if positive_mask.any():
        sample_bundle.loc[positive_mask, "pred_offer_type"] = offer_type_model.predict(
            sample_bundle.loc[positive_mask, feature_columns]
        )
        sample_bundle.loc[positive_mask, "pred_discount_pct"] = predict_discount_from_source_models(
            source_regressors,
            sample_bundle.loc[positive_mask, feature_columns],
            reg_feature_columns,
        )

    per_source_mae = {}
    for source_name in sorted(X_reg_test["source"].unique()):
        source_mask = X_reg_test["source"] == source_name
        per_source_mae[source_name] = float(
            mean_absolute_error(y_reg_test.loc[source_mask], reg_pred[source_mask.to_numpy()])
        )

    metrics = {
        "dataset": {
            "rows": int(len(df)),
            "offer_rows": int(df["has_offer"].sum()),
            "no_offer_rows": int((df["has_offer"] == 0).sum()),
            "sources": df["source"].value_counts().to_dict(),
        },
        "has_offer_classifier": {
            "accuracy": float(accuracy_score(y_test, has_offer_pred)),
            "classification_report": safe_jsonable(
                classification_report(y_test, has_offer_pred, output_dict=True, zero_division=0)
            ),
        },
        "offer_type_classifier": {
            "accuracy": float(accuracy_score(y_offer_test, offer_type_pred)),
            "classification_report": safe_jsonable(
                classification_report(y_offer_test, offer_type_pred, output_dict=True, zero_division=0)
            ),
            "train_strategy": "minority oversampling for 'forfaite'",
        },
        "discount_regressor": {
            "strategy": "source-specific ridge regressors",
            "mae": float(mean_absolute_error(y_reg_test, reg_pred)),
            "rmse": float(np.sqrt(mean_squared_error(y_reg_test, reg_pred))),
            "r2": float(r2_score(y_reg_test, reg_pred)),
            "mae_by_source": per_source_mae,
        },
    }

    (ARTIFACTS_DIR / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    sample_bundle.head(250).to_csv(ARTIFACTS_DIR / "sample_predictions.csv", index=False)

    joblib.dump(has_offer_model, ARTIFACTS_DIR / "has_offer_model.joblib")
    joblib.dump(offer_type_model, ARTIFACTS_DIR / "offer_type_model.joblib")
    joblib.dump(
        {
            "models": source_regressors,
            "feature_columns_without_source": reg_feature_columns,
        },
        ARTIFACTS_DIR / "discount_regressor.joblib",
    )

    print("Saved artifacts to:", ARTIFACTS_DIR)
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
