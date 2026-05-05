import logging
import time
import os
import sys
import joblib
import pandas as pd
import numpy as np
from flask import Flask, jsonify, request
from flask_cors import CORS
from textblob import TextBlob
from textblob_fr import PatternTagger, PatternAnalyzer
try:
    from xgboost import XGBClassifier
except ImportError:
    XGBClassifier = None

# Lexiques pour les features manuelles
SUPERLATIFS = ["incroyable", "parfait", "exceptionnel", "génial", "fantastique", "merveilleux", "top", "excellent", "meilleur", "super"]
NEGATIFS_AGRESSIFS = ["arnaque", "fraude", "fuyez", "nul", "décevant", "médiocre", "voleurs", "mensonge", "catastrophe", "pire"]
DETAILS_SPECIFIQUES = ["batterie", "écran", "autonomie", "livraison", "emballage", "bluetooth", "photo", "son", "clavier", "chargeur"]

# Import de la nouvelle logique d'offre
try:
    from predict_offer import detect_offer_anomaly
except ImportError:
    def detect_offer_anomaly(*args, **kwargs):
        # Fallback simple si le script est absent
        price = args[0] if len(args) > 0 else 0
        base = args[3] if len(args) > 3 else 100
        if price > 2 * base or price < 0.1 * base:
            return {"statut": "NON ACCEPTABLE", "message": "Prix hors limites"}
        return {"statut": "ACCEPTABLE", "message": "Offre valide"}

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s")
logger = logging.getLogger("ml_api_integrated")

# Chargement des modèles
MODELS = {}
try:
    MODELS["comment_tfidf"] = joblib.load("comment_tfidf.pkl")
    MODELS["comment_model"] = joblib.load("fake_comment_detector.pkl")
    if os.path.exists("comment_scaler.pkl"):
        MODELS["comment_scaler"] = joblib.load("comment_scaler.pkl")
    
    if os.path.exists("price_predictor.pkl"):
        MODELS["price_predictor"] = joblib.load("price_predictor.pkl")
    if os.path.exists("category_classifier.pkl"):
        MODELS["category_classifier"] = joblib.load("category_classifier.pkl")
    if os.path.exists("offer_category_encoder.pkl"):
        MODELS["category_encoder"] = joblib.load("offer_category_encoder.pkl")
    elif os.path.exists("offer_cat_encoder.pkl"):
        MODELS["category_encoder"] = joblib.load("offer_cat_encoder.pkl")
        
    logger.info("Tous les modèles sémantiques et prédictifs ont été chargés avec succès.")
except Exception as e:
    logger.error(f"Erreur lors du chargement des modèles : {e}")

# --- UTILITAIRES SÉMANTIQUES ---
def get_sentiment(text):
    try:
        blob = TextBlob(text, pos_tagger=PatternTagger(), analyzer=PatternAnalyzer())
        return blob.sentiment[0]
    except:
        return 0.0

def extract_manual_features(text, note):
    text_str = str(text)
    words = text_str.split()
    nb_words = len(words)
    
    features = {}
    features['longueur_mots'] = nb_words
    features['nb_exclamations'] = text_str.count('!')
    features['nb_majuscules_ratio'] = sum(1 for c in text_str if c.isupper()) / (len(text_str) + 1)
    
    def count_in_list(t, word_list):
        t_low = t.lower()
        count = sum(1 for word in word_list if word in t_low)
        return (count / (len(t_low.split()) + 1))

    features['ratio_superlatifs'] = count_in_list(text_str, SUPERLATIFS)
    features['ratio_negatifs'] = count_in_list(text_str, NEGATIFS_AGRESSIFS)
    features['ratio_details'] = count_in_list(text_str, DETAILS_SPECIFIQUES)
    features['diversite_lexicale'] = len(set(text_str.lower().split())) / (nb_words + 1)
     
    features['note'] = float(note)
    features['note_vs_moyenne'] = float(note) - 3.5
    features['sentiment_score'] = get_sentiment(text_str)
    
    note_norm = (float(note) - 3) / 2
    features['coherence_sentiment_note'] = np.abs(features['sentiment_score'] - note_norm)
    
    feature_order = [
        'longueur_mots', 'nb_exclamations', 'nb_majuscules_ratio', 'ratio_superlatifs',
        'ratio_negatifs', 'ratio_details', 'diversite_lexicale', 'note', 
        'note_vs_moyenne', 'sentiment_score', 'coherence_sentiment_note'
    ]
    return np.array([[features.get(f, 0.0) for f in feature_order]])

# --- ENDPOINTS ---

@app.route("/detect/comment", methods=["POST"])
def detect_comment():
    started = time.perf_counter()
    data = request.get_json(silent=True) or {}
    text = str(data.get("text", data.get("texte", data.get("commentaire", "")))).strip()
    note = int(data.get("note", 3))

    if not text:
        return jsonify({"error": "Texte vide"}), 400

    try:
        # Détection de l'Arabe (pour éviter les faux positifs sur cette langue)
        is_arabic = any('\u0600' <= c <= '\u06FF' for c in text)
        
        # 1. Extraction des features manuelles (Sémantique)
        X_manual = extract_manual_features(text, note)
        
        model = MODELS["comment_model"]
        
        # 2. Préparation de l'entrée selon le type de modèle
        # On vérifie si c'est le modèle avec TF-IDF (XGBoost) ou sans (GradientBoosting)
        if "XGB" in str(type(model)):
            vec_tfidf = MODELS["comment_tfidf"].transform([text]).toarray()
            X_final = np.hstack([vec_tfidf, X_manual])
        else:
            # Pour GradientBoosting (Approche A), il faut scaler les 11 features
            X_final = MODELS["comment_scaler"].transform(X_manual)
        
        score_fake = float(model.predict_proba(X_final)[0][1]) if hasattr(model, "predict_proba") else float(model.predict(X_final)[0])
        score_fake = float(np.clip(score_fake, 0.0, 1.0))
        
        # --- AJUSTEMENT SÉMANTIQUE POUR LES CAS COURTS ---
        # Si le modèle est trop sévère sur les textes courts mais positifs
        mots_positifs = ["bon", "bien", "super", "parfait", "excellent", "top", "merci", "génial"]
        if X_manual[0][0] <= 3 and any(m in text.lower() for m in mots_positifs) and note >= 3:
            if score_fake > 0.5:
                score_fake = 0.15 # On force l'acceptation
                logger.info(f"Ajustement sémantique appliqué pour commentaire court positif")
        
        # --- AJUSTEMENT POUR L'ARABE ---
        if is_arabic:
            score_fake = 0.1 # On fait confiance à l'Arabe car le modèle est entraîné sur le Français
            logger.info(f"Détection d'Arabe : Commentaire validé par défaut")
            
        # --- DÉTECTION DU TROLLING / SPAM (ELON MUSK, HAHAHA) ---
        troll_keywords = ["musk", "elon", "gates", "bezos", "trump", "obama", "hahaha", "hihihi", "hohoho"]
        text_lower = text.lower()
        if any(tk in text_lower for tk in troll_keywords):
            # Si on détecte un nom de célébrité ou un rire excessif, on augmente massivement la suspicion
            score_fake = max(score_fake, 0.85)
            logger.info(f"Trolling détecté (Mots clés suspects) : Score augmenté")
        
        raisons = []
        if any(tk in text_lower for tk in troll_keywords): raisons.append("Contenu non-pertinent ou Trolling")
        if X_manual[0][3] > 0.2: raisons.append("Densité de superlatifs anormale")
        if X_manual[0][10] > 0.6: raisons.append("Incohérence sémantique note/texte")
        if X_manual[0][6] < 0.3: raisons.append("Diversité lexicale très faible")

        elapsed_ms = (time.perf_counter() - started) * 1000.0
        logger.info(f"Analyse sémantique ({type(model).__name__}) terminée pour: '{text[:20]}...' -> score: {score_fake:.4f}")

        return jsonify({
            "statut": "FAKE_COMMENT" if score_fake >= 0.5 else "AUTHENTIQUE",
            "score_fake": round(score_fake, 4),
            "confiance": round(1.0 - score_fake, 4),
            "raisons": raisons if score_fake >= 0.5 else [],
        })
    except Exception as e:
        logger.error(f"Erreur analyse sémantique : {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/detect/offer", methods=["POST"])
def detect_offer():
    data = request.get_json(silent=True) or {}
    price = float(data.get("price", data.get("prix", 0)))
    rating = float(data.get("rating", data.get("note", 3.0)))
    category = str(data.get("category", data.get("categorie", "accessoire")))
    base_price = float(data.get("base_price", data.get("prixBase", price)))
    discount = (1 - price / base_price) * 100 if base_price > 0 else 0
    
    result = detect_offer_anomaly(price, rating, category, discount)
    return jsonify(result)

@app.route("/predict/price", methods=["POST"])
def predict_price():
    data = request.get_json(silent=True) or {}
    prix_base = float(data.get("prixBase", 0))
    prix_min = float(data.get("prixMin", 0))
    note_vendeur = float(data.get("noteVendeur", 4.0))
    categorie = str(data.get("categorie", "autre"))
    similar_prices = data.get("similarPrices", [prix_base])
    
    market_avg = float(np.mean(similar_prices))
    market_factor = market_avg / prix_base if prix_base > 0 else 1.0

    if "price_predictor" in MODELS and "category_encoder" in MODELS:
        try:
            encoded_cat = MODELS["category_encoder"].transform([categorie])[0]
            features = np.array([[prix_base, prix_min, note_vendeur, float(encoded_cat), market_avg, market_factor]])
            pred = float(MODELS["price_predictor"].predict(features)[0])
            pred = max(prix_min, pred)
            return jsonify({"prixSuggere": round(pred, 2), "discountPercent": round(((prix_base-pred)/prix_base*100), 2) if prix_base>0 else 0})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    return jsonify({"prixSuggere": round(prix_base * 0.9, 2), "message": "Modele non charge"})

@app.route("/classify/category", methods=["POST"])
def classify_category():
    data = request.get_json(silent=True) or {}
    text = f"{data.get('nom', '')} {data.get('description', '')}".strip()
    if "category_classifier" in MODELS:
        try:
            cat = MODELS["category_classifier"].predict([text])[0]
            return jsonify({"categorie": str(cat)})
        except: pass
    return jsonify({"categorie": "autre"})

if __name__ == "__main__":
    logger.info("🚀 Starting Full Semantic ML API on port 5000")
    app.run(host="0.0.0.0", port=5000, debug=False)
