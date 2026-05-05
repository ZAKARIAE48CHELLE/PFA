import os
import joblib
import pandas as pd
import math

# Configuration identique au script d'entraînement
CATEGORIES = {
    "smartphone": {"p_range": (200, 1500), "cf": 0.8},
    "laptop": {"p_range": (400, 3000), "cf": 0.8},
    "tv": {"p_range": (300, 4000), "cf": 0.8},
    "audio": {"p_range": (20, 500), "cf": 1.3},
    "accessoire": {"p_range": (10, 100), "cf": 1.3},
    "electromenager": {"p_range": (100, 2000), "cf": 0.8},
    "maison": {"p_range": (10, 500), "cf": 1.0}
}

_MODEL = None
_LE = None

def load_offer_model():
    global _MODEL, _LE
    if _MODEL is None:
        # Remonter de src/models à DATA AND ML, puis un niveau de plus vers la racine
        artifact_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "artifacts", "offer_security")
        # Si chemin relatif échoue, essayer chemin absolu connu
        if not os.path.exists(artifact_dir):
            artifact_dir = r"c:\Users\zaidh\Desktop\PFA_AURAMARKET\PFA-main\artifacts\offer_security"
            
        model_path = os.path.join(artifact_dir, "offer_security_model.pkl")
        le_path = os.path.join(artifact_dir, "offer_cat_encoder.pkl")
        
        if os.path.exists(model_path):
            _MODEL = joblib.load(model_path)
            _LE = joblib.load(le_path)
        else:
            raise FileNotFoundError(f"Modèle d'offre non trouvé à {model_path}")

def get_theoretical_discount(price, rating, category):
    cf = CATEGORIES.get(category.lower(), {"cf": 1.0})["cf"]
    base = 15.0 + 5.0 * math.log10(max(1, price) + 1) + 4.0 * (5.0 - max(1, min(5, rating)))
    discount = base * cf
    return max(5.0, min(60.0, discount))

def detect_offer_anomaly(price, rating, category, offered_discount):
    """
    Analyse la validité d'une offre.
    Retourne un dictionnaire avec le statut et les alternatives si nécessaire.
    """
    try:
        load_offer_model()
    except Exception as e:
        return {"error": str(e), "statut": "ERROR"}

    d_ref = get_theoretical_discount(price, rating, category)
    
    # Préparation des features pour le ML
    cat_enc = _LE.transform([category.lower()])[0] if category.lower() in _LE.classes_ else 0
    
    features = pd.DataFrame([{
        "prix": price,
        "note": rating,
        "cat_enc": cat_enc,
        "remise_proposee": offered_discount,
        "remise_theorique": d_ref,
        "diff_abs": abs(offered_discount - d_ref),
        "ratio_ref": offered_discount / d_ref if d_ref > 0 else 0
    }])
    
    # Prédiction ML
    is_suspect_ml = _MODEL.predict(features)[0]
    prob_suspect = _MODEL.predict_proba(features)[0][1]
    
    # Décision combinée
    # On rejette si le ML dit suspect OU si c'est mathématiquement délirant
    is_rejected = (is_suspect_ml == 1) or (offered_discount > 85) or (offered_discount < 0)
    
    if not is_rejected:
        return {
            "statut": "ACCEPTABLE",
            "score_fraude": round(float(prob_suspect), 3),
            "message": "L'offre est cohérente avec le marché."
        }
    else:
        # Génération d'alternatives basées sur la formule mathématique
        alts_raw = [
            round(d_ref, 0),
            round(d_ref * 0.8, 0),
            round(d_ref * 1.2, 0)
        ]
        # Nettoyage des alternatives
        alternatives = sorted(list(set([f"{int(max(5, min(60, a)))}%" for a in alts_raw])), reverse=True)
        
        raisons = []
        if offered_discount > d_ref * 2: raisons.append("Remise jugée trop agressive")
        if offered_discount < 2: raisons.append("Remise jugée trop faible pour être attractive")
        if offered_discount > 70: raisons.append("Offre potentiellement irréaliste pour cette catégorie")

        return {
            "statut": "NON ACCEPTABLE",
            "score_fraude": round(float(prob_suspect), 3),
            "raisons": raisons,
            "propositions": alternatives,
            "message": "L'offre a été bloquée car elle semble incohérente ou irréaliste."
        }

if __name__ == "__main__":
    # Test rapide
    print("Test 1 (Smartphone 10% - Valid):", detect_offer_anomaly(800, 4.5, "smartphone", 10))
    print("Test 2 (Smartphone 90% - Invalid):", detect_offer_anomaly(800, 4.5, "smartphone", 90))
    print("Test 3 (Laptop 25% - Valid):", detect_offer_anomaly(1200, 4.0, "laptop", 25))
