import os
import sys
import random
import joblib
import pandas as pd
import numpy as np
import math
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, roc_auc_score

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION ET CONSTANTES
# ─────────────────────────────────────────────────────────────────────────────

CATEGORIES = {
    "smartphone": {"p_range": (200, 1500), "cf": 0.8},
    "laptop": {"p_range": (400, 3000), "cf": 0.8},
    "tv": {"p_range": (300, 4000), "cf": 0.8},
    "audio": {"p_range": (20, 500), "cf": 1.3},
    "accessoire": {"p_range": (10, 100), "cf": 1.3},
    "electromenager": {"p_range": (100, 2000), "cf": 0.8},
    "maison": {"p_range": (10, 500), "cf": 1.0}
}

def get_theoretical_discount(price, rating, category):
    """Calcule la remise théorique basée sur la formule Cdiscount."""
    cf = CATEGORIES.get(category, {"cf": 1.0})["cf"]
    
    # Formule : (15 + 5*log10(P+1) + 4*(5-R)) * Cf
    base = 15.0 + 5.0 * math.log10(price + 1) + 4.0 * (5.0 - rating)
    discount = base * cf
    
    # Bornes de sécurité
    return max(5.0, min(60.0, discount))

# ─────────────────────────────────────────────────────────────────────────────
# GÉNÉRATION DU DATASET
# ─────────────────────────────────────────────────────────────────────────────

def generate_security_dataset(n_samples=10000):
    data = []
    
    for i in range(n_samples):
        cat = random.choice(list(CATEGORIES.keys()))
        p_min, p_max = CATEGORIES[cat]["p_range"]
        price = round(random.uniform(p_min, p_max), 2)
        rating = round(random.uniform(1.0, 5.0), 1)
        
        d_ref = get_theoretical_discount(price, rating, cat)
        
        # 70% d'offres acceptables, 30% suspectes
        is_suspect = 0
        raisons = []
        
        if random.random() < 0.30:
            is_suspect = 1
            pattern = random.randint(1, 4)
            
            if pattern == 1: # Trop élevé
                offered_discount = d_ref * random.uniform(2.5, 4.0)
                if offered_discount < 50: offered_discount = random.uniform(70, 95)
                raisons.append("Remise irréaliste (trop élevée)")
            
            elif pattern == 2: # Vraiment trop bas pour une "offre" affichée
                offered_discount = random.uniform(0.0, 1.0)
                raisons.append("Remise insignifiante")
            
            elif pattern == 3: # Incohérence catégorie (ex: smartphone -80%)
                if CATEGORIES[cat]["cf"] < 1.0: # High value
                    offered_discount = random.uniform(65, 95)
                else: # Low value
                    offered_discount = random.uniform(85, 99)
                raisons.append("Incohérence avec la catégorie de produit")
            
            elif pattern == 4: # Aléatoire total
                offered_discount = random.uniform(0, 100)
                # On ne marque suspect que si c'est loin de d_ref
                if 5 <= offered_discount <= 65:
                    is_suspect = 0
                else:
                    raisons.append("Anomalie statistique de prix")
        else:
            # Offre acceptable (plus large : de 5% à 60% ou ±50% de la ref)
            if random.random() > 0.5:
                offered_discount = d_ref * random.uniform(0.4, 1.6)
            else:
                offered_discount = random.uniform(5, 40)
            
            offered_discount = max(2, min(65, offered_discount))

        data.append({
            "prix": price,
            "note": rating,
            "categorie": cat,
            "remise_proposee": round(offered_discount, 2),
            "remise_theorique": round(d_ref, 2),
            "diff_abs": abs(offered_discount - d_ref),
            "ratio_ref": offered_discount / d_ref if d_ref > 0 else 0,
            "is_suspect": is_suspect
        })

    return pd.DataFrame(data)

# ─────────────────────────────────────────────────────────────────────────────
# ENTRAÎNEMENT
# ─────────────────────────────────────────────────────────────────────────────

def train_offer_model():
    print("Generating training data...")
    df = generate_security_dataset(10000)
    
    # Encodage
    le = LabelEncoder()
    df['cat_enc'] = le.fit_transform(df['categorie'])
    
    features = ["prix", "note", "cat_enc", "remise_proposee", "remise_theorique", "diff_abs", "ratio_ref"]
    X = df[features]
    y = df['is_suspect']
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    print("Training Security Agent model (Random Forest)...")
    model = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
    model.fit(X_train, y_train)
    
    y_pred = model.predict(X_test)
    print("\nModel Performance:")
    print(classification_report(y_test, y_pred))
    print(f"AUC Score: {roc_auc_score(y_test, model.predict_proba(X_test)[:, 1]):.4f}")
    
    # Sauvegarde
    artifact_dir = "artifacts/offer_security"
    os.makedirs(artifact_dir, exist_ok=True)
    
    joblib.dump(model, os.path.join(artifact_dir, "offer_security_model.pkl"))
    joblib.dump(le, os.path.join(artifact_dir, "offer_cat_encoder.pkl"))
    
    print(f"\nModel saved in {artifact_dir}")
    
    # Test de génération d'alternatives
    test_case = {"prix": 1000, "note": 4.5, "cat": "smartphone", "remise": 80}
    print(f"\nTest on suspect offer: {test_case}")
    
    d_ref = get_theoretical_discount(test_case["prix"], test_case["note"], test_case["cat"])
    alts = [
        round(d_ref, 0),
        round(d_ref * 0.8, 0),
        round(d_ref * 1.2, 0)
    ]
    # On s'assure qu'elles sont uniques et réalistes
    alts = sorted(list(set([max(5, min(60, a)) for a in alts])), reverse=True)
    print(f"Proposed alternatives: {alts}")

if __name__ == "__main__":
    train_offer_model()
