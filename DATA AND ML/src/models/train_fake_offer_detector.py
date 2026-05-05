import os
import sys
import random
import joblib
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
from xgboost import XGBClassifier
import shap

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

CATEGORIES = ["smartphone", "laptop", "tv", "casque", "cable_accessoire", "electromenager", "standard"]
PRICE_RANGES = {
    "smartphone": (200, 1500),
    "laptop": (400, 3000),
    "tv": (300, 4000),
    "casque": (50, 600),
    "cable_accessoire": (10, 100),
    "electromenager": (30, 1000),
    "standard": (5, 500)
}

# ─────────────────────────────────────────────────────────────────────────────
# GÉNÉRATION DU DATASET SYNTHÉTIQUE
# ─────────────────────────────────────────────────────────────────────────────

def generate_fake_offer_data(n_samples=5000):
    data = []
    
    for i in range(n_samples):
        cat = random.choice(CATEGORIES)
        p_min, p_max = PRICE_RANGES[cat]
        prix_base = round(random.uniform(p_min, p_max), 2)
        prix_min_marche = round(prix_base * 0.85, 2)
        avg_marche = round(prix_base * 1.05, 2)
        
        # Features de base
        note_vendeur = round(random.uniform(1.0, 5.0), 1)
        age_vendeur_jours = random.randint(1, 1000)
        nb_offres_vendeur = random.randint(1, 500)
        heure = random.randint(0, 23)
        est_weekend = random.choice([True, False])
        
        is_fake = 0
        raisons = []
        
        # 15% de fakes
        if random.random() < 0.15:
            is_fake = 1
            pattern = random.randint(1, 5)
            
            if pattern == 1: # Prix anormal
                if random.random() > 0.5:
                    prix_propose = prix_base * random.uniform(0.01, 0.04)
                    raisons.append(f"ratio prix/base anormalement bas ({prix_propose/prix_base:.2f})")
                else:
                    prix_propose = prix_base * random.uniform(3.1, 10.0)
                    raisons.append(f"ratio prix/base anormalement haut ({prix_propose/prix_base:.2f})")
            
            elif pattern == 2: # Nouveau compte + ratio suspect
                age_vendeur_jours = random.randint(1, 6)
                prix_propose = prix_base * random.uniform(0.4, 0.6)
                raisons.append(f"compte très récent ({age_vendeur_jours}j) avec prix suspect")
            
            elif pattern == 3: # Dumping
                prix_propose = prix_min_marche * random.uniform(0.5, 0.75)
                raisons.append(f"prix très inférieur au minimum marché")
            
            elif pattern == 4: # Heure suspecte + mauvaise note
                heure = random.randint(2, 5)
                note_vendeur = random.uniform(1.0, 2.8)
                prix_propose = prix_base * random.uniform(0.7, 1.2)
                raisons.append(f"publication nocturne ({heure}h) par vendeur mal noté")
            
            elif pattern == 5: # Incohérence catégorie
                if cat == "smartphone":
                    prix_propose = random.uniform(10, 35)
                    raisons.append("prix incohérent pour un smartphone")
                elif cat == "cable_accessoire":
                    prix_propose = random.uniform(1500, 3000)
                    raisons.append("prix incohérent pour un accessoire/câble")
                else:
                    prix_propose = prix_base * 5.0
                    raisons.append("prix incohérent avec la catégorie")
        else:
            # Offre légitime (variation ±30%)
            prix_propose = round(prix_base * random.uniform(0.7, 1.3), 2)

        # Calcul des features dérivées
        ratio_propose_base = prix_propose / prix_base
        ratio_propose_min = prix_propose / prix_min_marche
        deviation_marche = abs(prix_propose - avg_marche) / avg_marche
        
        data.append({
            "prix_propose": prix_propose,
            "prix_base": prix_base,
            "prix_min": prix_min_marche,
            "avg_marche": avg_marche,
            "ratio_propose_base": ratio_propose_base,
            "ratio_propose_min": ratio_propose_min,
            "deviation_marche": deviation_marche,
            "categorie": cat,
            "note_vendeur": note_vendeur,
            "age_vendeur_jours": age_vendeur_jours,
            "nb_offres_vendeur": nb_offres_vendeur,
            "heure_publication": heure,
            "est_weekend": int(est_weekend),
            "is_fake": is_fake,
            "raisons_debug": "; ".join(raisons)
        })

    return pd.DataFrame(data)

# ─────────────────────────────────────────────────────────────────────────────
# PIPELINE D'ENTRAÎNEMENT
# ─────────────────────────────────────────────────────────────────────────────

def train_detector():
    print("🚀  Génération du dataset de fraude (5000 exemples)...")
    df = generate_fake_offer_data(5000)
    
    # Encodage catégorie
    le = LabelEncoder()
    df['categorie_encoded'] = le.fit_transform(df['categorie'])
    
    # Features selection
    features = [
        "prix_propose", "prix_base", "prix_min", 
        "ratio_propose_base", "ratio_propose_min", "deviation_marche",
        "categorie_encoded", "note_vendeur", "age_vendeur_jours", 
        "nb_offres_vendeur", "heure_publication", "est_weekend"
    ]
    
    X = df[features]
    y = df['is_fake']
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    # Scaling
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    print("\n🔍  Entraînement et comparaison des modèles...")
    
    # 1. Isolation Forest
    iso = IsolationForest(contamination=0.15, random_state=42)
    y_pred_iso = iso.fit_predict(X_test_scaled)
    y_pred_iso = [1 if x == -1 else 0 for x in y_pred_iso]
    
    # 2. Random Forest
    rf = RandomForestClassifier(n_estimators=100, random_state=42)
    rf.fit(X_train, y_train)
    y_pred_rf = rf.predict(X_test)
    
    # 3. XGBoost
    xgb = XGBClassifier(use_label_encoder=False, eval_metric='logloss', scale_pos_weight=5.6) # balanced approx
    xgb.fit(X_train, y_train)
    y_pred_xgb = xgb.predict(X_test)

    print("\n📊  RÉSULTATS :")
    print(f"   - Isolation Forest (AUC) : {roc_auc_score(y_test, y_pred_iso):.4f}")
    print(f"   - Random Forest    (AUC) : {roc_auc_score(y_test, y_pred_rf):.4f}")
    print(f"   - XGBoost         (AUC) : {roc_auc_score(y_test, y_pred_xgb):.4f}")
    
    print("\n📝  Rapport détaillé (Random Forest) :")
    print(classification_report(y_test, y_pred_rf))

    # SHAP Analysis
    print("\n🧠  Analyse SHAP (Explicabilité)...")
    explainer = shap.TreeExplainer(rf)
    shap_values = explainer.shap_values(X_test)
    
    plt.figure(figsize=(10, 6))
    # Note: shap.summary_plot peut varier selon la version, on utilise la version bar
    # shap_values[1] correspond à la classe "fake"
    shap.summary_plot(shap_values[:, :, 1], X_test, plot_type="bar", show=False)
    
    artifact_dir = "artifacts/fake_offer_detector"
    os.makedirs(artifact_dir, exist_ok=True)
    plt.savefig(os.path.join(artifact_dir, "shap_importance.png"))
    print(f"📊  Graphique SHAP sauvegardé : {os.path.join(artifact_dir, 'shap_importance.png')}")
    
    # Confusion Matrix
    cm = confusion_matrix(y_test, y_pred_rf)
    plt.figure(figsize=(8, 6))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Reds')
    plt.title('Confusion Matrix - Fake Offer Detector')
    plt.savefig(os.path.join(artifact_dir, "confusion_matrix.png"))

    # Sauvegardes
    joblib.dump(rf, os.path.join(artifact_dir, 'fake_offer_detector.pkl'))
    joblib.dump(le, os.path.join(artifact_dir, 'offer_category_encoder.pkl'))
    joblib.dump(scaler, os.path.join(artifact_dir, 'offer_scaler.pkl'))
    print(f"💾  Modèles et encodeurs sauvegardés dans {artifact_dir}")

    return rf, le, scaler

# ─────────────────────────────────────────────────────────────────────────────
# FONCTION FINALE EXPOSÉE
# ─────────────────────────────────────────────────────────────────────────────

_MODEL = None
_LE = None
_SCALER = None

def detect_fake_offer(prix_propose, prix_base, prix_min, categorie,
                      note_vendeur, age_vendeur_jours, nb_offres,
                      avg_marche, heure=12, est_weekend=False) -> dict:
    global _MODEL, _LE, _SCALER
    
    artifact_dir = "artifacts/fake_offer_detector"
    if _MODEL is None:
        try:
            _MODEL = joblib.load(os.path.join(artifact_dir, 'fake_offer_detector.pkl'))
            _LE = joblib.load(os.path.join(artifact_dir, 'offer_category_encoder.pkl'))
            _SCALER = joblib.load(os.path.join(artifact_dir, 'offer_scaler.pkl'))
        except:
            return {"error": "Modèle non entraîné"}

    # Préparation des features
    cat_enc = _LE.transform([categorie])[0] if categorie in _LE.classes_ else 0
    ratio_base = prix_propose / prix_base
    ratio_min = prix_propose / prix_min
    dev_marche = abs(prix_propose - avg_marche) / avg_marche
    
    features = pd.DataFrame([{
        "prix_propose": prix_propose,
        "prix_base": prix_base,
        "prix_min": prix_min,
        "ratio_propose_base": ratio_base,
        "ratio_propose_min": ratio_min,
        "deviation_marche": dev_marche,
        "categorie_encoded": cat_enc,
        "note_vendeur": note_vendeur,
        "age_vendeur_jours": age_vendeur_jours,
        "nb_offres_vendeur": nb_offres,
        "heure_publication": heure,
        "est_weekend": int(est_weekend)
    }])

    # Prédiction
    prob = _MODEL.predict_proba(features)[0][1]
    prediction = _MODEL.predict(features)[0]
    
    statut = "SUSPECT" if prob > 0.5 else "ACCEPTABLE"
    
    # Analyse des raisons
    raisons = []
    if ratio_base < 0.1: raisons.append(f"prix extrêmement bas par rapport au prix de base ({ratio_base:.2f})")
    if ratio_base > 3.0: raisons.append(f"prix anormalement élevé ({ratio_base:.2f})")
    if age_vendeur_jours < 7 and prob > 0.4: raisons.append(f"nouveau compte ({age_vendeur_jours} jours)")
    if note_vendeur < 2.5: raisons.append(f"vendeur très mal noté ({note_vendeur}/5)")
    if 2 <= heure <= 5: raisons.append("heure de publication suspecte (nuit)")
    
    # Alternatives (prix suggérés)
    alternatives = [round(prix_base * 0.9, 2), round(avg_marche, 2), round(prix_min * 1.1, 2)]
    
    return {
        "statut": statut,
        "score_fraude": round(float(prob), 3),
        "score_confiance": round(float(1 - prob), 3),
        "raisons": raisons if statut == "SUSPECT" else [],
        "alternatives": sorted(alternatives, reverse=True) if statut == "SUSPECT" else []
    }

if __name__ == "__main__":
    # Fix encoding for Windows terminals
    if sys.platform == "win32":
        try:
            import codecs
            sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
            sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())
        except Exception:
            pass

    print("╔══════════════════════════════════════════════════════════════╗")
    print("║     AuraMarket — Fake Offer Detector Trainer                ║")
    print("╚══════════════════════════════════════════════════════════════╝\n")

    train_detector()
    
    print("\n🧪  Test de détection :")
    tests = [
        (50.0, 1000.0, 850.0, "smartphone", 4.5, 300, 50, 950.0), # Suspect (trop bas)
        (900.0, 1000.0, 850.0, "smartphone", 4.8, 500, 120, 950.0), # OK
        (25.0, 1000.0, 850.0, "smartphone", 1.2, 2, 1, 950.0), # Suspect (nouveau + bas + mauvaise note)
        (45.0, 30.0, 25.0, "cable_accessoire", 4.0, 100, 20, 32.0) # OK (câble cher mais pas délirant)
    ]
    
    for t in tests:
        res = detect_fake_offer(*t)
        print(f"   - Prix: {t[0]:7}€ | Base: {t[1]:7}€ | Cat: {t[3]:15} | Statut: {res['statut']} (Fraude: {res['score_fraude']})")
