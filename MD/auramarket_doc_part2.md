# AuraMarket — Documentation Technique Complète (Partie 2/2)

---

## 4. Modèles de données

### 4.1 Entités JPA

#### `Utilisateur` (base : `utilisateurs`) — auth-service
| Champ | Type | Contrainte |
|-------|------|-----------|
| `id` | UUID | PK, auto-généré |
| `email` | String | UNIQUE, NOT NULL |
| `mdpHash` | String | NOT NULL (BCrypt) |
| `role` | Enum | `ACHETEUR`, `VENDEUR`, `SUPERVISEUR` |

**Héritage :** `InheritanceType.JOINED`
- **`Vendeur`** (table `vendeurs`) : + `scoreReputation` (float, défaut 5.0)
- **`Acheteur`** (table `acheteurs`) : + `historique` (List\<String\>, `@ElementCollection`)

---

#### `Produit` (table `produits`) — product-service
| Champ | Type | Description |
|-------|------|-------------|
| `id` | UUID | PK |
| `titre` | String | Nom du produit |
| `description` | TEXT | Description longue |
| `prix` | double | Prix de vente affiché |
| `prixMin` | double | Prix plancher de négociation |
| `prixOffre` | Double | Prix d'offre spéciale (nullable) |
| `categorie` | String | Catégorie libre |
| `imageUrl` | TEXT | URL de l'image |
| `stock` | int | Quantité disponible |
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

#### `Offre` (table `offres`) — product-service
| Champ | Type | Description |
|-------|------|-------------|
| `id` | UUID | PK |
| `titre` | String | Libellé de l'offre |
| `description` | String | Description |
| `prixPropose` | double | Prix proposé par l'acheteur |
| `prixFinal` | double | Prix final accepté |
| `statut` | Enum | `EN_ATTENTE`, `VALIDEE`, `REJETEE`, `EXPIREE` |
| `dateCreation` | LocalDateTime | Auto |
| `dateExpiration` | LocalDateTime | Date limite de validité |
| `dateDebut` | LocalDateTime | Début de période d'offre |
| `dateFin` | LocalDateTime | Fin de période d'offre |
| `produitId` | UUID | FK produit |
| `acheteurId` | UUID | FK acheteur |
| `agentGenere` | boolean | `true` si générée par AgentOffre |
| `pourcentageDiscount` | double | % de remise |

---

#### `Commande` (table `commandes`) — product-service
| Champ | Type | Description |
|-------|------|-------------|
| `id` | UUID | PK |
| `reference` | String | UNIQUE — format `CMD-YYYYMMDD-NNNNNN` |
| `offreId` | UUID | Offre source |
| `acheteurId` | UUID | Acheteur |
| `vendeurId` | UUID | Vendeur |
| `produitId` | UUID | Produit acheté |
| `prixFinal` | double | Prix payé |
| `statut` | Enum | `EN_ATTENTE_PAIEMENT`, `PAYEE`, `EXPIREE`, `ANNULEE` |
| `dateCommande` | LocalDateTime | Auto |
| `dateExpiration` | LocalDateTime | `dateCommande + 24h` |
| `paiementId` | UUID | FK paiement |

**DTO de sortie `CommandeDTO` :** mêmes champs.

---

#### `Paiement` (table `paiements`) — product-service
| Champ | Type | Description |
|-------|------|-------------|
| `id` | UUID | PK |
| `commandeId` | UUID | FK commande |
| `montant` | double | Montant payé |
| `methode` | Enum | `CARTE`, `VIREMENT`, `PAYPAL`, `CRYPTO` |
| `statut` | Enum | `EN_COURS`, `CONFIRME`, `ECHOUE`, `REMBOURSE` |
| `reference` | String | UNIQUE — format `PAY-YYYYMMDD-NNNNNN` |
| `datePaiement` | LocalDateTime | Auto |
| `dateConfirmation` | LocalDateTime | Mise à jour lors de confirmation |

**`PaiementRequestDTO` (entrée POST /payer) :**
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

#### `Commentaire` (table `commentaires`) — product-service
| Champ | Type | Description |
|-------|------|-------------|
| `id` | UUID | PK |
| `produitId` | UUID | FK produit |
| `texte` | TEXT | Contenu |
| `note` | int | Note (1–5) |
| `datePublication` | LocalDateTime | Auto |
| `auteurId` | UUID | FK utilisateur |

---

#### `Negociation` (table `negociations`) — negotiation-service
| Champ | Type | Description |
|-------|------|-------------|
| `id` | UUID | PK |
| `acheteurId` | UUID | Acheteur |
| `produitId` | UUID | Produit négocié |
| `rounds` | int | Nombre de rounds joués (défaut 0) |
| `prixInitial` | Double | Prix de départ |
| `prixFinal` | Double | Prix courant / final |

#### `MessageNegociation` (table `messages_negociation`) — negotiation-service
| Champ | Type | Description |
|-------|------|-------------|
| `id` | UUID | PK |
| `negociationId` | UUID | FK négociation |
| `sender` | String | `"ACHETEUR"` ou `"AGENT"` |
| `content` | String | Texte du message |
| `price` | double | Prix associé au message |
| `timestamp` | LocalDateTime | Auto |

---

#### `Audit` (table `audits`) — audit-service
| Champ | Type | Description |
|-------|------|-------------|
| `id` | UUID | PK |
| `type` | String | Ex: `PRODUCT_CREATE`, `PRODUCT_UPDATE` |
| `severite` | Enum | `INFO`, `WARNING`, `CRITICAL` |
| `message` | String | Description de l'événement |
| `agentSource` | String | Service émetteur (ex: `ProductService`) |

---

## 5. Logique Métier

### 5.1 Algorithme de Négociation

L'`AgentNegociation` applique le pipeline suivant à chaque round :

```
INPUT: prixActuel, prixMin, prixPropose, roundActuel, roundsMax, historiqueOffres

GARDE 0 : prixMin invalide (≤0 ou ≥ prixActuel - ε)  → INVALID_CONFIG, fin
GARDE 1 : roundActuel > roundsMax                     → TIMEOUT, prix=prixMin, fin
GARDE 2 : prixPropose ≤ 0                             → INVALID, stable
GARDE 3 : prixPropose < prixMin - ε                   → AGGRESSIVE_BUYER, contre=prixMin
GARDE 4 : prixPropose ≤ prixMin + ε                   → ACCEPTED_AT_FLOOR, fin
GARDE 4b: marge résiduelle ≤ ε                        → FLOOR_REACHED, prix=prixMin
GARDE 5 : prixPropose ≥ prixActuel                    → ACCEPTED, fin
GARDE 6 : roundActuel = roundsMax                     → offre finale à prixMin, fin

ÉTAPE 1 : Calcul des variables fuzzy
  ecart       = (prixActuel - prixPropose) / prixActuel × 100
  progression = roundActuel / roundsMax
  tendance    = (last - secondLast) / prixActuel   (clamped [-1, 1])

ÉTAPE 2 : Inférence fuzzy (jFuzzyLogic + negotiation.fcl)
  → concessionRate ∈ [0.0, 0.5]
  (Fallback si FCL indisponible : table statique par tranches d'écart)

ÉTAPE 3 : Bonus de renforcement comportemental
  Pour chaque paire consécutive dans historiqueOffres :
    delta > 0.1% prixActuel  → +0.05 (acheteur monte)
    delta ≈ 0               → -0.02 (stagnation)
    delta < 0               → -0.04 (acheteur baisse)
  → reinforcementBonus ∈ [-0.15, +0.15]

ÉTAPE 4 : Bonus de stagnation
  Si ≥ 3 offres identiques consécutives : +0.05 par répétition supplémentaire
  → stagnationBonus ∈ [0.0, 0.20]

ÉTAPE 5 : Taux final
  concessionRate = clamp(fuzzy + renforcement + stagnation, 0.01, 0.50)

ÉTAPE 6 : Calcul du nouveau prix
  concession = concessionRate × (prixActuel - prixMin)
  candidat   = prixActuel - concession
  Si candidat ≤ prixPropose : candidat = (prixActuel + prixPropose) / 2

ÉTAPE 7 : Clamp absolu
  nouveauPrix = max(prixMin, max(prixPropose, min(prixActuel, candidat)))

OUTPUT: nouveauPrix, concession, buyerBehavior, buyerTrend, isFinalOffer
```

---

### 5.2 Fichier FCL — `negotiation.fcl`

**Variables d'entrée :**
| Variable | Plage | Termes flous |
|----------|-------|-------------|
| `ecart` | [0, 100] | `petit` (0–15), `moyen` (10–35), `grand` (30–100) |
| `progression` | [0.0, 1.0] | `debut` (0–0.4), `milieu` (0.3–0.7), `fin` (0.6–1.0) |
| `tendance` | [-1.0, 1.0] | `baisse` (-1 à 0), `stable` (-0.05 à 0.05), `hausse` (0 à 1) |

**Variable de sortie :**
| Variable | Plage | Termes flous |
|----------|-------|-------------|
| `concessionRate` | [0.0, 0.5] | `nulle` (0–0.05), `faible` (0.03–0.15), `moyenne` (0.12–0.32), `forte` (0.28–0.5) |

**Défuzzification :** `COG` (Centre of Gravity) — DEFAULT = 0.05

**13 règles principales :**
```
R1:  ecart=grand  ∧ tendance=baisse  → nulle
R2:  ecart=grand  ∧ tendance=stable  → faible
R3:  ecart=grand  ∧ tendance=hausse  → faible
R4:  ecart=moyen  ∧ tendance=baisse  → faible
R5:  ecart=moyen  ∧ tendance=stable  → moyenne
R6:  ecart=moyen  ∧ tendance=hausse  → moyenne
R7:  ecart=petit  ∧ tendance=baisse  → moyenne
R8:  ecart=petit  ∧ tendance=stable  → forte
R9:  ecart=petit  ∧ tendance=hausse  → forte
R10: progression=fin                 → forte   (urgence temporelle)
R11: progression=debut ∧ ecart=grand → nulle   (tenir ferme au début)
R12: progression=milieu ∧ ecart=moyen→ moyenne
R13: progression=debut ∧ ecart=petit → forte   (clore tôt si proche)
```

**Opérateurs :** `AND: MIN`, `ACT: MIN`, `ACCU: MAX`

---

### 5.3 Fallback Rate (sans FCL)

```
ecart > 45%  → rate = 0.02
ecart > 30%  → rate = 0.06
ecart > 15%  → rate = 0.18
ecart > 5%   → rate = 0.32
sinon        → rate = 0.45
+ progression > 70% : rate += 0.10 (capped à 0.50)
```

---

### 5.4 Règles absolues du système

1. **`nouveauPrix ≥ prixMin` toujours** (clamp absolu étape 7)
2. **`nouveauPrix ≥ prixPropose`** — le vendeur ne descend jamais sous l'offre acheteur
3. **`nouveauPrix ≤ prixActuel`** — le vendeur ne remonte jamais son prix
4. **prixMin invalide** (`≤ 0` ou `≥ prixActuel - ε`) → terminaison immédiate `INVALID_CONFIG`
5. **Timeout** : au-delà de `roundsMax`, le vendeur accepte automatiquement `prixMin`
6. **Paiement possible** uniquement si offre en statut `VALIDEE`
7. **Stock décrémenté** à chaque paiement, produit → `VENDU` si stock atteint 0
8. **Commande expire** automatiquement 24h après création (logique DB, pas de scheduler actif)

---

## 6. Base de Données

### 6.1 Bases PostgreSQL

| Base | Schéma principal | Service |
|------|-----------------|---------|
| `auramarket_auth` | `utilisateurs`, `vendeurs`, `acheteurs` | auth-service |
| `auramarket_product` | `produits`, `offres`, `commandes`, `paiements`, `commentaires` | product-service |
| `auramarket_negotiation` | `negociations`, `messages_negociation` | negotiation-service |
| `auramarket_audit` | `audits` | audit-service |

**Init :** `microservices/init-db.sql` — crée les 4 bases + tables initiales  
**DDL Auto :** `spring.jpa.hibernate.ddl-auto: update` sur tous les services  
**Seed :** `seed-data.sql`, `seed-nego.sql`, `seed-offers.sql`

### 6.2 Repositories JPA

| Repository | Service | Méthodes custom notables |
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

| Propriété | Valeur |
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

**`authGuard`** : vérifie `AuthService.getToken()`, redirige vers `/login` si absent.

### 7.3 Services Angular

| Service | Fichier | Responsabilité |
|---------|---------|----------------|
| `AuthService` | `auth.service.ts` | Login/register, stockage JWT localStorage |
| `ProductService` | `product.service.ts` | CRUD produits, offres, commentaires |
| `NegotiationService` | `negotiation.service.ts` | CRUD négociations, appel `/agent/nego/ajuster` |
| `CartService` | `cart.service.ts` | Panier local (BehaviorSubject) |
| `AuditService` | `audit.service.ts` | Lecture des logs d'audit |

**Payload `ajusterNegociation` envoyé par le frontend :**
```typescript
{
  negociationId: nego.id,
  prixActuel:    nego.prixFinal,       // prix courant de la négociation
  prixMin:       prixMin,              // vrai prixMin depuis le produit DB
  prixPropose:   prixPropose,          // offre de l'acheteur
  roundActuel:   (nego.rounds || 0) + 1,
  roundsMax:     5,
  historiqueOffres: history            // tableau des offres précédentes
}
```

---

## 8. Infrastructure Docker

```yaml
# docker-compose.yml (résumé)
services:
  postgres:          port 5432  — PostgreSQL 15-alpine
  pgadmin:           port 5050  — admin@auramarket.com / admin
  api-gateway:       port 8080
  auth-service:      port 8081
  product-service:   port 8082
  negotiation-service: port 8083
  audit-service:     port 8084
  agents-bridge:     ports 8085 (REST) + 1099 (JADE RMI)
```

**Variables d'env communes :**
- `SPRING_DATASOURCE_URL`, `SPRING_DATASOURCE_USERNAME`, `SPRING_DATASOURCE_PASSWORD`
- `ML_API_URL` (pour agents-bridge) → par défaut `http://host.docker.internal:5000`

---

## 9. Ce qui Manque / TODO

### 9.1 Fonctionnalités incomplètes

| # | Problème | Localisation | Sévérité |
|---|----------|-------------|----------|
| 1 | **Backdoor password123** non supprimé en prod | `AuthService.java:36` | 🔴 CRITIQUE |
| 2 | **Aucun filtre JWT** sur l'API Gateway — les routes ne sont pas protégées côté backend | `api-gateway/application.yml` | 🔴 CRITIQUE |
| 3 | **Scheduler d'expiration de commandes** absent — les commandes ne passent jamais à `EXPIREE` automatiquement | `CommandeService` | 🟠 IMPORTANT |
| 4 | **Scheduler d'expiration d'offres** absent — les offres ne passent jamais à `EXPIREE` | `ProductService` | 🟠 IMPORTANT |
| 5 | **ML API non containerisée** — le service Python Flask (`:5000`) n'est pas dans `docker-compose.yml` | `docker-compose.yml` | 🟠 IMPORTANT |
| 6 | **`Audit.timestamp` absent** — l'entité `Audit` n'a pas de champ date/heure | `Audit.java` | 🟡 MOYEN |
| 7 | **Rôle `SUPERVISEUR` non géré à l'inscription** — `register()` ne crée que `VENDEUR` ou `ACHETEUR` | `AuthService.java:52` | 🟡 MOYEN |
| 8 | **`prixOffre` nullable sans typage strict** — cause des erreurs TypeScript (`possibly undefined`) | `list-produit.ts:46` | 🟡 MOYEN |
| 9 | **`Negociation.prixInitial` jamais initialisée** — reste `null` si non fourni | `NegociationService.java` | 🟡 MOYEN |
| 10 | **Pas de gestion REJETEE/EXPIREE** des offres côté agent | `AgentNegociation` | 🟢 MINEUR |

### 9.2 Points d'extension identifiés

| Extension | Description |
|-----------|-------------|
| **Service ML** | Ajouter le service Flask (`:5000`) au `docker-compose.yml` avec `Dockerfile` dédié |
| **Eureka / Service Discovery** | Le gateway résout les services par nom statique, à remplacer par Eureka |
| **Spring Security sur Gateway** | Valider le JWT au niveau gateway avant de router les requêtes |
| **WebSocket** | La négociation est actuellement synchrone/polling — migrer vers WebSocket pour le temps réel |
| **Scheduler** | Ajouter `@Scheduled` pour expirer commandes (24h) et offres (dateExpiration) |
| **Notifications** | Aucune notification email/push lors d'acceptation d'offre ou création de commande |
| **Tests** | Aucun test unitaire ou d'intégration trouvé dans les microservices |
| **Pagination frontend** | La liste de commandes n'a pas de pagination (toutes chargées d'un coup) |
| **CORS backend** | Actuellement `allowedOrigins: "*"` — à restreindre en production |
| **Refresh Token** | JWT sans mécanisme de renouvellement (expiration 24h fixe) |

---

*Documentation générée par analyse statique du code source — AuraMarket v0.0.1-SNAPSHOT*
