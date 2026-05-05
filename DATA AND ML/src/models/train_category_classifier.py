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
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC
from sklearn.naive_bayes import MultinomialNB
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.pipeline import Pipeline
import nltk
from nltk.corpus import stopwords

# Initialisation NLTK
try:
    STOP_WORDS = set(stopwords.words('french'))
except Exception:
    nltk.download('stopwords')
    STOP_WORDS = set(stopwords.words('french'))

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

CATEGORIES = ["smartphone", "laptop", "tv", "casque", "cable_accessoire", "electromenager", "standard"]
CATEGORIE_CF = {
    "smartphone": 0.8, "laptop": 0.8, "tv": 0.8, "electromenager": 0.8,
    "casque": 1.3, "cable_accessoire": 1.3,
    "standard": 1.0
}

BRANDS = {
    "smartphone": ["Apple", "Samsung", "Xiaomi", "Google", "Huawei", "Oppo", "Realme"],
    "laptop": ["Apple", "Dell", "HP", "Lenovo", "Asus", "Acer", "MSI"],
    "tv": ["Samsung", "LG", "Sony", "Philips", "TCL", "Hisense", "Panasonic"],
    "casque": ["Sony", "Bose", "Sennheiser", "JBL", "Marshall", "Apple", "Beats"],
    "cable_accessoire": ["Anker", "Belkin", "Ugreen", "Apple", "Samsung", "Spigen"],
    "electromenager": ["Moulinex", "Philips", "Dyson", "Bosch", "Rowenta", "Tefal", "Nespresso"],
    "standard": ["Monopoly", "LEGO", "Hachette", "Nintendo", "Sony", "Microsoft"]
}

# ─────────────────────────────────────────────────────────────────────────────
# GÉNÉRATION DU DATASET SYNTHÉTIQUE
# ─────────────────────────────────────────────────────────────────────────────

def generate_synthetic_data(n_samples=3000):
    data = []
    
    # Distribution des exemples
    counts = {cat: 400 for cat in CATEGORIES if cat != "standard"}
    counts["standard"] = 200
    
    # Ajustement si n_samples est différent de 2600 (par défaut 3000 demandés)
    total_requested = sum(counts.values())
    ratio = n_samples / total_requested
    for cat in counts:
        counts[cat] = int(counts[cat] * ratio)

    templates = {
        "smartphone": [
            "{brand} {model} {specs}",
            "{model} par {brand}, {specs}",
            "Smartphone {brand} {model} neuf",
            "{brand} {model} {color} {storage}GB"
        ],
        "laptop": [
            "PC Portable {brand} {model} {specs}",
            "{brand} {model} {specs} SSD {ssd}GB",
            "Ordinateur portable {brand} {specs}",
            "{model} {brand} {cpu} {ram}GB RAM"
        ],
        "tv": [
            "TV {brand} {size} pouces {tech} 4K",
            "{brand} Smart TV {size}'' {tech}",
            "Téléviseur {brand} LED 4K {size} pouces",
            "{brand} {model} {tech} 120Hz"
        ],
        "casque": [
            "Casque Bluetooth {brand} {model}",
            "Écouteurs sans fil {brand} {model}",
            "{brand} {model} réduction de bruit active",
            "Casque audio {brand} filaire"
        ],
        "cable_accessoire": [
            "Câble {type} {brand} {length}m",
            "Chargeur rapide {brand} {power}W",
            "Coque {brand} {model} transparente",
            "Support voiture pour {device}",
            "Adaptateur {brand} {type} vers {type2}"
        ],
        "electromenager": [
            "Aspirateur {brand} {model}",
            "Machine à café {brand} {model}",
            "Robot cuisine {brand} multifonction",
            "Friteuse sans huile {brand}",
            "Bouilloire électrique {brand} {color}"
        ],
        "standard": [
            "Livre {title}",
            "Jeu de société {title}",
            "Figurine {char}",
            "Sac à dos {brand} {color}",
            "Montre {brand} classique"
        ]
    }

    # Données pour les templates
    specs_data = {
        "specs": ["5G Dual Sim", "Pro Max", "Ultra", "256GB Titane", "Plus", "Lite"],
        "tech": ["OLED", "QLED", "NanoCell", "Mini-LED", "Cristal UHD"],
        "cpu": ["Core i5", "Core i7", "Ryzen 5", "M2", "M3", "Ryzen 7"],
        "char": ["Spider-Man", "Batman", "Naruto", "One Piece"],
        "title": ["Python pour débutants", "Le Seigneur des Anneaux", "Cuisine Facile", "Monopoly", "Scrabble"]
    }

    for cat, count in counts.items():
        for _ in range(count):
            brand = random.choice(BRANDS[cat])
            template = random.choice(templates[cat])
            
            # Remplissage dynamique
            text = template.format(
                brand=brand,
                model=f"Model-{random.randint(10, 99)}",
                specs=random.choice(specs_data["specs"]),
                color=random.choice(["Noir", "Blanc", "Bleu", "Gris", "Or"]),
                storage=random.choice([64, 128, 256, 512]),
                ssd=random.choice([256, 512, 1024]),
                ram=random.choice([8, 16, 32]),
                size=random.choice([43, 50, 55, 65, 75]),
                tech=random.choice(specs_data["tech"]),
                cpu=random.choice(specs_data["cpu"]),
                type=random.choice(["USB-C", "Lightning", "HDMI", "Jack"]),
                length=random.choice([1, 2, 3]),
                power=random.choice([20, 30, 65, 100]),
                device=random.choice(["iPhone", "Samsung", "Laptop"]),
                type2=random.choice(["HDMI", "VGA", "DisplayPort"]),
                title=random.choice(specs_data["title"]),
                char=random.choice(specs_data["char"])
            )

            # Ajout d'une description aléatoire
            desc_len = random.choice(["short", "medium", "long"])
            if desc_len == "short":
                desc = "Produit de qualité supérieure."
            elif desc_len == "medium":
                desc = f"Découvrez le nouveau {text}. Idéal pour un usage quotidien avec des performances exceptionnelles."
            else:
                desc = f"Le {text} est conçu pour offrir la meilleure expérience possible. Doté de technologies avancées, il garantit fiabilité et durabilité. Profitez de la garantie constructeur de 2 ans. Livraison rapide incluse."

            # Fautes de frappe (10%)
            if random.random() < 0.10:
                text = text.replace('e', '3').replace('a', 'q') if random.random() > 0.5 else text.replace('i', '1')

            data.append({"nom": text, "description": desc, "categorie": cat})

    return pd.DataFrame(data)

# ─────────────────────────────────────────────────────────────────────────────
# PREPROCESSING
# ─────────────────────────────────────────────────────────────────────────────

def clean_text(text):
    if not isinstance(text, str):
        return ""
    text = text.lower()
    # Suppression ponctuation et caractères spéciaux
    text = re.sub(r'[^a-z0-9àâçéèêëîïôûùÿñæœ]', ' ', text)
    # Suppression des stopwords
    words = text.split()
    words = [w for w in words if w not in STOP_WORDS and len(w) > 1]
    return " ".join(words)

# ─────────────────────────────────────────────────────────────────────────────
# PIPELINE D'ENTRAÎNEMENT
# ─────────────────────────────────────────────────────────────────────────────

def train_classifier():
    print("🚀  Génération du dataset synthétique (3000 exemples)...")
    df = generate_synthetic_data(3000)
    
    print("🧹  Preprocessing des textes...")
    df['text_combined'] = df['nom'] + " " + df['description']
    df['text_cleaned'] = df['text_combined'].apply(clean_text)
    
    X = df['text_cleaned']
    y = df['categorie']
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    models = {
        "Logistic Regression": LogisticRegression(C=1.0, max_iter=1000),
        "LinearSVC": LinearSVC(max_iter=2000),
        "Naive Bayes": MultinomialNB()
    }
    
    best_acc = 0
    best_pipeline = None
    best_name = ""
    
    results = {}

    print("\n🔍  Comparaison des modèles :")
    for name, model in models.items():
        pipeline = Pipeline([
            ('tfidf', TfidfVectorizer(max_features=10000, ngram_range=(1, 2))),
            ('clf', model)
        ])
        
        pipeline.fit(X_train, y_train)
        y_pred = pipeline.predict(X_test)
        acc = accuracy_score(y_test, y_pred)
        results[name] = acc
        print(f"   - {name:20}: {acc:.4f}")
        
        if acc > best_acc:
            best_acc = acc
            best_pipeline = pipeline
            best_name = name

    print(f"\n🏆  Meilleur modèle : {best_name} ({best_acc:.4f})")
    
    # Évaluation finale
    y_pred_final = best_pipeline.predict(X_test)
    print("\n📝  Rapport de classification :")
    print(classification_report(y_test, y_pred_final))
    
    # Confusion Matrix Heatmap
    cm = confusion_matrix(y_test, y_pred_final, labels=CATEGORIES)
    plt.figure(figsize=(10, 8))
    sns.heatmap(cm, annot=True, fmt='d', xticklabels=CATEGORIES, yticklabels=CATEGORIES, cmap='Blues')
    plt.title(f'Confusion Matrix - {best_name}')
    plt.ylabel('Vraie Catégorie')
    plt.xlabel('Catégorie Prédite')
    
    # Création du dossier artifacts si besoin
    artifact_dir = "artifacts/category_classifier"
    os.makedirs(artifact_dir, exist_ok=True)
    
    plot_path = os.path.join(artifact_dir, "confusion_matrix.png")
    plt.savefig(plot_path)
    print(f"📊  Matrice de confusion sauvegardée : {plot_path}")
    
    # Sauvegarde du modèle
    model_path = os.path.join(artifact_dir, "category_classifier.pkl")
    joblib.dump(best_pipeline, model_path)
    print(f"💾  Modèle sauvegardé : {model_path}")
    
    return best_pipeline

# ─────────────────────────────────────────────────────────────────────────────
# FONCTION FINALE EXPOSÉE
# ─────────────────────────────────────────────────────────────────────────────

# Variable globale pour charger le modèle une seule fois si nécessaire
_MODEL = None

def classify_product(nom: str, description: str = "") -> dict:
    global _MODEL
    
    if _MODEL is None:
        model_path = "artifacts/category_classifier/category_classifier.pkl"
        if os.path.exists(model_path):
            _MODEL = joblib.load(model_path)
        else:
            print("⚠️  Modèle non trouvé. Veuillez d'abord exécuter train_classifier().")
            return {"categorie": "standard", "cf": 1.0, "confidence": 0.0}

    text = clean_text(nom + " " + description)
    prediction = _MODEL.predict([text])[0]
    
    # Calcul de la probabilité si supporté par le modèle
    confidence = 1.0
    if hasattr(_MODEL.named_steps['clf'], "predict_proba"):
        probs = _MODEL.predict_proba([text])[0]
        confidence = np.max(probs)
    elif hasattr(_MODEL.named_steps['clf'], "decision_function"):
        # Pour LinearSVC on peut utiliser decision_function mais c'est moins direct en probabilité
        confidence = 0.95 # Estimation par défaut pour SVC s'il gagne
        
    return {
        "categorie": prediction,
        "cf": CATEGORIE_CF.get(prediction, 1.0),
        "confidence": round(float(confidence), 3)
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
    print("║     AuraMarket — Product Category Classifier Trainer        ║")
    print("╚══════════════════════════════════════════════════════════════╝\n")

    trained_model = train_classifier()
    
    print("\n🧪  Test rapide :")
    test_items = [
        ("Sony WH-1000XM5 écouteurs Bluetooth réduction bruit", "Le meilleur casque du marché."),
        ("iPhone 15 Pro 256GB titane", ""),
        ("Câble USB-C 100W charge rapide 2m", "Câble tressé ultra résistant"),
        ("Aspirateur robot Roomba i7", "Nettoyage intelligent et automatique")
    ]
    
    for nom, desc in test_items:
        res = classify_product(nom, desc)
        print(f"   - Input  : {nom[:40]}...")
        print(f"     Output : {res}")
