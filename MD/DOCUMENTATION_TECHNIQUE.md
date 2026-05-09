# AuraMarket â€” Documentation Technique ComplÃ¨te (Partie 1/2)

> **Projet :** AuraMarket â€” Marketplace multi-agents intelligente  
> **Stack :** JADE 4.6 + Spring Boot 3.2 + Angular 18 + PostgreSQL 15  
> **GÃ©nÃ©rÃ© le :** 2026-05-08

---

## 1. Architecture GÃ©nÃ©rale

### 1.1 Vue d'ensemble des composants

```
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚                     FRONTEND (Angular 18)                       â”‚
â”‚  Port: 4200  â€”  Angular standalone components, lazy loading     â”‚
â”‚  Routes: /, /login, /signup, /list-produit, /produits/:id,      â”‚
â”‚          /cart, /checkout, /commandes, /dashboard,              â”‚
â”‚          /vendeur, /superviseur                                 â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                         â”‚ HTTP REST (JWT Bearer)
                         â–¼
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚                   API GATEWAY (Spring Cloud)                    â”‚
â”‚  Port: 8080  â€”  CORS global, routage par prÃ©dicats de chemin    â”‚
â”‚  /auth/**          â†’ auth-service:8081                         â”‚
â”‚  /products/**      â†’ product-service:8082                      â”‚
â”‚  /offers/**        â†’ product-service:8082                      â”‚
â”‚  /commandes/**     â†’ product-service:8082                      â”‚
â”‚  /negotiations/**  â†’ negotiation-service:8083                  â”‚
â”‚  /audits/**        â†’ audit-service:8084                        â”‚
â”‚  /agent/**         â†’ agents-bridge:8085                        â”‚
â””â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
   â”‚          â”‚          â”‚           â”‚            â”‚
   â–¼          â–¼          â–¼           â–¼            â–¼
 auth      product   negotiation  audit       agents-bridge
 :8081      :8082      :8083       :8084         :8085
   â”‚          â”‚          â”‚           â”‚            â”‚
   â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜            â”‚
                    â”‚                             â”‚
                    â–¼                             â–¼
             PostgreSQL :5432              JADE Platform
          4 bases de donnÃ©es           3 agents internes
          auramarket_auth                AgentOffre
          auramarket_product             AgentNegociation
          auramarket_negotiation         AgentSecurite
          auramarket_audit                    â”‚
                                             â–¼
                                     ML API :5000
                                   /predict/price
                                   /classify/category
                                   /detect/offer
                                   /detect/comment
```

### 1.2 Flux de communication

| Ã‰tape | Acteur | Direction | Protocole |
|-------|--------|-----------|-----------|
| 1 | Frontend â†’ API Gateway | HTTP + JWT | REST/JSON |
| 2 | API Gateway â†’ Microservice | HTTP interne | REST/JSON |
| 3 | product-service â†’ audit-service | HTTP interne | REST/JSON |
| 4 | Frontend â†’ agents-bridge | HTTP + JWT | REST/JSON |
| 5 | agents-bridge â†’ AgentXxx | ACL Message | JADE |
| 6 | AgentOffre / AgentSecurite â†’ ML API | HTTP | REST/JSON |
| 7 | Agent â†’ agents-bridge | ACL INFORM | JADE (sync, timeout 5s) |

---

## 2. Agents JADE

### 2.1 Liste des agents

| Agent | Classe | RÃ´le principal |
|-------|--------|----------------|
| `AgentNegociation` | `agents.AgentNegociation` | Vendeur IA â€” nÃ©gociation de prix par logique floue + renforcement |
| `AgentOffre` | `agents.AgentOffre` | GÃ©nÃ©ration d'offres de prix via ML API |
| `AgentSecurite` | `agents.AgentSecurite` | DÃ©tection de fraude sur offres et commentaires via ML API |

Tous dÃ©marrÃ©s au `@PostConstruct` de `AgentRestBridge`.

---

### 2.2 AgentNegociation

**RÃ´le :** ReprÃ©sente le vendeur dans la nÃ©gociation. ReÃ§oit les offres de l'acheteur, calcule une contre-proposition via logique floue (jFuzzyLogic + `negotiation.fcl`) et un systÃ¨me de renforcement comportemental.

**Performative reÃ§ue :** `ACLMessage.PROPOSE`

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

**Valeurs de `buyerBehavior` :** `AGGRESSIVE` (Ã©cart > 30%), `SERIOUS` (10â€“30%), `CLOSE` (< 10%), `AGGRESSIVE_BUYER`, `ACCEPTED`, `ACCEPTED_AT_FLOOR`, `FLOOR_REACHED`, `TIMEOUT`, `INVALID_CONFIG`, `INVALID`

**Valeurs de `buyerTrend` :** `IMPROVING`, `DECLINING`, `STABLE`, `FINAL`

---

### 2.3 AgentOffre

**RÃ´le :** GÃ©nÃ¨re un prix suggÃ©rÃ© pour un produit en consultant le service ML `/predict/price`. Peut aussi classifier la catÃ©gorie via `/classify/category` si non fournie.

**Performative reÃ§ue :** `ACLMessage.REQUEST`

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

**Payload sortant :** rÃ©ponse ML + `produitId` injectÃ©  
**Fallback ML :** si catÃ©gorie absente â†’ appel `/classify/category` avec `nom` + `description`

---

### 2.4 AgentSecurite

**RÃ´le :** VÃ©rifie la lÃ©gitimitÃ© d'une offre (dÃ©tection de prix abusif) ou d'un commentaire (faux avis). DÃ©lÃ¨gue au ML puis applique un fallback heuristique si ML indisponible.

**Performative reÃ§ue :** `ACLMessage.REQUEST`

**Mode OFFRE â€” Payload entrant :**
```json
{
  "type":      "OFFRE",
  "prix":      15.00,
  "prixBase":  200.00,
  "categorie": "Informatique",
  "rating":    3.5
}
```

**Mode OFFRE â€” Payload sortant :**
```json
{
  "statut":         "SUSPECT",
  "isSuspect":      true,
  "scoreConfiance": 0.12,
  "raison":         "Prix trop bas | IncohÃ©rence catÃ©gorie",
  "alternatives":   [170.0, 150.0, 120.0]
}
```

**Fallback heuristique OFFRE :** SUSPECT si `prix <= 0`, `prix > 2Ã—prixBase` ou `prix < 10%Ã—prixBase`.

**Mode COMMENTAIRE â€” Payload entrant :**
```json
{
  "type":    "COMMENTAIRE",
  "texte":   "Super produit !",
  "note":    5
}
```

**Mode COMMENTAIRE â€” Payload sortant :**
```json
{
  "statut":           "AUTHENTIQUE",
  "scoreConfiance":   0.91,
  "scoreSuspicion":   9,
  "raisonsDetectees": []
}
```

---

### 2.5 AgentRestBridge (pont Spring Boot â†” JADE)

Classe : `bridge.AgentRestBridge` â€” `@RestController` sur port **8085**

- Initialise la plateforme JADE au dÃ©marrage (`@PostConstruct`)
- DÃ©ploie les 3 agents dans le Main Container
- Communication synchrone via `JadeGateway.execute()` + `blockingReceive(5000ms)`
- Maintient un `ConcurrentHashMap<String, Double> prixActuelMap` pour tracker le `prixActuel` entre rounds

| Endpoint | MÃ©thode | Agent cible | Performative |
|----------|---------|-------------|--------------|
| `/agent/offre/generer` | POST | AgentOffre | REQUEST |
| `/agent/nego/ajuster` | POST | AgentNegociation | PROPOSE |
| `/agent/securite/verifier` | POST | AgentSecurite | REQUEST |

---

## 3. Microservices Spring Boot

### 3.1 API Gateway (`api-gateway`)

| PropriÃ©tÃ© | Valeur |
|-----------|--------|
| Port | `8080` |
| Spring app name | `api-gateway` |
| Type | Spring Cloud Gateway |
| CORS | `allowedOrigins: "*"`, toutes mÃ©thodes |

Routes configurÃ©es dans `application.yml` (section [1.1](#11-vue-densemble-des-composants)).  
**Note :** Aucun filtre JWT au niveau gateway â€” l'authentification est gÃ©rÃ©e cÃ´tÃ© frontend.

---

### 3.2 Auth Service (`auth-service`)

| PropriÃ©tÃ© | Valeur |
|-----------|--------|
| Port | `8081` |
| Base de donnÃ©es | `auramarket_auth` (PostgreSQL) |
| JWT expiration | 86 400 000 ms (24h) |
| Algorithme JWT | HS256 |

#### Endpoints

| MÃ©thode | Chemin | Description | Body |
|---------|--------|-------------|------|
| POST | `/auth/login` | Authentification | `AuthRequest` |
| POST | `/auth/register` | Inscription | `RegisterRequest` |

**`AuthRequest` (entrÃ©e) :**
```json
{ "email": "user@example.com", "mdp": "monMotDePasse" }
```

**`AuthResponse` (sortie) :**
```json
{ "token": "eyJhbGci...", "role": "ACHETEUR", "id": "uuid" }
```

**`RegisterRequest` (entrÃ©e) :**
```json
{ "email": "user@example.com", "password": "motDePasse", "role": "VENDEUR" }
```

**âš ï¸ VulnÃ©rabilitÃ© dÃ©tectÃ©e :** `AuthService.login()` contient un bypass `"password123"` hardcodÃ© (ligne 36) â€” mot de passe universel de test non supprimÃ© en production.

**Roles disponibles :** `ACHETEUR`, `VENDEUR`, `SUPERVISEUR`

**Claims JWT :** `sub` (email), `role`, `id`, `iat`, `exp`

---

### 3.3 Product Service (`product-service`)

| PropriÃ©tÃ© | Valeur |
|-----------|--------|
| Port | `8082` |
| Base de donnÃ©es | `auramarket_product` (PostgreSQL) |
| DDL auto | `update` |

#### Controllers et Endpoints

**ProduitController** â€” `/products`

| MÃ©thode | Chemin | Description |
|---------|--------|-------------|
| GET | `/products` | Liste tous les produits (filtre optionnel `?category=X`) |
| GET | `/products/{id}` | DÃ©tail d'un produit |
| POST | `/products` | CrÃ©er un produit |
| PUT | `/products/{id}` | Modifier un produit |
| DELETE | `/products/{id}` | Supprimer un produit |
| GET | `/products/{id}/offers` | Offres d'un produit |
| GET | `/products/stats/categories` | Nombre de produits par catÃ©gorie |

**OffreController** â€” `/offers`

| MÃ©thode | Chemin | Description |
|---------|--------|-------------|
| GET | `/offers` | Toutes les offres |
| POST | `/offers` | CrÃ©er une offre |
| PUT | `/offers/{id}` | Modifier une offre |
| DELETE | `/offers/{id}` | Supprimer une offre |

**CommandeController** â€” pas de prÃ©fixe commun

| MÃ©thode | Chemin | Description |
|---------|--------|-------------|
| POST | `/offers/{offreId}/accepter` | Valider une offre â†’ statut VALIDEE |
| POST | `/offers/{offreId}/payer` | Payer une offre â†’ crÃ©e Commande + Paiement |
| GET | `/commandes/{commandeId}` | DÃ©tail commande |
| GET | `/commandes/acheteur/{acheteurId}` | Commandes d'un acheteur |
| GET | `/commandes/vendeur/{vendeurId}` | Commandes d'un vendeur |
| GET | `/commandes` | Toutes les commandes |

**CommentaireController** â€” `/products`

| MÃ©thode | Chemin | Description |
|---------|--------|-------------|
| GET | `/products/{produitId}/comments` | Commentaires d'un produit (tri desc) |
| POST | `/products/{produitId}/comments` | Ajouter un commentaire |

#### Services

**ProductService :**
- `getAllProduits(category?)` â€” paginated (max 1000), tri par `datePublication DESC`
- `createProduit()` / `updateProduit()` / `deleteProduit()` â€” avec audit automatique vers `audit-service`
- `getProductsCountByCategory()` â€” query custom `@Query`

**CommandeService (`@Transactional`) :**
- `accepterOffre(offreId)` â€” passe l'offre Ã  `VALIDEE`, idempotent si dÃ©jÃ  validÃ©e
- `payerOffre(offreId, request)` â€” crÃ©e `Paiement` (ref `PAY-YYYYMMDD-NNNNNN`) + `Commande` (ref `CMD-...`), dÃ©crÃ©mente le stock, marque produit `VENDU` si stock = 0
- `getCommande*()` â€” projections vers `CommandeDTO`

---

### 3.4 Negotiation Service (`negotiation-service`)

| PropriÃ©tÃ© | Valeur |
|-----------|--------|
| Port | `8083` |
| Base de donnÃ©es | `auramarket_negotiation` (PostgreSQL) |

#### Endpoints

| MÃ©thode | Chemin | Description |
|---------|--------|-------------|
| GET | `/negotiations` | Toutes les nÃ©gociations |
| POST | `/negotiations` | CrÃ©er une nÃ©gociation (+ message initial AGENT) |
| GET | `/negotiations/{id}/messages` | Messages d'une nÃ©gociation (tri ASC timestamp) |
| POST | `/negotiations/messages` | Sauvegarder un message (incrÃ©mente `rounds` si ACHETEUR) |
| DELETE | `/negotiations/{id}` | Supprimer nÃ©gociation + ses messages |

**Message initial automatique Ã  la crÃ©ation :**
> *"Bonjour ! Je suis l'agent en charge de ce produit. Quel prix souhaiteriez-vous proposer ?"*

---

### 3.5 Audit Service (`audit-service`)

| PropriÃ©tÃ© | Valeur |
|-----------|--------|
| Port | `8084` |
| Base de donnÃ©es | `auramarket_audit` (PostgreSQL) |

| MÃ©thode | Chemin | Description |
|---------|--------|-------------|
| GET | `/audits` | Tous les audits |
| POST | `/audits` | CrÃ©er un audit |

AlimentÃ© automatiquement par `ProductService.logAudit()` sur create/update produit.

---
# AuraMarket â€” Documentation Technique ComplÃ¨te (Partie 2/2)

---

## 4. ModÃ¨les de donnÃ©es

### 4.1 EntitÃ©s JPA

#### `Utilisateur` (base : `utilisateurs`) â€” auth-service
| Champ | Type | Contrainte |
|-------|------|-----------|
| `id` | UUID | PK, auto-gÃ©nÃ©rÃ© |
| `email` | String | UNIQUE, NOT NULL |
| `mdpHash` | String | NOT NULL (BCrypt) |
| `role` | Enum | `ACHETEUR`, `VENDEUR`, `SUPERVISEUR` |

**HÃ©ritage :** `InheritanceType.JOINED`
- **`Vendeur`** (table `vendeurs`) : + `scoreReputation` (float, dÃ©faut 5.0)
- **`Acheteur`** (table `acheteurs`) : + `historique` (List\<String\>, `@ElementCollection`)

---

#### `Produit` (table `produits`) â€” product-service
| Champ | Type | Description |
|-------|------|-------------|
| `id` | UUID | PK |
| `titre` | String | Nom du produit |
| `description` | TEXT | Description longue |
| `prix` | double | Prix de vente affichÃ© |
| `prixMin` | double | Prix plancher de nÃ©gociation |
| `prixOffre` | Double | Prix d'offre spÃ©ciale (nullable) |
| `categorie` | String | CatÃ©gorie libre |
| `imageUrl` | TEXT | URL de l'image |
| `stock` | int | QuantitÃ© disponible |
| `statut` | Enum | `ACTIF`, `BLOQUE`, `VENDU`, `EN_ATTENTE` |
| `datePublication` | LocalDateTime | Auto au constructeur |
| `vendeurId` | UUID | FK vers utilisateurs (non enforced en DB) |

**Payload JSON typique :**
```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "titre": "iPhone 15 Pro",
  "description": "Smartphone haut de gamme",
  "prix": 1299.00,
  "prixMin": 999.00,
  "prixOffre": null,
  "categorie": "Smartphones",
  "imageUrl": "https://...",
  "stock": 10,
  "statut": "ACTIF",
  "datePublication": "2026-05-01T10:00:00",
  "vendeurId": "uuid-vendeur"
}
```

---

#### `Offre` (table `offres`) â€” product-service
| Champ | Type | Description |
|-------|------|-------------|
| `id` | UUID | PK |
| `titre` | String | LibellÃ© de l'offre |
| `description` | String | Description |
| `prixPropose` | double | Prix proposÃ© par l'acheteur |
| `prixFinal` | double | Prix final acceptÃ© |
| `statut` | Enum | `EN_ATTENTE`, `VALIDEE`, `REJETEE`, `EXPIREE` |
| `dateCreation` | LocalDateTime | Auto |
| `dateExpiration` | LocalDateTime | Date limite de validitÃ© |
| `dateDebut` | LocalDateTime | DÃ©but de pÃ©riode d'offre |
| `dateFin` | LocalDateTime | Fin de pÃ©riode d'offre |
| `produitId` | UUID | FK produit |
| `acheteurId` | UUID | FK acheteur |
| `agentGenere` | boolean | `true` si gÃ©nÃ©rÃ©e par AgentOffre |
| `pourcentageDiscount` | double | % de remise |

---

#### `Commande` (table `commandes`) â€” product-service
| Champ | Type | Description |
|-------|------|-------------|
| `id` | UUID | PK |
| `reference` | String | UNIQUE â€” format `CMD-YYYYMMDD-NNNNNN` |
| `offreId` | UUID | Offre source |
| `acheteurId` | UUID | Acheteur |
| `vendeurId` | UUID | Vendeur |
| `produitId` | UUID | Produit achetÃ© |
| `prixFinal` | double | Prix payÃ© |
| `statut` | Enum | `EN_ATTENTE_PAIEMENT`, `PAYEE`, `EXPIREE`, `ANNULEE` |
| `dateCommande` | LocalDateTime | Auto |
| `dateExpiration` | LocalDateTime | `dateCommande + 24h` |
| `paiementId` | UUID | FK paiement |

**DTO de sortie `CommandeDTO` :** mÃªmes champs.

---

#### `Paiement` (table `paiements`) â€” product-service
| Champ | Type | Description |
|-------|------|-------------|
| `id` | UUID | PK |
| `commandeId` | UUID | FK commande |
| `montant` | double | Montant payÃ© |
| `methode` | Enum | `CARTE`, `VIREMENT`, `PAYPAL`, `CRYPTO` |
| `statut` | Enum | `EN_COURS`, `CONFIRME`, `ECHOUE`, `REMBOURSE` |
| `reference` | String | UNIQUE â€” format `PAY-YYYYMMDD-NNNNNN` |
| `datePaiement` | LocalDateTime | Auto |
| `dateConfirmation` | LocalDateTime | Mise Ã  jour lors de confirmation |

**`PaiementRequestDTO` (entrÃ©e POST /payer) :**
```json
{ "montant": 130.00, "methode": "CARTE" }
```

**`PaiementConfirmationDTO` (sortie) :**
```json
{
  "paiement": {
    "id": "uuid", "reference": "PAY-20260508-123456",
    "montant": 130.00, "methode": "CARTE",
    "statut": "CONFIRME", "datePaiement": "...", "dateConfirmation": "..."
  },
  "commande": {
    "id": "uuid", "reference": "CMD-20260508-654321",
    "statut": "PAYEE", "prixFinal": 130.00, ...
  }
}
```

---

#### `Commentaire` (table `commentaires`) â€” product-service
| Champ | Type | Description |
|-------|------|-------------|
| `id` | UUID | PK |
| `produitId` | UUID | FK produit |
| `texte` | TEXT | Contenu |
| `note` | int | Note (1â€“5) |
| `datePublication` | LocalDateTime | Auto |
| `auteurId` | UUID | FK utilisateur |

---

#### `Negociation` (table `negociations`) â€” negotiation-service
| Champ | Type | Description |
|-------|------|-------------|
| `id` | UUID | PK |
| `acheteurId` | UUID | Acheteur |
| `produitId` | UUID | Produit nÃ©gociÃ© |
| `rounds` | int | Nombre de rounds jouÃ©s (dÃ©faut 0) |
| `prixInitial` | Double | Prix de dÃ©part |
| `prixFinal` | Double | Prix courant / final |

#### `MessageNegociation` (table `messages_negociation`) â€” negotiation-service
| Champ | Type | Description |
|-------|------|-------------|
| `id` | UUID | PK |
| `negociationId` | UUID | FK nÃ©gociation |
| `sender` | String | `"ACHETEUR"` ou `"AGENT"` |
| `content` | String | Texte du message |
| `price` | double | Prix associÃ© au message |
| `timestamp` | LocalDateTime | Auto |

---

#### `Audit` (table `audits`) â€” audit-service
| Champ | Type | Description |
|-------|------|-------------|
| `id` | UUID | PK |
| `type` | String | Ex: `PRODUCT_CREATE`, `PRODUCT_UPDATE` |
| `severite` | Enum | `INFO`, `WARNING`, `CRITICAL` |
| `message` | String | Description de l'Ã©vÃ©nement |
| `agentSource` | String | Service Ã©metteur (ex: `ProductService`) |

---

## 5. Logique MÃ©tier

### 5.1 Algorithme de NÃ©gociation

L'`AgentNegociation` applique le pipeline suivant Ã  chaque round :

```
INPUT: prixActuel, prixMin, prixPropose, roundActuel, roundsMax, historiqueOffres

GARDE 0 : prixMin invalide (â‰¤0 ou â‰¥ prixActuel - Îµ)  â†’ INVALID_CONFIG, fin
GARDE 1 : roundActuel > roundsMax                     â†’ TIMEOUT, prix=prixMin, fin
GARDE 2 : prixPropose â‰¤ 0                             â†’ INVALID, stable
GARDE 3 : prixPropose < prixMin - Îµ                   â†’ AGGRESSIVE_BUYER, contre=prixMin
GARDE 4 : prixPropose â‰¤ prixMin + Îµ                   â†’ ACCEPTED_AT_FLOOR, fin
GARDE 4b: marge rÃ©siduelle â‰¤ Îµ                        â†’ FLOOR_REACHED, prix=prixMin
GARDE 5 : prixPropose â‰¥ prixActuel                    â†’ ACCEPTED, fin
GARDE 6 : roundActuel = roundsMax                     â†’ offre finale Ã  prixMin, fin

Ã‰TAPE 1 : Calcul des variables fuzzy
  ecart       = (prixActuel - prixPropose) / prixActuel Ã— 100
  progression = roundActuel / roundsMax
  tendance    = (last - secondLast) / prixActuel   (clamped [-1, 1])

Ã‰TAPE 2 : InfÃ©rence fuzzy (jFuzzyLogic + negotiation.fcl)
  â†’ concessionRate âˆˆ [0.0, 0.5]
  (Fallback si FCL indisponible : table statique par tranches d'Ã©cart)

Ã‰TAPE 3 : Bonus de renforcement comportemental
  Pour chaque paire consÃ©cutive dans historiqueOffres :
    delta > 0.1% prixActuel  â†’ +0.05 (acheteur monte)
    delta â‰ˆ 0               â†’ -0.02 (stagnation)
    delta < 0               â†’ -0.04 (acheteur baisse)
  â†’ reinforcementBonus âˆˆ [-0.15, +0.15]

Ã‰TAPE 4 : Bonus de stagnation
  Si â‰¥ 3 offres identiques consÃ©cutives : +0.05 par rÃ©pÃ©tition supplÃ©mentaire
  â†’ stagnationBonus âˆˆ [0.0, 0.20]

Ã‰TAPE 5 : Taux final
  concessionRate = clamp(fuzzy + renforcement + stagnation, 0.01, 0.50)

Ã‰TAPE 6 : Calcul du nouveau prix
  concession = concessionRate Ã— (prixActuel - prixMin)
  candidat   = prixActuel - concession
  Si candidat â‰¤ prixPropose : candidat = (prixActuel + prixPropose) / 2

Ã‰TAPE 7 : Clamp absolu
  nouveauPrix = max(prixMin, max(prixPropose, min(prixActuel, candidat)))

OUTPUT: nouveauPrix, concession, buyerBehavior, buyerTrend, isFinalOffer
```

---

### 5.2 Fichier FCL â€” `negotiation.fcl`

**Variables d'entrÃ©e :**
| Variable | Plage | Termes flous |
|----------|-------|-------------|
| `ecart` | [0, 100] | `petit` (0â€“15), `moyen` (10â€“35), `grand` (30â€“100) |
| `progression` | [0.0, 1.0] | `debut` (0â€“0.4), `milieu` (0.3â€“0.7), `fin` (0.6â€“1.0) |
| `tendance` | [-1.0, 1.0] | `baisse` (-1 Ã  0), `stable` (-0.05 Ã  0.05), `hausse` (0 Ã  1) |

**Variable de sortie :**
| Variable | Plage | Termes flous |
|----------|-------|-------------|
| `concessionRate` | [0.0, 0.5] | `nulle` (0â€“0.05), `faible` (0.03â€“0.15), `moyenne` (0.12â€“0.32), `forte` (0.28â€“0.5) |

**DÃ©fuzzification :** `COG` (Centre of Gravity) â€” DEFAULT = 0.05

**13 rÃ¨gles principales :**
```
R1:  ecart=grand  âˆ§ tendance=baisse  â†’ nulle
R2:  ecart=grand  âˆ§ tendance=stable  â†’ faible
R3:  ecart=grand  âˆ§ tendance=hausse  â†’ faible
R4:  ecart=moyen  âˆ§ tendance=baisse  â†’ faible
R5:  ecart=moyen  âˆ§ tendance=stable  â†’ moyenne
R6:  ecart=moyen  âˆ§ tendance=hausse  â†’ moyenne
R7:  ecart=petit  âˆ§ tendance=baisse  â†’ moyenne
R8:  ecart=petit  âˆ§ tendance=stable  â†’ forte
R9:  ecart=petit  âˆ§ tendance=hausse  â†’ forte
R10: progression=fin                 â†’ forte   (urgence temporelle)
R11: progression=debut âˆ§ ecart=grand â†’ nulle   (tenir ferme au dÃ©but)
R12: progression=milieu âˆ§ ecart=moyenâ†’ moyenne
R13: progression=debut âˆ§ ecart=petit â†’ forte   (clore tÃ´t si proche)
```

**OpÃ©rateurs :** `AND: MIN`, `ACT: MIN`, `ACCU: MAX`

---

### 5.3 Fallback Rate (sans FCL)

```
ecart > 45%  â†’ rate = 0.02
ecart > 30%  â†’ rate = 0.06
ecart > 15%  â†’ rate = 0.18
ecart > 5%   â†’ rate = 0.32
sinon        â†’ rate = 0.45
+ progression > 70% : rate += 0.10 (capped Ã  0.50)
```

---

### 5.4 RÃ¨gles absolues du systÃ¨me

1. **`nouveauPrix â‰¥ prixMin` toujours** (clamp absolu Ã©tape 7)
2. **`nouveauPrix â‰¥ prixPropose`** â€” le vendeur ne descend jamais sous l'offre acheteur
3. **`nouveauPrix â‰¤ prixActuel`** â€” le vendeur ne remonte jamais son prix
4. **prixMin invalide** (`â‰¤ 0` ou `â‰¥ prixActuel - Îµ`) â†’ terminaison immÃ©diate `INVALID_CONFIG`
5. **Timeout** : au-delÃ  de `roundsMax`, le vendeur accepte automatiquement `prixMin`
6. **Paiement possible** uniquement si offre en statut `VALIDEE`
7. **Stock dÃ©crÃ©mentÃ©** Ã  chaque paiement, produit â†’ `VENDU` si stock atteint 0
8. **Commande expire** automatiquement 24h aprÃ¨s crÃ©ation (logique DB, pas de scheduler actif)

---

## 6. Base de DonnÃ©es

### 6.1 Bases PostgreSQL

| Base | SchÃ©ma principal | Service |
|------|-----------------|---------|
| `auramarket_auth` | `utilisateurs`, `vendeurs`, `acheteurs` | auth-service |
| `auramarket_product` | `produits`, `offres`, `commandes`, `paiements`, `commentaires` | product-service |
| `auramarket_negotiation` | `negociations`, `messages_negociation` | negotiation-service |
| `auramarket_audit` | `audits` | audit-service |

**Init :** `microservices/init-db.sql` â€” crÃ©e les 4 bases + tables initiales  
**DDL Auto :** `spring.jpa.hibernate.ddl-auto: update` sur tous les services  
**Seed :** `seed-data.sql`, `seed-nego.sql`, `seed-offers.sql`

### 6.2 Repositories JPA

| Repository | Service | MÃ©thodes custom notables |
|-----------|---------|--------------------------|
| `UtilisateurRepository` | auth | `findByEmail(String)` |
| `ProduitRepository` | product | `findByCategorie(String, Pageable)`, `countProductsByCategory()` (@Query) |
| `OffreRepository` | product | `findByProduitId(UUID)` |
| `CommandeRepository` | product | `findByAcheteurId(UUID)`, `findByVendeurId(UUID)` |
| `PaiementRepository` | product | standard JPA |
| `CommentaireRepository` | product | `findByProduitIdOrderByDatePublicationDesc(UUID)` |
| `NegociationRepository` | negotiation | standard JPA |
| `MessageNegociationRepository` | negotiation | `findByNegociationIdOrderByTimestampAsc(UUID)`, `deleteByNegociationId(UUID)` |
| `AuditRepository` | audit | standard JPA |

---

## 7. Frontend Angular

### 7.1 Configuration

| PropriÃ©tÃ© | Valeur |
|-----------|--------|
| Framework | Angular 18 (standalone components) |
| Port dev | `4200` |
| Base URL API | `http://localhost:8080` (configurable dans `api.config.ts`) |
| ngrok support | Header `ngrok-skip-browser-warning: true` dans tous les services |
| Module de pagination | `ngx-pagination` |

### 7.2 Routes

| Chemin | Composant | Guard |
|--------|-----------|-------|
| `/` | `HomeComponent` | aucun |
| `/login` | `LoginComponent` | aucun |
| `/signup` | `SignupComponent` | aucun |
| `/list-produit` | `ListProduitComponent` | aucun |
| `/produits/:id` | `DetailProduit` | aucun |
| `/cart` | `CartComponent` | aucun |
| `/checkout` | `CheckoutComponent` | `authGuard` |
| `/dashboard` | `DashboardAcheteurComponent` | `authGuard` |
| `/vendeur` | `SellerDashboardComponent` | `authGuard` |
| `/superviseur` | `SupervisorDashboardComponent` | `authGuard` |
| `/commandes` | `MesCommandesComponent` | `authGuard` |
| `/commandes/:id` | `DetailCommandeComponent` | `authGuard` |

**`authGuard`** : vÃ©rifie `AuthService.getToken()`, redirige vers `/login` si absent.

### 7.3 Services Angular

| Service | Fichier | ResponsabilitÃ© |
|---------|---------|----------------|
| `AuthService` | `auth.service.ts` | Login/register, stockage JWT localStorage |
| `ProductService` | `product.service.ts` | CRUD produits, offres, commentaires |
| `NegotiationService` | `negotiation.service.ts` | CRUD nÃ©gociations, appel `/agent/nego/ajuster` |
| `CartService` | `cart.service.ts` | Panier local (BehaviorSubject) |
| `AuditService` | `audit.service.ts` | Lecture des logs d'audit |

**Payload `ajusterNegociation` envoyÃ© par le frontend :**
```typescript
{
  negociationId: nego.id,
  prixActuel:    nego.prixFinal,       // prix courant de la nÃ©gociation
  prixMin:       prixMin,              // vrai prixMin depuis le produit DB
  prixPropose:   prixPropose,          // offre de l'acheteur
  roundActuel:   (nego.rounds || 0) + 1,
  roundsMax:     5,
  historiqueOffres: history            // tableau des offres prÃ©cÃ©dentes
}
```

---

## 8. Infrastructure Docker

```yaml
# docker-compose.yml (rÃ©sumÃ©)
services:
  postgres:          port 5432  â€” PostgreSQL 15-alpine
  pgadmin:           port 5050  â€” admin@auramarket.com / admin
  api-gateway:       port 8080
  auth-service:      port 8081
  product-service:   port 8082
  negotiation-service: port 8083
  audit-service:     port 8084
  agents-bridge:     ports 8085 (REST) + 1099 (JADE RMI)
```

**Variables d'env communes :**
- `SPRING_DATASOURCE_URL`, `SPRING_DATASOURCE_USERNAME`, `SPRING_DATASOURCE_PASSWORD`
- `ML_API_URL` (pour agents-bridge) â†’ par dÃ©faut `http://host.docker.internal:5000`

---

## 9. Ce qui Manque / TODO

### 9.1 FonctionnalitÃ©s incomplÃ¨tes

| # | ProblÃ¨me | Localisation | SÃ©vÃ©ritÃ© |
|---|----------|-------------|----------|
| 1 | **Backdoor password123** non supprimÃ© en prod | `AuthService.java:36` | ðŸ”´ CRITIQUE |
| 2 | **Aucun filtre JWT** sur l'API Gateway â€” les routes ne sont pas protÃ©gÃ©es cÃ´tÃ© backend | `api-gateway/application.yml` | ðŸ”´ CRITIQUE |
| 3 | **Scheduler d'expiration de commandes** absent â€” les commandes ne passent jamais Ã  `EXPIREE` automatiquement | `CommandeService` | ðŸŸ  IMPORTANT |
| 4 | **Scheduler d'expiration d'offres** absent â€” les offres ne passent jamais Ã  `EXPIREE` | `ProductService` | ðŸŸ  IMPORTANT |
| 5 | **ML API non containerisÃ©e** â€” le service Python Flask (`:5000`) n'est pas dans `docker-compose.yml` | `docker-compose.yml` | ðŸŸ  IMPORTANT |
| 6 | **`Audit.timestamp` absent** â€” l'entitÃ© `Audit` n'a pas de champ date/heure | `Audit.java` | ðŸŸ¡ MOYEN |
| 7 | **RÃ´le `SUPERVISEUR` non gÃ©rÃ© Ã  l'inscription** â€” `register()` ne crÃ©e que `VENDEUR` ou `ACHETEUR` | `AuthService.java:52` | ðŸŸ¡ MOYEN |
| 8 | **`prixOffre` nullable sans typage strict** â€” cause des erreurs TypeScript (`possibly undefined`) | `list-produit.ts:46` | ðŸŸ¡ MOYEN |
| 9 | **`Negociation.prixInitial` jamais initialisÃ©e** â€” reste `null` si non fourni | `NegociationService.java` | ðŸŸ¡ MOYEN |
| 10 | **Pas de gestion REJETEE/EXPIREE** des offres cÃ´tÃ© agent | `AgentNegociation` | ðŸŸ¢ MINEUR |

### 9.2 Points d'extension identifiÃ©s

| Extension | Description |
|-----------|-------------|
| **Service ML** | Ajouter le service Flask (`:5000`) au `docker-compose.yml` avec `Dockerfile` dÃ©diÃ© |
| **Eureka / Service Discovery** | Le gateway rÃ©sout les services par nom statique, Ã  remplacer par Eureka |
| **Spring Security sur Gateway** | Valider le JWT au niveau gateway avant de router les requÃªtes |
| **WebSocket** | La nÃ©gociation est actuellement synchrone/polling â€” migrer vers WebSocket pour le temps rÃ©el |
| **Scheduler** | Ajouter `@Scheduled` pour expirer commandes (24h) et offres (dateExpiration) |
| **Notifications** | Aucune notification email/push lors d'acceptation d'offre ou crÃ©ation de commande |
| **Tests** | Aucun test unitaire ou d'intÃ©gration trouvÃ© dans les microservices |
| **Pagination frontend** | La liste de commandes n'a pas de pagination (toutes chargÃ©es d'un coup) |
| **CORS backend** | Actuellement `allowedOrigins: "*"` â€” Ã  restreindre en production |
| **Refresh Token** | JWT sans mÃ©canisme de renouvellement (expiration 24h fixe) |

---

*Documentation gÃ©nÃ©rÃ©e par analyse statique du code source â€” AuraMarket v0.0.1-SNAPSHOT*
