import os
import sys
import re
import random
import joblib
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import classification_report, roc_auc_score, confusion_matrix
from xgboost import XGBClassifier
from textblob import TextBlob
from textblob_fr import PatternTagger, PatternAnalyzer
import shap

# ─────────────────────────────────────────────────────────────────────────────
# LEXIQUES
# ─────────────────────────────────────────────────────────────────────────────

SUPERLATIFS = ["incroyable", "parfait", "exceptionnel", "génial", "fantastique", "merveilleux", "top", "excellent", "meilleur", "super"]
NEGATIFS_AGRESSIFS = ["arnaque", "fraude", "fuyez", "nul", "décevant", "médiocre", "voleurs", "mensonge", "catastrophe", "pire"]
DETAILS_SPECIFIQUES = ["batterie", "écran", "autonomie", "livraison", "emballage", "bluetooth", "photo", "son", "clavier", "chargeur"]

# ─────────────────────────────────────────────────────────────────────────────
# GÉNÉRATION DU DATASET SYNTHÉTIQUE
# ─────────────────────────────────────────────────────────────────────────────

def generate_fake_comment_data(n_samples=4000):
    data = []
    
    # 60% Authentiques, 40% Fakes
    n_auth = int(n_samples * 0.6)
    n_fake = n_samples - n_auth
    
    # AUTHENTIQUES
    auth_templates = [
        "La {feature} {verbe} bien. Le {feature2} est {adj} pour ce prix.",
        "Livraison {v_livraison} mais l'{emballage} était {v_emb}. Produit {adj} sinon.",
        "Bien dans l'ensemble, mais l'{feature} {v_bug} parfois.",
        "Utilisé depuis {temps}, très satisfait de l'{feature}. Je recommande.",
        "Correct pour le prix, mais ne vous attendez pas à des miracles sur la {feature}."
    ]
    
    for _ in range(n_auth):
        note = random.randint(3, 5)
        if random.random() < 0.2: note = random.randint(1, 2)
        
        text = random.choice(auth_templates).format(
            feature=random.choice(DETAILS_SPECIFIQUES),
            feature2=random.choice(DETAILS_SPECIFIQUES),
            verbe=random.choice(["tient", "fonctionne", "marche"]),
            adj=random.choice(["correct", "bien", "correct", "pas mal"]),
            v_livraison=random.choice(["rapide", "dans les temps"]),
            emballage=random.choice(["emballage", "carton"]),
            v_emb=random.choice(["abîmé", "un peu sale", "correct"]),
            v_bug=random.choice(["bug", "décroche", "chauffe"]),
            temps=random.choice(["1 mois", "2 semaines", "quelques jours"])
        )
        data.append({"texte": text, "note": note, "is_fake": 0})

    # FAKES
    for _ in range(n_fake):
        pattern = random.choice(["A", "B", "C", "D", "E"])
        
        if pattern == "A": # Spam positif
            text = " ".join([random.choice(SUPERLATIFS).capitalize() + " !" for _ in range(5)])
            text += " Je recommande vraiment à tout le monde ! Livraison super rapide !"
            note = 5
        elif pattern == "B": # Spam négatif
            text = " ".join([random.choice(NEGATIFS_AGRESSIFS).capitalize() + " !" for _ in range(4)])
            text += " Ne perdez pas votre argent ! Fuyez ce vendeur !"
            note = 1
        elif pattern == "C": # Incohérence
            if random.random() > 0.5:
                text = "Vraiment décevant, ne fonctionne pas, retour en cours."
                note = 5
            else:
                text = "Excellent produit, parfait en tous points."
                note = 1
        elif pattern == "D": # Court / Vide
            text = random.choice(["Bien.", "Ok", "Super.", "5 étoiles.", "Top"])
            note = 5
        elif pattern == "E": # Répétitif
            phrase = "Produit de qualité supérieure. "
            text = phrase * 3
            note = 5
            
        data.append({"texte": text, "note": note, "is_fake": 1})

    df = pd.DataFrame(data)
    # Mélange
    return df.sample(frac=1).reset_index(drop=True)

# ─────────────────────────────────────────────────────────────────────────────
# FEATURE ENGINEERING
# ─────────────────────────────────────────────────────────────────────────────

def get_sentiment(text):
    blob = TextBlob(text, pos_tagger=PatternTagger(), analyzer=PatternAnalyzer())
    return blob.sentiment[0] # polarity

def extract_features(df):
    features = pd.DataFrame()
    
    # 1. Textuelles
    features['longueur_mots'] = df['texte'].apply(lambda x: len(str(x).split()))
    features['nb_exclamations'] = df['texte'].apply(lambda x: str(x).count('!'))
    features['nb_majuscules_ratio'] = df['texte'].apply(lambda x: sum(1 for c in str(x) if c.isupper()) / (len(str(x)) + 1))
    
    def count_in_list(text, word_list):
        text = str(text).lower()
        count = sum(1 for word in word_list if word in text)
        return count / (len(text.split()) + 1)

    features['ratio_superlatifs'] = df['texte'].apply(lambda x: count_in_list(x, SUPERLATIFS))
    features['ratio_negatifs'] = df['texte'].apply(lambda x: count_in_list(x, NEGATIFS_AGRESSIFS))
    features['ratio_details'] = df['texte'].apply(lambda x: count_in_list(x, DETAILS_SPECIFIQUES))
    
    features['diversite_lexicale'] = df['texte'].apply(lambda x: len(set(str(x).lower().split())) / (len(str(x).split()) + 1))
    
    # 2. Contextuelles
    features['note'] = df['note']
    # Simulation d'une moyenne produit (entre 3 et 4.5)
    df['note_moyenne_prod'] = 3.5
    features['note_vs_moyenne'] = df['note'] - df['note_moyenne_prod']
    
    # 3. Sentiment & Cohérence
    print("   (Analyse de sentiment en cours...)")
    features['sentiment_score'] = df['texte'].apply(get_sentiment)
    # Cohérence : sentiment positif (0.5) vs note élevée (5) -> faible écart
    # On normalise la note sur [-1, 1]
    note_norm = (df['note'] - 3) / 2
    features['coherence_sentiment_note'] = np.abs(features['sentiment_score'] - note_norm)
    
    return features

# ─────────────────────────────────────────────────────────────────────────────
# PIPELINE D'ENTRAÎNEMENT
# ─────────────────────────────────────────────────────────────────────────────

def train_detector():
    print("🚀  Génération du dataset de commentaires (4000 exemples)...")
    df = generate_fake_comment_data(4000)
    
    print("🛠️  Extraction des features manuelles...")
    X_manual = extract_features(df)
    y = df['is_fake']
    
    X_train_m, X_test_m, y_train, y_test = train_test_split(X_manual, y, test_size=0.2, random_state=42, stratify=y)
    df_train, df_test = train_test_split(df, test_size=0.2, random_state=42, stratify=y)

    # ─────────────────────────────────────────────────────────────────────────
    # APPROCHE A : Features + Gradient Boosting
    # ─────────────────────────────────────────────────────────────────────────
    print("\n🌲  Approche A : Features manuelles + Gradient Boosting")
    scaler = StandardScaler()
    X_train_m_scaled = scaler.fit_transform(X_train_m)
    X_test_m_scaled = scaler.transform(X_test_m)
    
    model_a = GradientBoostingClassifier(n_estimators=100, random_state=42)
    model_a.fit(X_train_m_scaled, y_train)
    y_pred_a = model_a.predict(X_test_m_scaled)
    auc_a = roc_auc_score(y_test, model_a.predict_proba(X_test_m_scaled)[:, 1])
    print(f"   - ROC-AUC : {auc_a:.4f}")

    # ─────────────────────────────────────────────────────────────────────────
    # APPROCHE B : TF-IDF + Features + XGBoost
    # ─────────────────────────────────────────────────────────────────────────
    print("\n🚀  Approche B : TF-IDF + Features + XGBoost")
    tfidf = TfidfVectorizer(max_features=2000, ngram_range=(1, 2))
    X_train_tfidf = tfidf.fit_transform(df_train['texte']).toarray()
    X_test_tfidf = tfidf.transform(df_test['texte']).toarray()
    
    # On combine TF-IDF et Features manuelles
    X_train_combined = np.hstack([X_train_tfidf, X_train_m])
    X_test_combined = np.hstack([X_test_tfidf, X_test_m])
    
    model_b = XGBClassifier(eval_metric='logloss')
    model_b.fit(X_train_combined, y_train)
    y_pred_b = model_b.predict(X_test_combined)
    auc_b = roc_auc_score(y_test, model_b.predict_proba(X_test_combined)[:, 1])
    print(f"   - ROC-AUC : {auc_b:.4f}")

    # ─────────────────────────────────────────────────────────────────────────
    # ÉVALUATION & SAUVEGARDE
    # ─────────────────────────────────────────────────────────────────────────
    best_model = model_b if auc_b > auc_a else model_a
    print(f"\n🏆  Meilleur modèle : {'XGBoost (TF-IDF+Features)' if auc_b > auc_a else 'Gradient Boosting (Features only)'}")
    
    print("\n📝  Rapport de classification :")
    print(classification_report(y_test, y_pred_b if auc_b > auc_a else y_pred_a))
    
    artifact_dir = "artifacts/fake_comment_detector"
    os.makedirs(artifact_dir, exist_ok=True)
    
    # SHAP sur Approche A (plus simple à visualiser pour les features manuelles)
    print("\n🧠  Analyse SHAP sur les features manuelles...")
    explainer = shap.TreeExplainer(model_a)
    shap_values = explainer.shap_values(X_test_m_scaled)
    plt.figure(figsize=(10, 6))
    shap.summary_plot(shap_values, X_test_m, show=False)
    plt.savefig(os.path.join(artifact_dir, "shap_features.png"))
    
    # Sauvegardes
    joblib.dump(best_model, os.path.join(artifact_dir, 'fake_comment_detector.pkl'))
    joblib.dump(tfidf, os.path.join(artifact_dir, 'comment_tfidf.pkl'))
    joblib.dump(scaler, os.path.join(artifact_dir, 'comment_scaler.pkl'))
    print(f"💾  Modèles sauvegardés dans {artifact_dir}")

    return best_model, tfidf, scaler

# ─────────────────────────────────────────────────────────────────────────────
# FONCTION FINALE EXPOSÉE
# ─────────────────────────────────────────────────────────────────────────────

_MODEL = None
_TFIDF = None
_SCALER = None

def detect_fake_comment(texte: str, note: int, note_moyenne_produit: float = 3.5) -> dict:
    global _MODEL, _TFIDF, _SCALER
    
    artifact_dir = "artifacts/fake_comment_detector"
    if _MODEL is None:
        try:
            _MODEL = joblib.load(os.path.join(artifact_dir, 'fake_comment_detector.pkl'))
            _TFIDF = joblib.load(os.path.join(artifact_dir, 'comment_tfidf.pkl'))
            _SCALER = joblib.load(os.path.join(artifact_dir, 'comment_scaler.pkl'))
        except:
            return {"error": "Modèle non entraîné"}

    # Extraction des features manuelles
    df_temp = pd.DataFrame([{"texte": texte, "note": note}])
    df_temp['note_moyenne_prod'] = note_moyenne_produit
    X_m = extract_features(df_temp)
    
    # Si le meilleur modèle est l'approche B (XGBoost avec TF-IDF)
    if isinstance(_MODEL, XGBClassifier):
        X_tfidf = _TFIDF.transform([texte]).toarray()
        X_final = np.hstack([X_tfidf, X_m])
    else:
        # Sinon Approche A
        X_final = _SCALER.transform(X_m)

    prob = _MODEL.predict_proba(X_final)[0][1]
    statut = "FAKE_COMMENT" if prob > 0.5 else "AUTHENTIQUE"
    
    # Analyse des raisons
    raisons = []
    if X_m['ratio_superlatifs'].values[0] > 0.2: raisons.append(f"Densité de superlatifs anormale ({X_m['ratio_superlatifs'].values[0]:.2f})")
    if X_m['coherence_sentiment_note'].values[0] > 0.6: raisons.append(f"Incohérence note/sentiment ({X_m['coherence_sentiment_note'].values[0]:.2f})")
    if X_m['diversite_lexicale'].values[0] < 0.3: raisons.append("Diversité lexicale très faible")
    if X_m['nb_exclamations'].values[0] > 3: raisons.append("Excès de ponctuation expressive")

    return {
        "statut": statut,
        "score_suspicion": round(float(prob), 3),
        "score_confiance": round(float(1 - prob), 3),
        "raisons_detectees": raisons if statut == "FAKE_COMMENT" else []
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
    print("║     AuraMarket — Fake Comment Detector Trainer               ║")
    print("╚══════════════════════════════════════════════════════════════╝\n")

    train_detector()
    
    print("\n🧪  Test de détection :")
    tests = [
        ("Incroyable ! Parfait ! Génial ! Je recommande à 100% !", 5),
        ("La batterie est un peu faible mais l'écran est superbe.", 4),
        ("Arnaque ! Fuyez ! Nul !", 1),
        ("Produit magnifique, j'adore !", 1) # Incohérence
    ]
    
    for txt, note in tests:
        res = detect_fake_comment(txt, note)
        print(f"   - Texte : {txt[:40]}... | Note: {note}")
        print(f"     Sortie: {res}")
