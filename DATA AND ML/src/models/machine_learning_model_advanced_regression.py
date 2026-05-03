#!/usr/bin/env python
# coding: utf-8

# # Modèle de Prédiction de `discount_pct`
# 
# ## Objectif unique
# 
# Ce notebook a désormais un seul objectif clair :
# 
# > prédire la variable `discount_pct`.
# 
# Autrement dit, nous voulons estimer **le pourcentage de remise** d'un produit à partir de ses caractéristiques observables.
# 
# Cela rend la démarche plus propre méthodologiquement, plus simple à expliquer, et plus directement exploitable dans le projet.
# 
# ---
# 
# ## Question de recherche
# 
# Peut-on apprendre la valeur de `discount_pct` à partir de variables telles que :
# 
# - la source marketplace
# - la catégorie
# - le vendeur
# - le prix initial normalisé
# - la note produit
# - le texte du titre
# 
# Notre hypothèse est la suivante :
# 
# > oui, une partie significative de la logique de remise peut être apprise, même si certaines décisions restent cachées côté marketplace.
# 

# ## Positionnement méthodologique
# 
# Nous faisons ici une **régression supervisée**.
# 
# ### Variable cible
# 
# \[
# y = discount\_pct
# \]
# 
# ### Important
# 
# Nous n'utilisons **pas** `price_offre` comme feature de prédiction principale, car sinon on reconstruirait presque directement la remise via :
# 
# \[
# discount\_pct = \frac{price\_initial - price\_offre}{price\_initial} \times 100
# \]
# 
# Ce serait du leakage.
# 
# Le but ici est de prédire la remise **à partir du contexte produit**, pas de la recalculer à partir du prix déjà remisé.
# 

# ## Stratégie retenue
# 
# Nous comparons **cinq familles** de modèles pour couvrir le spectre des approches :
# 
# ### 1. Baseline linéaire : Ridge
# - rapide, stable, interprétable.
# 
# ### 2. Linéaires régularisés : Lasso / ElasticNet  *(Upgrade 6)*
# - Lasso (L1) : sélection implicite de features via sparsité.
# - ElasticNet (L1+L2) : compromis entre les deux régularisations.
# 
# ### 3. Modèle non linéaire : ExtraTreesRegressor
# - capture les interactions complexes entre marketplace, prix, catégorie.
# 
# ### 4. Gradient Boosting : XGBoost · LightGBM
# - souvent plus performants sur les données tabulaires hétérogènes.
# 
# ### 5. Sélection de features : ExtraTrees + SelectFromModel  *(Upgrade 7)*
# - réduit le bruit des composantes SVD peu informatives.
# 
# ### 6. Stacking Ensemble  *(Upgrade 8)*
# - méta-apprenant (Ridge) combinant les prédictions de Ridge, ExtraTrees, XGBoost, LightGBM.
# 
# Le titre produit est encodé par **TF-IDF**, puis compressé par **TruncatedSVD** (256 composantes) pour les modèles nécessitant un espace dense.

# In[1]:


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


# ## Chargement des données
# 
# Nous partons du dataset traité afin d'éviter les incohérences de format provenant directement des scrapers.
# 

# In[2]:


df = pd.read_csv(DATA_PATH)
print(df.shape)
df.head(3)


# ## Restriction aux lignes utiles pour la régression
# 
# Comme la cible est `discount_pct`, nous gardons uniquement les lignes où cette variable est renseignée.
# 

# In[3]:


reg_df = df[df['discount_pct'].notna()].copy()
print('Nombre de lignes pour la régression :', len(reg_df))
reg_df[['source', 'discount_pct']].head()


# In[4]:


resume = {
    'lignes_regression': len(reg_df),
    'distribution_sources': reg_df['source'].value_counts().to_dict(),
    'discount_pct_stats': reg_df['discount_pct'].describe().to_dict(),
}
resume


# ## Distribution de la cible
# 
# Cette étape permet de comprendre si la cible est concentrée, asymétrique, ou très dispersée.
# 

# In[5]:


fig, axes = plt.subplots(1, 2, figsize=(14, 4))

reg_df['discount_pct'].plot(kind='hist', bins=30, ax=axes[0], color='#8da0cb', edgecolor='black')
axes[0].set_title('Distribution de discount_pct')
axes[0].set_xlabel('discount_pct')

sns.boxplot(x=reg_df['discount_pct'], ax=axes[1], color='#fc8d62')
axes[1].set_title('Boîte à moustaches de discount_pct')
axes[1].set_xlabel('discount_pct')

plt.tight_layout()
plt.show()


# ## Feature engineering
# 
# Nous construisons un espace de features multi-dimensionnel.
# 
# ### Variables numériques
# - `price_initial_mad`
# - `log_price_initial_mad`
# - `rating_filled`
# - `rating_gap_to_5`
# - `rating_missing`
# 
# ### Variables catégorielles
# - `source`
# - `category`
# - `currency`
# - `location`
# - `source_category`
# - `seller_source`
# 
# ### Variable textuelle
# - `title_clean`
# 

# In[6]:


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


# ## Définition du jeu d'entraînement
# 
# Nous créons maintenant :
# 
# - `X` : les variables explicatives
# - `y` : la cible `discount_pct`
# 

# In[7]:


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


# ## Modèle baseline : Ridge
# 
# Le modèle Ridge sert de référence. Il est utile pour mesurer le gain réel apporté par un modèle plus puissant.
# 

# In[8]:


ridge_model = Pipeline([
    ('preprocess', build_sparse_preprocessor(max_features=8000, include_source=True)),
    ('model', Ridge(alpha=1.0)),
])

ridge_model.fit(X_train, y_train)
ridge_pred = np.clip(ridge_model.predict(X_test), 0, 99)

ridge_metrics = {
    'MAE': mean_absolute_error(y_test, ridge_pred),
    'RMSE': float(np.sqrt(mean_squared_error(y_test, ridge_pred))),
    'R2': r2_score(y_test, ridge_pred),
}

ridge_metrics


# ## Modèle amélioré : ExtraTreesRegressor
# 
# Le modèle ExtraTrees est retenu comme modèle principal car il capture mieux les interactions non linéaires entre :
# 
# - type de marketplace
# - niveau de prix
# - structure du titre
# - qualité produit
# - catégorie
# 

# In[9]:


extra_trees_model = Pipeline([
    ('preprocess', build_dense_preprocessor(max_features=10000, include_source=True)),
    ('model', ExtraTreesRegressor(
        n_estimators=400,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1,  # ← Upgrade 2
    )),
])

extra_trees_model.fit(X_train, y_train)
extra_trees_pred = np.clip(extra_trees_model.predict(X_test), 0, 99)

extra_trees_metrics = {
    'MAE': mean_absolute_error(y_test, extra_trees_pred),
    'RMSE': float(np.sqrt(mean_squared_error(y_test, extra_trees_pred))),
    'R2': r2_score(y_test, extra_trees_pred),
}

extra_trees_metrics


# ## Upgrade 1 — XGBoost et LightGBM
# 
# Ces deux modèles gradient-boosted sont souvent plus performants qu'ExtraTrees sur les données tabulaires.  
# Ils utilisent eux aussi le préprocesseur dense (sparse → SVD 256 composantes).
# 

# In[10]:


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


# ## Upgrade 6 — Lasso et ElasticNet (méthodes linéaires)
# 
# Deux modèles linéaires régularisés viennent compléter la baseline Ridge :
# 
# - **Lasso** (régularisation L1) : encourage la sparsité — certains coefficients tombent exactement à zéro, ce qui réalise une **sélection implicite de features**.
# - **ElasticNet** (L1 + L2) : compromis entre Lasso et Ridge contrôlé par `l1_ratio`.
# 
# Les deux utilisent le **même préprocesseur sparse** que Ridge (TF-IDF, sans réduction SVD), ce qui garantit une comparaison équitable côté linéaire.

# In[11]:


from sklearn.linear_model import Lasso, ElasticNet

# ── Lasso ──────────────────────────────────────────────────────────────────
lasso_model = Pipeline([
    ('preprocess', build_sparse_preprocessor(max_features=8000, include_source=True)),
    ('model', Lasso(alpha=0.5, max_iter=5000)),
])

lasso_model.fit(X_train, y_train)
lasso_pred = np.clip(lasso_model.predict(X_test), 0, 99)

lasso_metrics = {
    'MAE':  mean_absolute_error(y_test, lasso_pred),
    'RMSE': float(np.sqrt(mean_squared_error(y_test, lasso_pred))),
    'R2':   r2_score(y_test, lasso_pred),
}
print('Lasso →', lasso_metrics)

# ── ElasticNet ─────────────────────────────────────────────────────────────
elasticnet_model = Pipeline([
    ('preprocess', build_sparse_preprocessor(max_features=8000, include_source=True)),
    ('model', ElasticNet(alpha=0.5, l1_ratio=0.5, max_iter=5000)),
])

elasticnet_model.fit(X_train, y_train)
elasticnet_pred = np.clip(elasticnet_model.predict(X_test), 0, 99)

elasticnet_metrics = {
    'MAE':  mean_absolute_error(y_test, elasticnet_pred),
    'RMSE': float(np.sqrt(mean_squared_error(y_test, elasticnet_pred))),
    'R2':   r2_score(y_test, elasticnet_pred),
}
print('ElasticNet →', elasticnet_metrics)


# ## Upgrade 7 — Test de sélection de features (SelectFromModel)
# 
# Pipeline en **trois étapes** :
# 
# 1. **Préprocesseur dense** : TF-IDF + TruncatedSVD → 256 composantes.
# 2. **SelectFromModel** : un ExtraTrees léger (100 arbres) calcule l'importance de chaque composante SVD, puis ne conserve que celles dont l'importance est ≥ à la **moyenne** (filtre ≈ 50 % des composantes).
# 3. **Modèle final** : ExtraTreesRegressor entraîné sur le sous-espace retenu.
# 
# Objectif : éliminer les composantes peu informatives et améliorer la généralisation.

# In[12]:


from sklearn.feature_selection import SelectFromModel

# ── ExtraTrees + SelectFromModel ───────────────────────────────────────────
et_selection_pipeline = Pipeline([
    ('preprocess', build_dense_preprocessor(max_features=10000, include_source=True)),
    ('selector', SelectFromModel(
        ExtraTreesRegressor(n_estimators=100, random_state=42, n_jobs=-1),
        threshold='mean',
    )),
    ('model', ExtraTreesRegressor(
        n_estimators=400, min_samples_leaf=2, random_state=42, n_jobs=-1,
    )),
])

et_selection_pipeline.fit(X_train, y_train)
et_selection_pred = np.clip(et_selection_pipeline.predict(X_test), 0, 99)

et_selection_metrics = {
    'MAE':  mean_absolute_error(y_test, et_selection_pred),
    'RMSE': float(np.sqrt(mean_squared_error(y_test, et_selection_pred))),
    'R2':   r2_score(y_test, et_selection_pred),
}

# ── Rapport de sélection ───────────────────────────────────────────────────
_sample_pre = et_selection_pipeline['preprocess'].transform(X_train.head(2))
n_in  = _sample_pre.shape[1]
n_out = et_selection_pipeline['selector'].transform(_sample_pre).shape[1]
print(f'Composantes SVD totales  : {n_in}')
print(f'Composantes sélectionnées: {n_out}')
print('ET + SelectFromModel →', et_selection_metrics)


# ## Upgrade 8 — Stacking Ensemble (méthode ensembliste)
# 
# Le **Stacking** combine les prédictions de plusieurs modèles de base (niveau 0) grâce à un méta-apprenant (niveau 1) entraîné sur les prédictions hors-fold.
# 
# | Niveau | Modèles |
# |--------|---------|
# | **Niveau 0** (base) | Ridge · ExtraTrees · XGBoost · LightGBM |
# | **Niveau 1** (méta) | Ridge |
# 
# **Mécanisme :** les prédictions de chaque modèle de base sont générées par validation croisée 5-fold sur l'ensemble d'entraînement → 4 nouvelles features pour le méta-apprenant. Le préprocesseur dense (TF-IDF → SVD 256) est appliqué en amont.

# In[13]:


from sklearn.ensemble import StackingRegressor

# ── Stacking Ensemble ──────────────────────────────────────────────────────
stacking_pipeline = Pipeline([
    ('preprocess', build_dense_preprocessor(max_features=10000, include_source=True)),
    ('stacking', StackingRegressor(
        estimators=[
            ('ridge', Ridge(alpha=1.0)),
            ('et', ExtraTreesRegressor(
                n_estimators=200, min_samples_leaf=2,
                random_state=42, n_jobs=-1,
            )),
            ('xgb', xgb.XGBRegressor(
                n_estimators=200, learning_rate=0.05, max_depth=6,
                subsample=0.8, colsample_bytree=0.8,
                random_state=42, n_jobs=-1, verbosity=0,
                eval_metric='mae',
            )),
            ('lgbm', lgbm.LGBMRegressor(
                n_estimators=200, learning_rate=0.05, max_depth=7, num_leaves=63,
                subsample=0.8, colsample_bytree=0.8,
                random_state=42, n_jobs=-1, verbosity=-1,
            )),
        ],
        final_estimator=Ridge(alpha=1.0),
        cv=5,
    )),
])

stacking_pipeline.fit(X_train, y_train)
stacking_pred = np.clip(stacking_pipeline.predict(X_test), 0, 99)

stacking_metrics = {
    'MAE':  mean_absolute_error(y_test, stacking_pred),
    'RMSE': float(np.sqrt(mean_squared_error(y_test, stacking_pred))),
    'R2':   r2_score(y_test, stacking_pred),
}
print('Stacking →', stacking_metrics)


# ## Upgrade 9 — Modele par source (Per-Source LightGBM Ensemble)
# 
# **Observation cle :** la MAE varie enormement selon la marketplace :
# - Amazon / Jumia / Steam : MAE ≈ 10–12
# - **CDiscount : MAE ≈ 24.76** (deux fois plus grande !)
# 
# Chaque source a sa propre logique de remise (arrondie sur Steam, variable sur Jumia, etc.).
# Entraîner un **LightGBM dedie par source** reduit cette heterogeneite.
# 
# **Architecture :**
# - Pipeline `dense preprocessor + LightGBM` par source.
# - Fallback global pour les sources inconnues.

# In[14]:


from sklearn.base import BaseEstimator, RegressorMixin


class PerSourceEnsemble(BaseEstimator, RegressorMixin):
    """Un pipeline LightGBM dedie par source ; fallback global."""

    def _make_pipe(self):
        return Pipeline([
            # include_source=False : inutile (chaque modele ne voit qu'une source)
            ('preprocess', build_dense_preprocessor(max_features=8000, include_source=False)),
            ('model', lgbm.LGBMRegressor(
                n_estimators=500, learning_rate=0.04,
                max_depth=7, num_leaves=63,
                subsample=0.8, colsample_bytree=0.8,
                min_child_samples=20, reg_lambda=2,
                random_state=42, n_jobs=-1, verbosity=-1,
            )),
        ])

    def fit(self, X, y):
        self.models_ = {}
        for source in sorted(X['source'].unique()):
            mask = (X['source'] == source)
            X_s, y_s = X[mask], y[mask]
            if len(X_s) < 30:
                print(f"  [skip] {source}: {len(X_s)} lignes -> fallback uniquement")
                continue
            p = self._make_pipe()
            p.fit(X_s, y_s)
            self.models_[source] = p
            print(f"  {source:<12}  {len(X_s):>5} lignes  OK")
        # Fallback global
        self.fallback_ = self._make_pipe()
        self.fallback_.fit(X, y)
        return self

    def predict(self, X):
        Xr = X.reset_index(drop=True)
        preds = np.full(len(Xr), np.nan)
        for source, model in self.models_.items():
            mask = (Xr['source'] == source).values
            if mask.any():
                preds[mask] = model.predict(Xr[mask])
        missing = np.where(np.isnan(preds))[0]
        if len(missing):
            preds[missing] = self.fallback_.predict(Xr.iloc[missing])
        return preds


per_source_model = PerSourceEnsemble()
per_source_model.fit(X_train, y_train)
per_source_pred = np.clip(per_source_model.predict(X_test), 0, 99)

per_source_metrics = {
    'MAE':  mean_absolute_error(y_test, per_source_pred),
    'RMSE': float(np.sqrt(mean_squared_error(y_test, per_source_pred))),
    'R2':   r2_score(y_test, per_source_pred),
}

# Rapport par source (compare avec ExtraTrees global)
_src_df = pd.DataFrame({
    'source': X_test['source'].values,
    'y_true': y_test.values,
    'y_pred': per_source_pred,
})
_src_report = _src_df.groupby('source').apply(
    lambda d: pd.Series({
        'n':          len(d),
        'MAE_perSrc': round(mean_absolute_error(d['y_true'], d['y_pred']),  4),
        'MAE_global': round(mean_absolute_error(d['y_true'],
                      np.clip(extra_trees_model.predict(X_test[X_test['source'] == d['source'].iloc[0]]), 0, 99)), 4),
    })
)
print()
print("Per-Source LightGBM global ->", per_source_metrics)
print()
_src_report


# ## Upgrade 10 — HistGradientBoostingRegressor (sklearn natif)
# 
# Implementation sklearn du gradient boosting par **histogramme** (inspire de LightGBM).
# 
# Avantages :
# - Tres rapide grace a la discretisation des features.
# - Gere nativement les valeurs manquantes.
# - Regularisation integree (`l2_regularization`, `min_samples_leaf`).
# - Aucune dependance externe — uniquement sklearn.

# In[15]:


from sklearn.ensemble import HistGradientBoostingRegressor

hgb_model = Pipeline([
    ('preprocess', build_dense_preprocessor(max_features=10000, include_source=True)),
    ('model', HistGradientBoostingRegressor(
        max_iter=500,
        learning_rate=0.04,
        max_depth=8,
        min_samples_leaf=20,
        l2_regularization=0.5,
        random_state=42,
    )),
])

hgb_model.fit(X_train, y_train)
hgb_pred = np.clip(hgb_model.predict(X_test), 0, 99)

hgb_metrics = {
    'MAE':  mean_absolute_error(y_test, hgb_pred),
    'RMSE': float(np.sqrt(mean_squared_error(y_test, hgb_pred))),
    'R2':   r2_score(y_test, hgb_pred),
}
print('HistGradientBoosting ->', hgb_metrics)


# ## Upgrade 11 — LightGBM optimise (RandomizedSearchCV)
# 
# Recherche aleatoire de 15 combinaisons d'hyperparametres en 3-fold CV.
# 
# **Strategie acceleree :**
# 1. Pre-calculer les features denses **une seule fois** (SVD 256 dim).
# 2. Lancer `RandomizedSearchCV` sur ces features fixes (45 fits de LGBM, pas du pipeline complet).
# 3. Reconstruire un pipeline propre avec les meilleurs hyperparametres trouves.
# 
# Espace de recherche : `n_estimators`, `learning_rate`, `max_depth`, `num_leaves`,
# `min_child_samples`, `subsample`, `colsample_bytree`, `reg_alpha`, `reg_lambda`.

# In[16]:


from sklearn.model_selection import RandomizedSearchCV
from scipy.stats import randint, uniform

# ── Etape 1 : features denses calculees une seule fois ─────────────────────
print("Pre-calcul des features denses (une fois pour la recherche)...")
_pre_tune = build_dense_preprocessor(max_features=8000, include_source=True)
X_tr_d = _pre_tune.fit_transform(X_train, y_train)
X_te_d = _pre_tune.transform(X_test)

# ── Etape 2 : recherche aleatoire rapide ───────────────────────────────────
param_dist = {
    'n_estimators':      randint(400, 900),
    'learning_rate':     uniform(0.02, 0.10),
    'max_depth':         randint(5, 10),
    'num_leaves':        randint(40, 128),
    'min_child_samples': randint(10, 50),
    'subsample':         uniform(0.60, 0.40),
    'colsample_bytree':  uniform(0.60, 0.40),
    'reg_alpha':         uniform(0.00, 0.50),
    'reg_lambda':        uniform(0.00, 3.00),
}

rscv = RandomizedSearchCV(
    lgbm.LGBMRegressor(random_state=42, n_jobs=-1, verbosity=-1),
    param_distributions=param_dist,
    n_iter=15,
    cv=3,
    scoring='neg_mean_absolute_error',
    n_jobs=1,          # chaque estimateur utilise deja n_jobs=-1 en interne
    random_state=42,
    verbose=0,
)
rscv.fit(X_tr_d, y_train)
print(f"Meilleure CV MAE : {-rscv.best_score_:.4f}")
print("Meilleurs params :", rscv.best_params_)

# ── Etape 3 : pipeline final propre ────────────────────────────────────────
lgbm_tuned_model = Pipeline([
    ('preprocess', build_dense_preprocessor(max_features=8000, include_source=True)),
    ('model',      lgbm.LGBMRegressor(
        **rscv.best_params_,
        random_state=42, n_jobs=-1, verbosity=-1,
    )),
])
lgbm_tuned_model.fit(X_train, y_train)
lgbm_tuned_pred = np.clip(lgbm_tuned_model.predict(X_test), 0, 99)

lgbm_tuned_metrics = {
    'MAE':  mean_absolute_error(y_test, lgbm_tuned_pred),
    'RMSE': float(np.sqrt(mean_squared_error(y_test, lgbm_tuned_pred))),
    'R2':   r2_score(y_test, lgbm_tuned_pred),
}
print('LightGBM Tuned ->', lgbm_tuned_metrics)


# ## Comparaison des modèles
# 
# Nous comparons maintenant la baseline linéaire et le modèle non linéaire.
# 

# ## Upgrade 5 — Validation croisée 5-fold
# 
# Au lieu d'un seul split 80/20, nous calculons la MAE en validation croisée 5 plis pour chaque modèle.  
# Cela donne une estimation plus robuste de la performance réelle.
# 

# In[17]:


# ── 5-fold CV MAE pour les modeles stateless rapides ─────────────────────
# Note : ET+Selection, Stacking, PerSource, LGBM Tuned ont deja une
#        validation interne  -> on omet leur CV externe pour ne pas doubler.

def cv_mae(pipeline, X, y, cv=5):
    scores = cross_val_score(pipeline, X, y,
                             cv=cv, scoring='neg_mean_absolute_error', n_jobs=-1)
    return float(-scores.mean())

print('Calcul des CV MAE (patience, 7 x 5 fits)...')
cv_results = {
    'Ridge':      cv_mae(ridge_model,       X_train, y_train),
    'Lasso':      cv_mae(lasso_model,       X_train, y_train),
    'ElasticNet': cv_mae(elasticnet_model,  X_train, y_train),
    'ExtraTrees': cv_mae(extra_trees_model, X_train, y_train),
    'XGBoost':    cv_mae(xgboost_model,     X_train, y_train),
    'LightGBM':   cv_mae(lightgbm_model,    X_train, y_train),
    'HGB':        cv_mae(hgb_model,         X_train, y_train),
}
print('CV MAE (5-fold):')
for name, v in cv_results.items():
    print(f'  {name:<12} {v:.3f}')


# In[18]:


comparison = pd.DataFrame([
    {'modele': 'Ridge',        **ridge_metrics,          'CV_MAE_5fold': cv_results['Ridge']},
    {'modele': 'Lasso',        **lasso_metrics,          'CV_MAE_5fold': cv_results['Lasso']},
    {'modele': 'ElasticNet',   **elasticnet_metrics,     'CV_MAE_5fold': cv_results['ElasticNet']},
    {'modele': 'ExtraTrees',   **extra_trees_metrics,    'CV_MAE_5fold': cv_results['ExtraTrees']},
    {'modele': 'XGBoost',      **xgboost_metrics,        'CV_MAE_5fold': cv_results['XGBoost']},
    {'modele': 'LightGBM',     **lightgbm_metrics,       'CV_MAE_5fold': cv_results['LightGBM']},
    {'modele': 'ET+Selection', **et_selection_metrics,   'CV_MAE_5fold': float('nan')},
    {'modele': 'Stacking',     **stacking_metrics,       'CV_MAE_5fold': float('nan')},
    {'modele': 'PerSource',    **per_source_metrics,     'CV_MAE_5fold': float('nan')},
    {'modele': 'HGB',          **hgb_metrics,            'CV_MAE_5fold': cv_results['HGB']},
    {'modele': 'LGBM Tuned',   **lgbm_tuned_metrics,     'CV_MAE_5fold': float('nan')},
])
comparison.sort_values('MAE')


# In[19]:


comparison_melted = comparison.melt(id_vars='modele', var_name='metrique', value_name='valeur')
plt.figure(figsize=(8, 4))
sns.barplot(data=comparison_melted, x='metrique', y='valeur', hue='modele')
plt.title('Comparaison Ridge vs ExtraTrees')
plt.tight_layout()
plt.show()


# ## Analyse détaillée du meilleur modèle
# 
# Dans la suite, nous considérons `ExtraTreesRegressor` comme le modèle principal.
# 

# In[20]:


# Choisir le modele avec la MAE hold-out la plus basse
_all_models = {
    'Ridge':        (ridge_pred,         ridge_metrics,        ridge_model),
    'Lasso':        (lasso_pred,         lasso_metrics,        lasso_model),
    'ElasticNet':   (elasticnet_pred,    elasticnet_metrics,   elasticnet_model),
    'ExtraTrees':   (extra_trees_pred,   extra_trees_metrics,  extra_trees_model),
    'XGBoost':      (xgboost_pred,       xgboost_metrics,      xgboost_model),
    'LightGBM':     (lightgbm_pred,      lightgbm_metrics,     lightgbm_model),
    'ET+Selection': (et_selection_pred,  et_selection_metrics, et_selection_pipeline),
    'Stacking':     (stacking_pred,      stacking_metrics,     stacking_pipeline),
    'PerSource':    (per_source_pred,    per_source_metrics,   per_source_model),
    'HGB':          (hgb_pred,           hgb_metrics,          hgb_model),
    'LGBM Tuned':   (lgbm_tuned_pred,    lgbm_tuned_metrics,   lgbm_tuned_model),
}

best_name = min(_all_models, key=lambda n: _all_models[n][1]['MAE'])
best_pred, best_metrics, best_model = _all_models[best_name]
print(f'Best model: {best_name}')
best_metrics


# In[21]:


eval_df = pd.DataFrame({
    'y_true': y_test.values,
    'y_pred': best_pred,
})
eval_df['abs_error'] = (eval_df['y_true'] - eval_df['y_pred']).abs()
eval_df.describe().T


# In[22]:


fig, axes = plt.subplots(1, 2, figsize=(14, 5))

sns.scatterplot(data=eval_df.sample(min(1500, len(eval_df)), random_state=42), x='y_true', y='y_pred', alpha=0.5, ax=axes[0])
axes[0].plot([0, 100], [0, 100], color='red', linestyle='--')
axes[0].set_title('Réel vs prédit')
axes[0].set_xlabel('discount_pct réel')
axes[0].set_ylabel('discount_pct prédit')

sns.histplot(eval_df['abs_error'], bins=30, kde=True, ax=axes[1], color='#66c2a5')
axes[1].set_title("Distribution de l'erreur absolue")
axes[1].set_xlabel('Erreur absolue')

plt.tight_layout()
plt.show()


# ## Erreur par source
# 
# Cette analyse est importante car elle montre que certaines marketplaces sont plus prévisibles que d'autres.
# 

# In[23]:


source_eval = X_test[['source']].copy()
source_eval['abs_error'] = eval_df['abs_error'].values
source_mae = source_eval.groupby('source')['abs_error'].mean().sort_values()
source_mae


# In[24]:


plt.figure(figsize=(7, 4))
sns.boxplot(data=source_eval, x='source', y='abs_error')
plt.title('Erreur absolue par source')
plt.xlabel('Source')
plt.ylabel('Erreur absolue')
plt.tight_layout()
plt.show()


# ## Démonstration de prédiction
# 
# Cette section montre concrètement comment le modèle prédit `discount_pct` pour quelques produits de test.
# 

# In[25]:


demo = X_test.copy().head(50).copy()
demo['discount_pct_predit'] = np.clip(best_model.predict(demo[feature_columns]), 0, 99)
demo[['title_clean', 'source', 'category', 'price_initial_mad', 'rating_filled', 'discount_pct_predit']]


# ## Sauvegarde du modèle
# 
# Nous sauvegardons ici le meilleur modèle de prédiction de `discount_pct`.
# 

# In[26]:


metrics = {
    'dataset': {
        'rows_total_regression': int(len(base_reg_df)),
        'sources': base_reg_df['source'].value_counts().to_dict(),
    },
    'models': {
        'Ridge':
            {**{k.lower(): float(v) for k, v in ridge_metrics.items()},
             'cv_mae_5fold': cv_results['Ridge']},
        'Lasso':
            {**{k.lower(): float(v) for k, v in lasso_metrics.items()},
             'cv_mae_5fold': cv_results['Lasso']},
        'ElasticNet':
            {**{k.lower(): float(v) for k, v in elasticnet_metrics.items()},
             'cv_mae_5fold': cv_results['ElasticNet']},
        'ExtraTrees':
            {**{k.lower(): float(v) for k, v in extra_trees_metrics.items()},
             'cv_mae_5fold': cv_results['ExtraTrees']},
        'XGBoost':
            {**{k.lower(): float(v) for k, v in xgboost_metrics.items()},
             'cv_mae_5fold': cv_results['XGBoost']},
        'LightGBM':
            {**{k.lower(): float(v) for k, v in lightgbm_metrics.items()},
             'cv_mae_5fold': cv_results['LightGBM']},
        'ET+Selection':
            {**{k.lower(): float(v) for k, v in et_selection_metrics.items()},
             'cv_mae_5fold': None},
        'Stacking':
            {**{k.lower(): float(v) for k, v in stacking_metrics.items()},
             'cv_mae_5fold': None},
        'PerSource':
            {**{k.lower(): float(v) for k, v in per_source_metrics.items()},
             'cv_mae_5fold': None},
        'HGB':
            {**{k.lower(): float(v) for k, v in hgb_metrics.items()},
             'cv_mae_5fold': cv_results['HGB']},
        'LGBM_Tuned':
            {**{k.lower(): float(v) for k, v in lgbm_tuned_metrics.items()},
             'cv_mae_5fold': None},
    },
    'best_model': {
        'name':         best_name,
        'mae':          float(best_metrics['MAE']),
        'rmse':         float(best_metrics['RMSE']),
        'r2':           float(best_metrics['R2']),
        'cv_mae_5fold': float(cv_results[best_name]) if best_name in cv_results else None,
        'mae_by_source': {k: float(v) for k, v in source_mae.to_dict().items()},
    },
}

(ARTIFACTS_DIR / 'discount_model_metrics.json').write_text(
    json.dumps(metrics, indent=2, ensure_ascii=False), encoding='utf-8'
)
joblib.dump(best_model, ARTIFACTS_DIR / 'discount_pct_model.joblib')
metrics


# ## Interprétation finale
# 
# ### Conclusion principale
# 
# Le modèle est capable de prédire `discount_pct` avec une qualité raisonnable, et le modèle non linéaire améliore nettement la baseline linéaire.
# 
# ### Lecture académique
# 
# Cela signifie que :
# 
# - la variable `discount_pct` n'est pas purement aléatoire
# - la remise dépend bien d'un espace de variables multi-dimensionnel
# - les signaux texte + catégorie + source + prix apportent une information réelle
# 
# ### Message fort pour le superviseur
# 
# > Nous avons transformé le problème en une vraie tâche de régression supervisée centrée sur `discount_pct`, puis montré qu'un modèle enrichi non linéaire dépasse clairement une baseline linéaire classique.
# 

# ## Limites et améliorations futures
# 
# ### Limites actuelles
# - Certaines remises restent pilotées par des règles cachées côté marketplace.
# - La qualité de prédiction varie selon la source (`CDiscount` reste plus difficile).
# - Le Stacking entraîne chaque modèle de base 5 fois → coût computationnel élevé.
# 
# ### Perspectives
# 1. ✅ Tester XGBoost/LightGBM *(intégré)*
# 2. ✅ Méthodes linéaires Lasso/ElasticNet *(Upgrade 6)*
# 3. ✅ Sélection de features *(Upgrade 7)*
# 4. ✅ Méthode ensembliste Stacking *(Upgrade 8)*
# 5. Utiliser le GPU lorsque la stack CUDA sera prête.
# 6. Ajouter des embeddings texte plus riches (sentence-transformers).
# 7. Entraîner un modèle spécifique par source si les volumes le permettent.
# 8. Tuning bayésien des hyperparamètres (Optuna).
# 
# Cette suite logique est parfaitement défendable dans une soutenance ou un rapport PFE.

# ## Prédiction d'une ligne spécifique
# 
# Cette cellule est conçue pour prédire `discount_pct` pour **une seule ligne**.
# 
# Elle applique automatiquement :
# 
# - `build_base_dataframe(...)`
# - la sélection de `feature_columns`
# - la duplication sécurisée de la ligne si nécessaire
# 
# Vous pouvez remplacer `df.head(1)` par n'importe quel sous-ensemble d'une seule ligne, par exemple :
# 
# - `df[df["id"] == "AMA_091e5a908c15"]`
# - `df.iloc[[25]]`
# - `mon_dataframe_personnalise`
# 

# In[27]:


def predict_single_row(row_df, model=None):
    """Prédit discount_pct pour une seule ligne du dataset.

    Si `model` n'est pas fourni, utilise automatiquement `best_model`.
    La ligne est dupliquée si nécessaire (certains pipelines texte
    requièrent au moins 2 exemples). Seule la première prédiction est retournée.
    """
    if model is None:
        model = best_model
    row_df = build_base_dataframe(row_df.copy())
    row_df = row_df[feature_columns]
    if len(row_df) == 1:
        row_df = pd.concat([row_df, row_df], ignore_index=True)
    pred = np.clip(model.predict(row_df), 0, 99)
    return float(pred[0])


Topredict = df[df['id'] == 'AMA_4c588cdef653'].copy()
Topredict


# In[28]:


prediction = predict_single_row(Topredict)
print(f"discount_pct prédit : {prediction:.2f}%")


# ## Upgrade 12 — Benchmark élargi de régression
# 
# Cette section ajoute un **banc d'essai plus large** pour tester plusieurs approches de régression sur les mêmes données.
# 
# ### Objectif
# Comparer rapidement des modèles supplémentaires afin d'identifier ceux qui peuvent améliorer la MAE / RMSE / R² :
# 
# - `LinearRegression`
# - `DecisionTreeRegressor`
# - `RandomForestRegressor`
# - `GradientBoostingRegressor`
# - `AdaBoostRegressor`
# - `KNeighborsRegressor`
# - `SVR`
# - `HuberRegressor`
# 
# ### Principe
# - Les modèles **linéaires** et **à noyau / voisinage** utilisent le préprocesseur **sparse**.
# - Les modèles **arborescents / boosting** utilisent le préprocesseur **dense**.
# - Chaque modèle est évalué avec le même split `train/test`.
# - Un `try/except` est utilisé pour éviter qu'un seul modèle bloque tout le benchmark.
# 

# In[29]:


from sklearn.linear_model import LinearRegression, HuberRegressor
from sklearn.tree import DecisionTreeRegressor
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor, AdaBoostRegressor
from sklearn.neighbors import KNeighborsRegressor
from sklearn.svm import SVR

def safe_clip_predict(model, X, low=0, high=99):
    pred = model.predict(X)
    return np.clip(np.asarray(pred, dtype=float), low, high)

additional_regressors = {
    'LinearRegression': Pipeline([
        ('preprocess', build_sparse_preprocessor(max_features=8000, include_source=True)),
        ('model', LinearRegression()),
    ]),
    'HuberRegressor': Pipeline([
        ('preprocess', build_sparse_preprocessor(max_features=8000, include_source=True)),
        ('model', HuberRegressor(epsilon=1.35, alpha=0.0001, max_iter=300)),
    ]),
    'DecisionTree': Pipeline([
        ('preprocess', build_dense_preprocessor(max_features=8000, include_source=True)),
        ('model', DecisionTreeRegressor(
            max_depth=18,
            min_samples_leaf=4,
            random_state=42,
        )),
    ]),
    'RandomForest': Pipeline([
        ('preprocess', build_dense_preprocessor(max_features=10000, include_source=True)),
        ('model', RandomForestRegressor(
            n_estimators=350,
            max_depth=None,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1,
        )),
    ]),
    'GradientBoosting': Pipeline([
        ('preprocess', build_dense_preprocessor(max_features=8000, include_source=True)),
        ('model', GradientBoostingRegressor(
            n_estimators=300,
            learning_rate=0.05,
            max_depth=3,
            random_state=42,
        )),
    ]),
    'AdaBoost': Pipeline([
        ('preprocess', build_dense_preprocessor(max_features=8000, include_source=True)),
        ('model', AdaBoostRegressor(
            n_estimators=250,
            learning_rate=0.05,
            random_state=42,
        )),
    ]),
    'KNeighbors': Pipeline([
        ('preprocess', build_sparse_preprocessor(max_features=6000, include_source=True)),
        ('model', KNeighborsRegressor(
            n_neighbors=9,
            weights='distance',
            metric='minkowski',
            p=2,
        )),
    ]),
    'SVR_rbf': Pipeline([
        ('preprocess', build_dense_preprocessor(max_features=6000, include_source=True)),
        ('model', SVR(
            kernel='rbf',
            C=12.0,
            epsilon=0.8,
            gamma='scale',
        )),
    ]),
}

print(f"{len(additional_regressors)} modèles de régression supplémentaires prêts.")


# ## Évaluation unifiée des nouveaux modèles
# 
# Cette cellule entraîne chaque modèle, calcule les métriques hold-out, puis ajoute une validation croisée 3-fold pour les modèles les plus raisonnables en coût de calcul.
# 

# In[30]:


additional_results = []
additional_predictions = {}
additional_fitted_models = {}

cv_candidates = {
    'LinearRegression',
    'HuberRegressor',
    'DecisionTree',
    'RandomForest',
    'GradientBoosting',
    'KNeighbors',
}

for model_name, pipeline in additional_regressors.items():
    print(f"\n===== {model_name} =====")
    try:
        pipeline.fit(X_train, y_train)
        pred = safe_clip_predict(pipeline, X_test)

        metrics_row = {
            'modele': model_name,
            'MAE': float(mean_absolute_error(y_test, pred)),
            'RMSE': float(np.sqrt(mean_squared_error(y_test, pred))),
            'R2': float(r2_score(y_test, pred)),
        }

        if model_name in cv_candidates:
            try:
                cv_mae_value = cv_mae(pipeline, X, y, cv=3)
            except Exception as cv_error:
                print(f"CV ignorée pour {model_name}: {cv_error}")
                cv_mae_value = np.nan
        else:
            cv_mae_value = np.nan

        metrics_row['CV_MAE_3fold'] = cv_mae_value

        additional_results.append(metrics_row)
        additional_predictions[model_name] = pred
        additional_fitted_models[model_name] = pipeline

        print(metrics_row)

    except Exception as e:
        print(f"Echec sur {model_name}: {type(e).__name__} - {e}")

additional_comparison = (
    pd.DataFrame(additional_results)
    .sort_values(['MAE', 'RMSE', 'R2'], ascending=[True, True, False])
    .reset_index(drop=True)
)

additional_comparison


# In[31]:


if not additional_comparison.empty:
    plt.figure(figsize=(10, 4))
    sns.barplot(data=additional_comparison, x='modele', y='MAE')
    plt.xticks(rotation=45, ha='right')
    plt.title('Benchmark additionnel — MAE par modèle')
    plt.tight_layout()
    plt.show()

    display(additional_comparison.style.background_gradient(subset=['MAE', 'RMSE'], cmap='YlGn_r'))
else:
    print("Aucun modèle additionnel n'a pu être évalué.")


# ## Fusion avec les modèles déjà présents
# 
# On fusionne ici :
# 
# - les modèles initiaux du notebook,
# - les nouveaux modèles de régression ajoutés ci-dessus.
# 
# Le but est d'obtenir **un classement global unique**.
# 

# In[32]:


base_comparison_global = comparison.copy()
if 'CV_MAE_5fold' not in base_comparison_global.columns:
    base_comparison_global['CV_MAE_5fold'] = np.nan

add_global = additional_comparison.copy()
if not add_global.empty:
    add_global['CV_MAE_5fold'] = np.nan
    add_global = add_global.rename(columns={'CV_MAE_3fold': 'CV_MAE_3fold'})
else:
    add_global = pd.DataFrame(columns=['modele', 'MAE', 'RMSE', 'R2', 'CV_MAE_3fold', 'CV_MAE_5fold'])

global_comparison = pd.concat(
    [base_comparison_global, add_global],
    ignore_index=True,
    sort=False
).sort_values(['MAE', 'RMSE', 'R2'], ascending=[True, True, False]).reset_index(drop=True)

global_comparison


# In[33]:


plt.figure(figsize=(11, 5))
sns.barplot(data=global_comparison, x='modele', y='MAE')
plt.xticks(rotation=60, ha='right')
plt.title('Classement global des modèles de régression (plus bas = meilleur)')
plt.tight_layout()
plt.show()


# ## Mise à jour automatique du meilleur modèle
# 
# Si l'un des nouveaux modèles surpasse le meilleur modèle déjà retenu dans le notebook, on met à jour automatiquement :
# 
# - `best_name`
# - `best_model`
# - `best_pred`
# - `best_metrics`
# 
# Ainsi, les cellules de démonstration et de sauvegarde peuvent continuer à fonctionner sans être réécrites.
# 

# In[34]:


if not additional_comparison.empty:
    additional_best_name = additional_comparison.iloc[0]['modele']
    additional_best_mae = float(additional_comparison.iloc[0]['MAE'])

    if additional_best_mae < float(best_metrics['MAE']):
        print(f"Nouveau meilleur modèle détecté : {additional_best_name}")
        best_name = additional_best_name
        best_model = additional_fitted_models[additional_best_name]
        best_pred = additional_predictions[additional_best_name]
        best_metrics = {
            'MAE': float(additional_comparison.iloc[0]['MAE']),
            'RMSE': float(additional_comparison.iloc[0]['RMSE']),
            'R2': float(additional_comparison.iloc[0]['R2']),
        }
    else:
        print(f"Le meilleur modèle existant reste : {best_name}")
else:
    print("Pas de nouveau modèle valide à comparer.")

print("best_name =", best_name)
print("best_metrics =", best_metrics)


# ## Sauvegarde du benchmark étendu
# 
# Cette cellule exporte un classement consolidé dans le dossier d'artefacts pour pouvoir comparer les essais plus tard.
# 

# In[35]:


global_path = ARTIFACTS_DIR / 'global_regression_benchmark.csv'
global_comparison.to_csv(global_path, index=False, encoding='utf-8-sig')
print("Benchmark sauvegardé :", global_path)


# ## Améliorations avancées pour gagner en score
# 
# Cette section ajoute :
# 
# - des **pipelines avec normalisation** pour les modèles sensibles à l'échelle ;
# - une **transformation logarithmique de la cible** pour mieux gérer les distributions asymétriques ;
# - un **tuning d'hyperparamètres** sur plusieurs régressions performantes ;
# - un **benchmark final** pour comparer les versions de base et les versions améliorées.
# 

# In[40]:


from sklearn.pipeline import Pipeline
from sklearn.compose import TransformedTargetRegressor
from sklearn.model_selection import RandomizedSearchCV
from sklearn.preprocessing import StandardScaler, RobustScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.base import clone
from scipy.stats import randint, uniform, loguniform

advanced_results = []
advanced_models = {}
advanced_predictions = {}

def eval_regression_model(name, model, Xtr, Xte, ytr, yte):
    model.fit(Xtr, ytr)
    pred = model.predict(Xte)
    mae = mean_absolute_error(yte, pred)
    rmse = np.sqrt(mean_squared_error(yte, pred))
    r2 = r2_score(yte, pred)
    advanced_results.append({
        'modele': name,
        'MAE': mae,
        'RMSE': rmse,
        'R2': r2
    })
    advanced_models[name] = model
    advanced_predictions[name] = pred
    print(f"{name} -> MAE={mae:.4f} | RMSE={rmse:.4f} | R2={r2:.4f}")

# sécurité sur la cible pour la transformation log
use_log_target = bool(np.all(np.asarray(y_train) > -1) and np.all(np.asarray(y_test) > -1))
print('Log-transform cible possible :', use_log_target)


# In[ ]:


# On instancie d'abord le préprocesseur (utilise la fonction que vous avez définie plus haut)
preprocessor = build_sparse_preprocessor(max_features=8000)

# 1) Pipelines + preprocessor + scaling pour les modèles sensibles à l'échelle
scaled_candidates = {
    'Ridge_scaled': Pipeline([
        ('preprocessor', preprocessor), 
        ('scaler', StandardScaler(with_mean=False)), 
        ('model', Ridge(alpha=10.0))
    ]),
    'Lasso_scaled': Pipeline([
        ('preprocessor', preprocessor), 
        ('scaler', StandardScaler(with_mean=False)), 
        ('model', Lasso(alpha=0.001, max_iter=20000))
    ]),
    'ElasticNet_scaled': Pipeline([
        ('preprocessor', preprocessor), 
        ('scaler', StandardScaler(with_mean=False)), 
        ('model', ElasticNet(alpha=0.001, l1_ratio=0.5, max_iter=20000))
    ]),
    'SVR_rbf_scaled': Pipeline([
        ('preprocessor', preprocessor), 
        ('scaler', StandardScaler(with_mean=False)), 
        ('model', SVR(C=10, gamma='scale', epsilon=0.1))
    ]),
    'KNeighbors_scaled': Pipeline([
        ('preprocessor', preprocessor), 
        ('scaler', StandardScaler(with_mean=False)), 
        ('model', KNeighborsRegressor(n_neighbors=7, weights='distance'))
    ]),
    'Huber_robust_scaled': Pipeline([
        ('preprocessor', preprocessor), 
        ('scaler', RobustScaler(with_centering=False)), 
        ('model', HuberRegressor())
    ])
}

for name, model in scaled_candidates.items():
    eval_regression_model(name, model, X_train, X_test, y_train, y_test)


# In[ ]:


# 2) Versions avec transformation log de la cible
if use_log_target:
    log_target_candidates = {
        'RandomForest_log_target': TransformedTargetRegressor(
            regressor=RandomForestRegressor(n_estimators=400, random_state=42, n_jobs=-1),
            func=np.log1p, inverse_func=np.expm1
        ),
        'GradientBoosting_log_target': TransformedTargetRegressor(
            regressor=GradientBoostingRegressor(random_state=42),
            func=np.log1p, inverse_func=np.expm1
        ),
        'LinearRegression_log_target': TransformedTargetRegressor(
            regressor=Pipeline([('scaler', StandardScaler()), ('model', LinearRegression())]),
            func=np.log1p, inverse_func=np.expm1
        )
    }

    for name, model in log_target_candidates.items():
        eval_regression_model(name, model, X_train, X_test, y_train, y_test)
else:
    print('Transformation log non appliquée car la cible contient des valeurs < -1.')


# In[ ]:


# 3) Tuning avancé sur quelques modèles prometteurs
search_spaces = {
    'RandomForest_tuned_adv': (
        RandomForestRegressor(random_state=42, n_jobs=-1),
        {
            'n_estimators': randint(200, 800),
            'max_depth': [None, 6, 8, 10, 12, 16, 20],
            'min_samples_split': randint(2, 12),
            'min_samples_leaf': randint(1, 6),
            'max_features': ['sqrt', 'log2', None]
        }
    ),
    'GradientBoosting_tuned_adv': (
        GradientBoostingRegressor(random_state=42),
        {
            'n_estimators': randint(100, 500),
            'learning_rate': loguniform(0.01, 0.2),
            'max_depth': randint(2, 6),
            'subsample': uniform(0.6, 0.4),
            'min_samples_split': randint(2, 12),
            'min_samples_leaf': randint(1, 6)
        }
    ),
    'ExtraTrees_tuned_adv': (
        ExtraTreesRegressor(random_state=42, n_jobs=-1),
        {
            'n_estimators': randint(200, 900),
            'max_depth': [None, 8, 10, 12, 16, 20],
            'min_samples_split': randint(2, 10),
            'min_samples_leaf': randint(1, 5),
            'max_features': ['sqrt', 'log2', None]
        }
    )
}

search_summaries = []
for search_name, (base_model, param_dist) in search_spaces.items():
    print(f"\n===== Tuning : {search_name} =====")
    search = RandomizedSearchCV(
        estimator=base_model,
        param_distributions=param_dist,
        n_iter=20,
        scoring='neg_mean_absolute_error',
        cv=3,
        random_state=42,
        n_jobs=-1,
        verbose=0
    )
    search.fit(X_train, y_train)
    best_est = search.best_estimator_
    pred = best_est.predict(X_test)
    mae = mean_absolute_error(y_test, pred)
    rmse = np.sqrt(mean_squared_error(y_test, pred))
    r2 = r2_score(y_test, pred)

    advanced_results.append({'modele': search_name, 'MAE': mae, 'RMSE': rmse, 'R2': r2})
    advanced_models[search_name] = best_est
    advanced_predictions[search_name] = pred
    search_summaries.append({
        'modele': search_name,
        'best_params': search.best_params_,
        'CV_best_MAE': -search.best_score_,
        'Test_MAE': mae,
        'Test_RMSE': rmse,
        'Test_R2': r2
    })
    print('Best params:', search.best_params_)
    print(f"Test -> MAE={mae:.4f} | RMSE={rmse:.4f} | R2={r2:.4f}")

search_summaries_df = pd.DataFrame(search_summaries)
display(search_summaries_df)


# In[ ]:


advanced_comparison = pd.DataFrame(advanced_results).sort_values(by=['MAE', 'RMSE'], ascending=[True, True]).reset_index(drop=True)
print('=== Classement avancé ===')
display(advanced_comparison.style.background_gradient(subset=['MAE', 'RMSE'], cmap='YlGn_r'))

final_global_comparison = pd.concat([global_comparison[['modele', 'MAE', 'RMSE', 'R2']], advanced_comparison], ignore_index=True)
final_global_comparison = final_global_comparison.sort_values(by=['MAE', 'RMSE'], ascending=[True, True]).drop_duplicates(subset=['modele']).reset_index(drop=True)

print('=== Classement final global ===')
display(final_global_comparison.style.background_gradient(subset=['MAE', 'RMSE'], cmap='YlGn_r'))

plt.figure(figsize=(12, 5))
sns.barplot(data=final_global_comparison.head(15), x='modele', y='MAE')
plt.xticks(rotation=65, ha='right')
plt.title('Top 15 des modèles de régression après améliorations')
plt.tight_layout()
plt.show()


# In[ ]:


# 4) Mise à jour du meilleur modèle global
best_final_name = final_global_comparison.iloc[0]['modele']
print('Meilleur modèle final :', best_final_name)

if best_final_name in advanced_models:
    best_model = advanced_models[best_final_name]
    best_pred = advanced_predictions[best_final_name]
    best_metrics = {
        'MAE': float(final_global_comparison.iloc[0]['MAE']),
        'RMSE': float(final_global_comparison.iloc[0]['RMSE']),
        'R2': float(final_global_comparison.iloc[0]['R2'])
    }
    best_name = best_final_name

print('best_name =', best_name)
print('best_metrics =', best_metrics)


# In[ ]:


final_path = ARTIFACTS_DIR / 'final_global_regression_benchmark_with_advanced_models.csv'
final_global_comparison.to_csv(final_path, index=False, encoding='utf-8-sig')
print('Benchmark final sauvegardé :', final_path)

