#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  AuraMarket — ML Price Predictor Trainer                                   ║
║  ────────────────────────────────────────                                   ║
║  Entraîne un modèle de prédiction de remise optimale (discount %)          ║
║  à partir des données réelles du projet (unified_dataset.csv) +            ║
║  augmentation synthétique.                                                 ║
║                                                                            ║
║  Remplace la formule logarithmique D = D_base + 5*log10(P+1) + 3*(5-R)    ║
║  de l'AgentOffre par un modèle ML appris sur les données du marché.        ║
╚══════════════════════════════════════════════════════════════════════════════╝

Usage:
    python train_price_predictor.py

Outputs:
    - price_predictor.pkl      : meilleur modèle (RF ou XGBoost)
    - category_encoder.pkl     : LabelEncoder catégorie
    - feature_importance.png   : graphe d'importance des features
    - metrics + comparaison dans le terminal
"""

import os
import sys
import warnings
from pathlib import Path

import joblib
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Fix encoding for Windows terminals
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

try:
    from xgboost import XGBRegressor
except ImportError:
    print("⚠  xgboost non installé — pip install xgboost")
    sys.exit(1)

warnings.filterwarnings("ignore", category=FutureWarning)
matplotlib.use("Agg")  # backend non-interactif pour serveur / CI

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────
ROOT_DIR = Path(__file__).resolve().parents[2]  # DATA AND ML/
DATA_PATH = ROOT_DIR / "data" / "processed" / "unified_dataset.csv"
ARTIFACTS_DIR = ROOT_DIR / "artifacts" / "price_predictor"

RANDOM_STATE = 42
np.random.seed(RANDOM_STATE)

# Mapping des catégories brutes du dataset vers les 5 domaines cibles
CATEGORY_MAP = {
    # smartphones
    "Smartphones": "smartphones",
    "Téléphones & Tablettes": "smartphones",
    "T\u00e9l\u00e9phones & Tablettes": "smartphones",
    "Tablettes": "smartphones",
    # laptops / informatique
    "Informatique": "laptops",
    "Gaming": "laptops",
    # accessoires
    "Audio": "accessoires",
    "Photo & Caméra": "accessoires",
    "Photo & Cam\u00e9ra": "accessoires",
    "Montres": "accessoires",
    "Jouets": "accessoires",
    "Mode Femme": "accessoires",
    "Mode Homme": "accessoires",
    "Beauté": "accessoires",
    "Beaut\u00e9": "accessoires",
    "Sport": "accessoires",
    # tv
    "TV & Vidéo": "tv",
    "TV & Vid\u00e9o": "tv",
    "Électronique": "tv",
    "\u00c9lectronique": "tv",
    # electromenager
    "Électroménager": "electromenager",
    "\u00c9lectrom\u00e9nager": "electromenager",
    "Maison": "electromenager",
}

# Paramètres par catégorie pour la génération synthétique
SYNTH_PARAMS = {
    "smartphones":    {"prix_min": 400,  "prix_max": 1500, "note_min": 3.5, "note_max": 5.0, "disc_min": 8,  "disc_max": 25},
    "laptops":        {"prix_min": 600,  "prix_max": 2500, "note_min": 3.0, "note_max": 5.0, "disc_min": 10, "disc_max": 30},
    "accessoires":    {"prix_min": 5,    "prix_max": 100,  "note_min": 2.5, "note_max": 5.0, "disc_min": 15, "disc_max": 45},
    "tv":             {"prix_min": 200,  "prix_max": 2000, "note_min": 3.0, "note_max": 4.8, "disc_min": 10, "disc_max": 28},
    "electromenager": {"prix_min": 150,  "prix_max": 1500, "note_min": 3.2, "note_max": 4.9, "disc_min": 12, "disc_max": 35},
}

FEATURE_COLS = [
    "prix_base",
    "prix_min",
    "note_vendeur",
    "categorie_encoded",
    "nb_similar_products",
    "avg_similar_price",
    "std_similar_price",
    "market_ratio",
    "note_minus_avg",
]
TARGET_COL = "discount_percent"


# ═════════════════════════════════════════════════════════════════════════════
#  1.  CHARGEMENT ET TRAITEMENT DES DONNÉES RÉELLES
# ═════════════════════════════════════════════════════════════════════════════
def load_real_data() -> pd.DataFrame:
    """Charge unified_dataset.csv et le transforme dans le schéma ML attendu."""
    if not DATA_PATH.exists():
        print(f"⚠  Fichier introuvable : {DATA_PATH}")
        print("   → Passage en mode 100% synthétique.")
        return pd.DataFrame()

    print(f"📂  Chargement des données réelles : {DATA_PATH}")
    raw = pd.read_csv(DATA_PATH, low_memory=False)
    print(f"   Lignes brutes : {len(raw):,}")

    # ── Nettoyage de base ──
    raw["price_initial_mad"] = pd.to_numeric(raw["price_initial_mad"], errors="coerce")
    raw["price_offre_mad"]   = pd.to_numeric(raw["price_offre_mad"], errors="coerce")
    raw["discount_pct"]      = pd.to_numeric(raw["discount_pct"], errors="coerce")
    raw["rating"]            = pd.to_numeric(raw["rating"], errors="coerce")

    # Garder seulement les lignes avec prix et discount valides
    mask = (
        raw["price_initial_mad"].notna()
        & (raw["price_initial_mad"] > 0)
        & raw["discount_pct"].notna()
        & (raw["discount_pct"] > 0)
        & (raw["discount_pct"] <= 80)
    )
    df = raw.loc[mask].copy()
    print(f"   Lignes avec prix+discount valides : {len(df):,}")

    # ── Mapping catégorie ──
    df["categorie"] = df["category"].map(CATEGORY_MAP).fillna("accessoires")

    # ── Colonnes ML ──
    df["prix_base"]     = df["price_initial_mad"]
    df["note_vendeur"]  = df["rating"].fillna(3.5).clip(0, 5)
    df["discount_percent"] = df["discount_pct"].clip(5, 50)

    # prix_min = prix_offre si dispo, sinon prix_base * (1 - discount/100 * 1.1)
    df["prix_min"] = df["price_offre_mad"]
    no_offre = df["prix_min"].isna()
    df.loc[no_offre, "prix_min"] = (
        df.loc[no_offre, "prix_base"] * (1 - df.loc[no_offre, "discount_percent"] / 100 * 1.1)
    ).clip(lower=1)

    return df[["prix_base", "prix_min", "note_vendeur", "categorie", "discount_percent"]]


# ═════════════════════════════════════════════════════════════════════════════
#  2.  GÉNÉRATION DU DATASET SYNTHÉTIQUE
# ═════════════════════════════════════════════════════════════════════════════
def generate_synthetic_data(n_rows: int = 5000) -> pd.DataFrame:
    """Génère des lignes synthétiques réalistes avec bruit gaussien."""
    print(f"\n🔧  Génération de {n_rows:,} lignes synthétiques…")
    rows = []
    cats = list(SYNTH_PARAMS.keys())
    per_cat = n_rows // len(cats)
    remainder = n_rows - per_cat * len(cats)

    for i, cat in enumerate(cats):
        p = SYNTH_PARAMS[cat]
        n = per_cat + (1 if i < remainder else 0)

        prix_base    = np.random.uniform(p["prix_min"], p["prix_max"], n)
        note_vendeur = np.random.uniform(p["note_min"], p["note_max"], n)

        # Discount dépend intelligemment du prix et de la note
        base_discount = np.random.uniform(p["disc_min"], p["disc_max"], n)

        # Les produits chers → discount légèrement plus élevé
        prix_norm = (prix_base - p["prix_min"]) / max(1, p["prix_max"] - p["prix_min"])
        base_discount += prix_norm * 3  # +0→3% pour les chers

        # Meilleure note → discount plus faible (le produit se vend bien)
        note_norm = (note_vendeur - p["note_min"]) / max(0.1, p["note_max"] - p["note_min"])
        base_discount -= note_norm * 4  # −0→4% pour les bien notés

        # Bruit gaussien σ=2%
        noise = np.random.normal(0, 2, n)
        discount_percent = np.clip(base_discount + noise, 5, 50)

        # prix_min = prix_base * (1 - marge raisonnable)
        marge_extra = np.random.uniform(0.05, 0.15, n)
        prix_min = prix_base * (1 - discount_percent / 100 - marge_extra)
        prix_min = np.maximum(prix_min, prix_base * 0.3)  # plancher 30% du prix

        for j in range(n):
            rows.append({
                "prix_base":        round(float(prix_base[j]), 2),
                "prix_min":         round(float(prix_min[j]), 2),
                "note_vendeur":     round(float(note_vendeur[j]), 2),
                "categorie":        cat,
                "discount_percent": round(float(discount_percent[j]), 2),
            })

    return pd.DataFrame(rows)


# ═════════════════════════════════════════════════════════════════════════════
#  3.  FEATURE ENGINEERING
# ═════════════════════════════════════════════════════════════════════════════
def compute_market_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcule les features de marché :
    - nb_similar_products, avg_similar_price, std_similar_price
    - market_ratio, note_minus_avg
    Basé sur les statistiques intra-catégorie du dataset.
    """
    df = df.copy()

    # Stats intra-catégorie (simule les "produits similaires")
    cat_stats = df.groupby("categorie")["prix_base"].agg(
        nb_similar_products="count",
        avg_similar_price="mean",
        std_similar_price="std",
    ).reset_index()
    cat_stats["std_similar_price"] = cat_stats["std_similar_price"].fillna(0)

    df = df.merge(cat_stats, on="categorie", how="left")

    # Ajouter un léger bruit pour diversifier les features de marché
    n = len(df)
    noise_avg = np.random.normal(1.0, 0.05, n)  # ±5%
    noise_std = np.random.normal(1.0, 0.10, n)   # ±10%
    noise_nb  = np.random.randint(-5, 6, n)

    df["avg_similar_price"] = (df["avg_similar_price"] * noise_avg).round(2)
    df["std_similar_price"] = (df["std_similar_price"] * np.abs(noise_std)).round(2)
    df["nb_similar_products"] = (df["nb_similar_products"] + noise_nb).clip(lower=1).astype(int)

    # Features dérivées
    df["market_ratio"]  = (df["avg_similar_price"] / df["prix_base"]).round(4)
    df["note_minus_avg"] = (df["note_vendeur"] - 3.5).round(2)

    return df


# ═════════════════════════════════════════════════════════════════════════════
#  4.  PIPELINE D'ENTRAÎNEMENT PRINCIPAL
# ═════════════════════════════════════════════════════════════════════════════
def train_and_evaluate():
    """Pipeline complet : data → features → train → evaluate → save."""

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    # ── 1. Charger les données réelles ──
    real_df = load_real_data()

    # ── 2. Données synthétiques ──
    synth_df = generate_synthetic_data(n_rows=5000)

    # ── 3. Combiner ──
    if len(real_df) > 0:
        combined = pd.concat([real_df, synth_df], ignore_index=True)
        print(f"\n📊  Dataset combiné : {len(real_df):,} réelles + {len(synth_df):,} synthétiques = {len(combined):,} lignes")
    else:
        combined = synth_df
        print(f"\n📊  Dataset : {len(combined):,} lignes (synthétiques uniquement)")

    # ── 4. LabelEncoder catégorie ──
    le = LabelEncoder()
    combined["categorie_encoded"] = le.fit_transform(combined["categorie"])
    print(f"   Catégories : {dict(zip(le.classes_, le.transform(le.classes_)))}")

    # ── 5. Feature Engineering ──
    combined = compute_market_features(combined)

    # Vérifier les colonnes
    for col in FEATURE_COLS + [TARGET_COL]:
        assert col in combined.columns, f"Colonne manquante : {col}"

    X = combined[FEATURE_COLS].copy()
    y = combined[TARGET_COL].copy()

    # Nettoyer NaN / Inf
    X = X.replace([np.inf, -np.inf], np.nan).fillna(0)
    y = y.fillna(y.median())

    print(f"\n   Features shape : {X.shape}")
    print(f"   Target range  : [{y.min():.1f}%, {y.max():.1f}%]")
    print(f"   Target mean   : {y.mean():.1f}%")

    # ── 6. Train / Test split 80/20 ──
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=RANDOM_STATE
    )
    print(f"\n   Train : {len(X_train):,}  |  Test : {len(X_test):,}")

    # ── 7. Entraînement ──
    models = {}

    # Random Forest
    print("\n🌲  Entraînement Random Forest (n=200, depth=10)…")
    rf = RandomForestRegressor(
        n_estimators=200,
        max_depth=10,
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )
    rf.fit(X_train, y_train)
    models["Random Forest"] = rf

    # XGBoost
    print("🚀  Entraînement XGBoost (n=200, lr=0.05)…")
    xgb = XGBRegressor(
        n_estimators=200,
        learning_rate=0.05,
        max_depth=6,
        random_state=RANDOM_STATE,
        n_jobs=-1,
        verbosity=0,
    )
    xgb.fit(X_train, y_train)
    models["XGBoost"] = xgb

    # ── 8. Évaluation ──
    print("\n" + "═" * 70)
    print("  RÉSULTATS — Comparaison des modèles")
    print("═" * 70)

    results = {}
    for name, model in models.items():
        y_pred = model.predict(X_test)
        mae  = mean_absolute_error(y_test, y_pred)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        r2   = r2_score(y_test, y_pred)
        results[name] = {"MAE": mae, "RMSE": rmse, "R²": r2, "model": model}

        print(f"\n  📈 {name}")
        print(f"     MAE  = {mae:.4f} %")
        print(f"     RMSE = {rmse:.4f} %")
        print(f"     R²   = {r2:.4f}")

    # ── 9. Sélection du meilleur modèle ──
    best_name = min(results, key=lambda k: results[k]["MAE"])
    best_model = results[best_name]["model"]
    best_metrics = results[best_name]

    print(f"\n  🏆  Meilleur modèle : {best_name}")
    print(f"     MAE={best_metrics['MAE']:.4f}  RMSE={best_metrics['RMSE']:.4f}  R²={best_metrics['R²']:.4f}")
    print("═" * 70)

    # ── 10. Feature Importance ──
    print("\n📊  Génération du graphe d'importance des features…")
    plot_feature_importance(best_model, best_name)

    # ── 11. Sauvegarde ──
    model_path   = ARTIFACTS_DIR / "price_predictor.pkl"
    encoder_path = ARTIFACTS_DIR / "category_encoder.pkl"

    joblib.dump(best_model, model_path)
    joblib.dump(le, encoder_path)

    print(f"\n💾  Modèle sauvegardé   : {model_path}")
    print(f"💾  Encoder sauvegardé  : {encoder_path}")

    # Sauvegarder aussi les stats de marché pour la prédiction
    market_stats = combined.groupby("categorie").agg(
        avg_prix_base=("prix_base", "mean"),
        avg_similar_price=("avg_similar_price", "mean"),
        std_similar_price=("std_similar_price", "mean"),
        nb_similar_products=("nb_similar_products", "median"),
    ).to_dict("index")
    joblib.dump(market_stats, ARTIFACTS_DIR / "market_stats.pkl")
    print(f"💾  Stats marché        : {ARTIFACTS_DIR / 'market_stats.pkl'}")

    # ── 12. Résumé final par catégorie ──
    print("\n" + "─" * 70)
    print("  ANALYSE PAR CATÉGORIE (sur le test set)")
    print("─" * 70)
    test_combined = X_test.copy()
    test_combined["y_true"] = y_test.values
    test_combined["y_pred"] = best_model.predict(X_test)

    for cat_code in sorted(test_combined["categorie_encoded"].unique()):
        cat_name = le.inverse_transform([int(cat_code)])[0]
        mask = test_combined["categorie_encoded"] == cat_code
        sub = test_combined[mask]
        if len(sub) == 0:
            continue
        mae_cat = mean_absolute_error(sub["y_true"], sub["y_pred"])
        print(f"  {cat_name:<15s}  n={len(sub):>5,}  MAE={mae_cat:.2f}%  "
              f"discount moyen={sub['y_true'].mean():.1f}%")
    print("─" * 70)

    # ── 13. Test de la fonction predict_discount ──
    print("\n🧪  Test de predict_discount()…")
    test_result = predict_discount(
        prix_base=1200.0,
        prix_min=900.0,
        note_vendeur=4.3,
        categorie="smartphones",
        similar_prices=[1100, 1250, 1180, 1300, 1050],
    )
    print(f"   Input  : prix_base=1200, note=4.3, cat=smartphones")
    print(f"   Output : {test_result}")

    test_result2 = predict_discount(
        prix_base=25.0,
        prix_min=10.0,
        note_vendeur=3.8,
        categorie="accessoires",
        similar_prices=[20, 30, 15, 28, 22, 18],
    )
    print(f"\n   Input  : prix_base=25, note=3.8, cat=accessoires")
    print(f"   Output : {test_result2}")

    print("\n✅  Entraînement terminé avec succès !")
    return best_model, le, results


# ═════════════════════════════════════════════════════════════════════════════
#  FEATURE IMPORTANCE PLOT
# ═════════════════════════════════════════════════════════════════════════════
def plot_feature_importance(model, model_name: str):
    """Trace et sauvegarde le graphe d'importance des features."""
    if hasattr(model, "feature_importances_"):
        importances = model.feature_importances_
    else:
        print("   ⚠  Le modèle n'a pas de feature_importances_")
        return

    indices = np.argsort(importances)[::-1]
    sorted_names = [FEATURE_COLS[i] for i in indices]
    sorted_importances = importances[indices]

    fig, ax = plt.subplots(figsize=(10, 6))

    # Palette de couleurs dégradée
    colors = plt.cm.viridis(np.linspace(0.3, 0.9, len(sorted_names)))

    bars = ax.barh(range(len(sorted_names)), sorted_importances, color=colors)
    ax.set_yticks(range(len(sorted_names)))
    ax.set_yticklabels(sorted_names, fontsize=11)
    ax.invert_yaxis()
    ax.set_xlabel("Importance", fontsize=12)
    ax.set_title(f"Feature Importance — {model_name}\nAuraMarket Price Predictor",
                 fontsize=14, fontweight="bold", pad=15)

    # Ajouter les valeurs sur les barres
    for bar, val in zip(bars, sorted_importances):
        ax.text(bar.get_width() + 0.002, bar.get_y() + bar.get_height() / 2,
                f"{val:.3f}", va="center", fontsize=10, color="#333333")

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.tight_layout()

    save_path = ARTIFACTS_DIR / "feature_importance.png"
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"   📊 Graphe sauvegardé : {save_path}")


# ═════════════════════════════════════════════════════════════════════════════
#  FONCTION DE PRÉDICTION EXPOSÉE
# ═════════════════════════════════════════════════════════════════════════════
def predict_discount(
    prix_base: float,
    prix_min: float,
    note_vendeur: float,
    categorie: str,
    similar_prices: list,
) -> dict:
    """
    Prédit le pourcentage de remise optimal et le prix suggéré.

    Args:
        prix_base:       Prix de départ vendeur (MAD)
        prix_min:        Plancher prix vendeur (MAD)
        note_vendeur:    Note vendeur (0-5)
        categorie:       Catégorie texte (smartphones, laptops, accessoires, tv, electromenager)
        similar_prices:  Liste de prix de produits similaires sur le marché

    Returns:
        dict avec :
            - discount_percent : remise prédite (5-50%)
            - prix_suggere     : prix final suggéré
            - market_factor    : ratio avg_similar / prix_base
            - confidence       : score de confiance (0-1)
    """
    # Charger les artefacts
    model_path   = ARTIFACTS_DIR / "price_predictor.pkl"
    encoder_path = ARTIFACTS_DIR / "category_encoder.pkl"

    if not model_path.exists() or not encoder_path.exists():
        raise FileNotFoundError(
            "Modèle ou encoder introuvable. Lancez d'abord train_and_evaluate()."
        )

    model = joblib.load(model_path)
    le    = joblib.load(encoder_path)

    # Encoder la catégorie
    if categorie in le.classes_:
        cat_encoded = le.transform([categorie])[0]
    else:
        # Fallback : catégorie la plus proche ou 'accessoires'
        cat_encoded = le.transform(["accessoires"])[0]

    # Calculer les features de marché
    similar = np.array(similar_prices, dtype=float) if similar_prices else np.array([prix_base])
    nb_similar       = len(similar)
    avg_similar      = float(np.mean(similar))
    std_similar      = float(np.std(similar)) if len(similar) > 1 else 0.0
    market_ratio     = avg_similar / max(prix_base, 1e-6)
    note_minus_avg   = note_vendeur - 3.5

    # Construire le vecteur de features
    features = np.array([[
        prix_base,
        prix_min,
        note_vendeur,
        cat_encoded,
        nb_similar,
        avg_similar,
        std_similar,
        market_ratio,
        note_minus_avg,
    ]])

    # Prédire
    raw_discount = float(model.predict(features)[0])
    discount = np.clip(raw_discount, 5.0, 50.0)

    # Prix suggéré
    prix_suggere = prix_base * (1 - discount / 100)
    prix_suggere = max(prix_suggere, prix_min)  # ≥ prix_min

    # Recalculer le discount effectif si clampé par prix_min
    effective_discount = (1 - prix_suggere / prix_base) * 100 if prix_base > 0 else 0
    effective_discount = np.clip(effective_discount, 5.0, 50.0)

    # Confidence basée sur la cohérence marché
    # Plus le prix est proche de la moyenne du marché → plus confiant
    if avg_similar > 0:
        price_coherence = 1.0 - min(abs(prix_base - avg_similar) / avg_similar, 1.0)
    else:
        price_coherence = 0.5

    # Bonus de confiance si beaucoup de produits similaires
    volume_bonus = min(nb_similar / 20, 0.2)

    # Bonus note ≥ 4
    note_bonus = 0.1 if note_vendeur >= 4.0 else 0.0

    confidence = round(min(0.5 + price_coherence * 0.3 + volume_bonus + note_bonus, 0.99), 2)

    return {
        "discount_percent": round(float(effective_discount), 2),
        "prix_suggere":     round(float(prix_suggere), 2),
        "market_factor":    round(float(market_ratio), 2),
        "confidence":       confidence,
    }


# ═════════════════════════════════════════════════════════════════════════════
#  MAIN
# ═════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print()
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║     AuraMarket — ML Price Predictor Trainer                ║")
    print("║     Entraînement du modèle de prédiction de prix           ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()

    best_model, le, results = train_and_evaluate()
