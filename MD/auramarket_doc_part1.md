# AuraMarket — Documentation Technique Complète (Partie 1/2)

> **Projet :** AuraMarket — Marketplace multi-agents intelligente  
> **Stack :** JADE 4.6 + Spring Boot 3.2 + Angular 18 + PostgreSQL 15  
> **Généré le :** 2026-05-08

---

## 1. Architecture Générale

### 1.1 Vue d'ensemble des composants

```
┌─────────────────────────────────────────────────────────────────┐
│                     FRONTEND (Angular 18)                       │
│  Port: 4200  —  Angular standalone components, lazy loading     │
│  Routes: /, /login, /signup, /list-produit, /produits/:id,      │
│          /cart, /checkout, /commandes, /dashboard,              │
│          /vendeur, /superviseur                                 │
└────────────────────────┬────────────────────────────────────────┘
                         │ HTTP REST (JWT Bearer)
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                   API GATEWAY (Spring Cloud)                    │
│  Port: 8080  —  CORS global, routage par prédicats de chemin    │
│  /auth/**          → auth-service:8081                         │
│  /products/**      → product-service:8082                      │
│  /offers/**        → product-service:8082                      │
│  /commandes/**     → product-service:8082                      │
│  /negotiations/**  → negotiation-service:8083                  │
│  /audits/**        → audit-service:8084                        │
│  /agent/**         → agents-bridge:8085                        │
└──┬──────────┬──────────┬───────────┬────────────┬──────────────┘
   │          │          │           │            │
   ▼          ▼          ▼           ▼            ▼
 auth      product   negotiation  audit       agents-bridge
 :8081      :8082      :8083       :8084         :8085
   │          │          │           │            │
   └──────────┴──────────┴───────────┘            │
                    │                             │
                    ▼                             ▼
             PostgreSQL :5432              JADE Platform
          4 bases de données           3 agents internes
          auramarket_auth                AgentOffre
          auramarket_product             AgentNegociation
          auramarket_negotiation         AgentSecurite
          auramarket_audit                    │
                                             ▼
                                     ML API :5000
                                   /predict/price
                                   /classify/category
                                   /detect/offer
                                   /detect/comment
```

### 1.2 Flux de communication

| Étape | Acteur | Direction | Protocole |
|-------|--------|-----------|-----------|
| 1 | Frontend → API Gateway | HTTP + JWT | REST/JSON |
| 2 | API Gateway → Microservice | HTTP interne | REST/JSON |
| 3 | product-service → audit-service | HTTP interne | REST/JSON |
| 4 | Frontend → agents-bridge | HTTP + JWT | REST/JSON |
| 5 | agents-bridge → AgentXxx | ACL Message | JADE |
| 6 | AgentOffre / AgentSecurite → ML API | HTTP | REST/JSON |
| 7 | Agent → agents-bridge | ACL INFORM | JADE (sync, timeout 5s) |

---

## 2. Agents JADE

### 2.1 Liste des agents

| Agent | Classe | Rôle principal |
|-------|--------|----------------|
| `AgentNegociation` | `agents.AgentNegociation` | Vendeur IA — négociation de prix par logique floue + renforcement |
| `AgentOffre` | `agents.AgentOffre` | Génération d'offres de prix via ML API |
| `AgentSecurite` | `agents.AgentSecurite` | Détection de fraude sur offres et commentaires via ML API |

Tous démarrés au `@PostConstruct` de `AgentRestBridge`.

---

### 2.2 AgentNegociation

**Rôle :** Représente le vendeur dans la négociation. Reçoit les offres de l'acheteur, calcule une contre-proposition via logique floue (jFuzzyLogic + `negotiation.fcl`) et un système de renforcement comportemental.

**Performative reçue :** `ACLMessage.PROPOSE`

**Payload entrant (JSON) :**
```json
{
  "negociationId": "uuid-string",
  "prixActuel":   150.00,
  "prixMin":       90.00,
  "prixPropose":  110.00,
  "roundActuel":    2,
  "roundsMax":      5,
  "historiqueOffres": [105.0, 108.0, 110.0]
}
```

**Payload sortant (JSON) :**
```json
{
  "negociationId": "uuid-string",
  "nouveauPrix":  130.00,
  "concession":    20.00,
  "buyerBehavior": "SERIOUS",
  "buyerTrend":    "IMPROVING",
  "roundActuel":    2,
  "isFinalOffer":  false
}
```

**Valeurs de `buyerBehavior` :** `AGGRESSIVE` (écart > 30%), `SERIOUS` (10–30%), `CLOSE` (< 10%), `AGGRESSIVE_BUYER`, `ACCEPTED`, `ACCEPTED_AT_FLOOR`, `FLOOR_REACHED`, `TIMEOUT`, `INVALID_CONFIG`, `INVALID`

**Valeurs de `buyerTrend` :** `IMPROVING`, `DECLINING`, `STABLE`, `FINAL`

---

### 2.3 AgentOffre

**Rôle :** Génère un prix suggéré pour un produit en consultant le service ML `/predict/price`. Peut aussi classifier la catégorie via `/classify/category` si non fournie.

**Performative reçue :** `ACLMessage.REQUEST`

**Payload entrant :**
```json
{
  "prixBase":     200.00,
  "prixMin":      120.00,
  "noteVendeur":    4.5,
  "categorie":   "Informatique",
  "similarPrices": [195.0, 198.0, 205.0],
  "produitId":   "uuid-string"
}
```

**Payload sortant :** réponse ML + `produitId` injecté  
**Fallback ML :** si catégorie absente → appel `/classify/category` avec `nom` + `description`

---

### 2.4 AgentSecurite

**Rôle :** Vérifie la légitimité d'une offre (détection de prix abusif) ou d'un commentaire (faux avis). Délègue au ML puis applique un fallback heuristique si ML indisponible.

**Performative reçue :** `ACLMessage.REQUEST`

**Mode OFFRE — Payload entrant :**
```json
{
  "type":      "OFFRE",
  "prix":      15.00,
  "prixBase":  200.00,
  "categorie": "Informatique",
  "rating":    3.5
}
```

**Mode OFFRE — Payload sortant :**
```json
{
  "statut":         "SUSPECT",
  "isSuspect":      true,
  "scoreConfiance": 0.12,
  "raison":         "Prix trop bas | Incohérence catégorie",
  "alternatives":   [170.0, 150.0, 120.0]
}
```

**Fallback heuristique OFFRE :** SUSPECT si `prix <= 0`, `prix > 2×prixBase` ou `prix < 10%×prixBase`.

**Mode COMMENTAIRE — Payload entrant :**
```json
{
  "type":    "COMMENTAIRE",
  "texte":   "Super produit !",
  "note":    5
}
```

**Mode COMMENTAIRE — Payload sortant :**
```json
{
  "statut":           "AUTHENTIQUE",
  "scoreConfiance":   0.91,
  "scoreSuspicion":   9,
  "raisonsDetectees": []
}
```

---

### 2.5 AgentRestBridge (pont Spring Boot ↔ JADE)

Classe : `bridge.AgentRestBridge` — `@RestController` sur port **8085**

- Initialise la plateforme JADE au démarrage (`@PostConstruct`)
- Déploie les 3 agents dans le Main Container
- Communication synchrone via `JadeGateway.execute()` + `blockingReceive(5000ms)`
- Maintient un `ConcurrentHashMap<String, Double> prixActuelMap` pour tracker le `prixActuel` entre rounds

| Endpoint | Méthode | Agent cible | Performative |
|----------|---------|-------------|--------------|
| `/agent/offre/generer` | POST | AgentOffre | REQUEST |
| `/agent/nego/ajuster` | POST | AgentNegociation | PROPOSE |
| `/agent/securite/verifier` | POST | AgentSecurite | REQUEST |

---

## 3. Microservices Spring Boot

### 3.1 API Gateway (`api-gateway`)

| Propriété | Valeur |
|-----------|--------|
| Port | `8080` |
| Spring app name | `api-gateway` |
| Type | Spring Cloud Gateway |
| CORS | `allowedOrigins: "*"`, toutes méthodes |

Routes configurées dans `application.yml` (section [1.1](#11-vue-densemble-des-composants)).  
**Note :** Aucun filtre JWT au niveau gateway — l'authentification est gérée côté frontend.

---

### 3.2 Auth Service (`auth-service`)

| Propriété | Valeur |
|-----------|--------|
| Port | `8081` |
| Base de données | `auramarket_auth` (PostgreSQL) |
| JWT expiration | 86 400 000 ms (24h) |
| Algorithme JWT | HS256 |

#### Endpoints

| Méthode | Chemin | Description | Body |
|---------|--------|-------------|------|
| POST | `/auth/login` | Authentification | `AuthRequest` |
| POST | `/auth/register` | Inscription | `RegisterRequest` |

**`AuthRequest` (entrée) :**
```json
{ "email": "user@example.com", "mdp": "monMotDePasse" }
```

**`AuthResponse` (sortie) :**
```json
{ "token": "eyJhbGci...", "role": "ACHETEUR", "id": "uuid" }
```

**`RegisterRequest` (entrée) :**
```json
{ "email": "user@example.com", "password": "motDePasse", "role": "VENDEUR" }
```

**⚠️ Vulnérabilité détectée :** `AuthService.login()` contient un bypass `"password123"` hardcodé (ligne 36) — mot de passe universel de test non supprimé en production.

**Roles disponibles :** `ACHETEUR`, `VENDEUR`, `SUPERVISEUR`

**Claims JWT :** `sub` (email), `role`, `id`, `iat`, `exp`

---

### 3.3 Product Service (`product-service`)

| Propriété | Valeur |
|-----------|--------|
| Port | `8082` |
| Base de données | `auramarket_product` (PostgreSQL) |
| DDL auto | `update` |

#### Controllers et Endpoints

**ProduitController** — `/products`

| Méthode | Chemin | Description |
|---------|--------|-------------|
| GET | `/products` | Liste tous les produits (filtre optionnel `?category=X`) |
| GET | `/products/{id}` | Détail d'un produit |
| POST | `/products` | Créer un produit |
| PUT | `/products/{id}` | Modifier un produit |
| DELETE | `/products/{id}` | Supprimer un produit |
| GET | `/products/{id}/offers` | Offres d'un produit |
| GET | `/products/stats/categories` | Nombre de produits par catégorie |

**OffreController** — `/offers`

| Méthode | Chemin | Description |
|---------|--------|-------------|
| GET | `/offers` | Toutes les offres |
| POST | `/offers` | Créer une offre |
| PUT | `/offers/{id}` | Modifier une offre |
| DELETE | `/offers/{id}` | Supprimer une offre |

**CommandeController** — pas de préfixe commun

| Méthode | Chemin | Description |
|---------|--------|-------------|
| POST | `/offers/{offreId}/accepter` | Valider une offre → statut VALIDEE |
| POST | `/offers/{offreId}/payer` | Payer une offre → crée Commande + Paiement |
| GET | `/commandes/{commandeId}` | Détail commande |
| GET | `/commandes/acheteur/{acheteurId}` | Commandes d'un acheteur |
| GET | `/commandes/vendeur/{vendeurId}` | Commandes d'un vendeur |
| GET | `/commandes` | Toutes les commandes |

**CommentaireController** — `/products`

| Méthode | Chemin | Description |
|---------|--------|-------------|
| GET | `/products/{produitId}/comments` | Commentaires d'un produit (tri desc) |
| POST | `/products/{produitId}/comments` | Ajouter un commentaire |

#### Services

**ProductService :**
- `getAllProduits(category?)` — paginated (max 1000), tri par `datePublication DESC`
- `createProduit()` / `updateProduit()` / `deleteProduit()` — avec audit automatique vers `audit-service`
- `getProductsCountByCategory()` — query custom `@Query`

**CommandeService (`@Transactional`) :**
- `accepterOffre(offreId)` — passe l'offre à `VALIDEE`, idempotent si déjà validée
- `payerOffre(offreId, request)` — crée `Paiement` (ref `PAY-YYYYMMDD-NNNNNN`) + `Commande` (ref `CMD-...`), décrémente le stock, marque produit `VENDU` si stock = 0
- `getCommande*()` — projections vers `CommandeDTO`

---

### 3.4 Negotiation Service (`negotiation-service`)

| Propriété | Valeur |
|-----------|--------|
| Port | `8083` |
| Base de données | `auramarket_negotiation` (PostgreSQL) |

#### Endpoints

| Méthode | Chemin | Description |
|---------|--------|-------------|
| GET | `/negotiations` | Toutes les négociations |
| POST | `/negotiations` | Créer une négociation (+ message initial AGENT) |
| GET | `/negotiations/{id}/messages` | Messages d'une négociation (tri ASC timestamp) |
| POST | `/negotiations/messages` | Sauvegarder un message (incrémente `rounds` si ACHETEUR) |
| DELETE | `/negotiations/{id}` | Supprimer négociation + ses messages |

**Message initial automatique à la création :**
> *"Bonjour ! Je suis l'agent en charge de ce produit. Quel prix souhaiteriez-vous proposer ?"*

---

### 3.5 Audit Service (`audit-service`)

| Propriété | Valeur |
|-----------|--------|
| Port | `8084` |
| Base de données | `auramarket_audit` (PostgreSQL) |

| Méthode | Chemin | Description |
|---------|--------|-------------|
| GET | `/audits` | Tous les audits |
| POST | `/audits` | Créer un audit |

Alimenté automatiquement par `ProductService.logAudit()` sur create/update produit.

---
