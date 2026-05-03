# 🛡️ Guide Technique : Intégration ML AuraMarket
**Auteur :** Antigravity AI (pour Zaid)
**Date :** 03 Mai 2026
**Projet :** PFA AuraMarket

Ce document résume les améliorations apportées aujourd'hui et explique comment faire fonctionner l'écosystème complet.

---

## 🚀 1. Comment lancer l'application (Ordre de démarrage)

Pour que tout fonctionne à 100%, suivez cet ordre précis :

### Étape A : Lancer l'Intelligence Artificielle (Python)
L'API ML est le cerveau du projet. Elle doit être active pour que la sécurité fonctionne.
1.  Ouvrez un terminal à la racine du projet (`PFA-main`).
2.  Activez votre environnement Python si nécessaire.
3.  Lancez l'API :
    ```bash
    python ml_api.py
    ```
    *Vérifiez que vous voyez : `🚀 Starting Full Semantic ML API on port 5000`*

### Étape B : Lancer le Backend (Docker & JADE)
Les microservices et les agents JADE doivent être reconstruits pour inclure les nouveaux changements (Persistance).
1.  Ouvrez un nouveau terminal.
2.  Reconstruisez et lancez les microservices :
    ```bash
    docker-compose up --build
    ```
    *Cela va créer la nouvelle table `commentaires` et activer le système de sauvegarde.*

### Étape C : Lancer le Frontend (Angular)
1.  Allez dans le dossier frontend : `cd AURA_MARKET/frontend`.
2.  Lancez le serveur :
    ```bash
    npm start
    ```

---

## 🧠 2. Ce qui a été ajouté aujourd'hui

### 🟢 Analyse Sémantique "Full Power"
L'IA utilise désormais le modèle **XGBoost avec TF-IDF**. Contrairement aux versions précédentes, elle ne se contente pas de compter les mots, elle "lit" le texte.
*   **Support Arabe :** Détection automatique des caractères arabes pour éviter les blocages injustes.
*   **Détection des Trolls :** L'IA repère désormais les messages hors-sujet (ex: Elon Musk, blagues) sans avoir besoin d'une liste manuelle.
*   **Correction des Courts :** Les messages courts mais positifs (ex: "Bon produit !") sont désormais acceptés.

### 💾 Persistance des Commentaires
Auparavant, les commentaires s'effaçaient au rafraîchissement de la page. C'est corrigé :
*   **Backend :** Création d'une entité Java `Commentaire` et d'un Repository dans le `product-service`.
*   **Base de données :** Ajout automatique d'une table `commentaires` dans PostgreSQL.
*   **Frontend :** Le bouton "Publier" n'enregistre le message que **SI** l'Agent Sécurité donne son feu vert.

### 🧹 Nettoyage du Projet
Le projet a été nettoyé pour ne garder que l'essentiel :
*   Le dossier `auramarket-mini` a été supprimé (tout est maintenant dans le projet principal).
*   Tous les modèles IA sont centralisés à la racine (`.pkl`).

---

## 🛠️ 3. Dépannage pour ton ami

*   **Problème :** "Statut IA : ERREUR" sur le site.
    *   **Solution :** L'API Python n'est pas lancée. Relancez `python ml_api.py`.
*   **Problème :** Le commentaire est validé mais n'apparaît pas après un refresh.
    *   **Solution :** Le container `product-service` n'a pas été mis à jour. Faites un `docker-compose up --build product-service`.
*   **Problème :** Erreur `XGBClassifier` manquante.
    *   **Solution :** Installez la bibliothèque : `pip install xgboost`.

---
*Ce document a été généré pour assurer la continuité du projet PFA AuraMarket.*
