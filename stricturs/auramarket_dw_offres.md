# 🏛️ AuraMarket DW — Modèle Centré sur les Offres

> [!IMPORTANT]
> Dans AuraMarket, **l'offre est l'événement atomique fondamental**. Toute transaction naît d'une offre. Tout ajustement de prix est une nouvelle offre. La confiance de L'Oracle est consultée **avant** de soumettre une offre. Ce modèle place `FAIT_OFFRE` au cœur du DW.

---

## Le Cycle de Vie d'une Offre

```mermaid
stateDiagram-v2
    [*] --> PROPOSEE : Agent soumet une offre
    PROPOSEE --> EN_NEGOCIATION : Contre-offre reçue
    PROPOSEE --> ACCEPTEE : Acceptée directement
    PROPOSEE --> REJETEE : Refusée
    PROPOSEE --> SUSPENDUE : Score confiance trop bas
    EN_NEGOCIATION --> ACCEPTEE : Accord final
    EN_NEGOCIATION --> REJETEE : Échec de négociation
    EN_NEGOCIATION --> EXPIREE : Délai dépassé
    ACCEPTEE --> [*] : → FAIT_TRANSACTION créé
    REJETEE --> [*]
    SUSPENDUE --> PROPOSEE : Oracle score remonté
    EXPIREE --> [*]
```

---

## Architecture Galaxy — L'Offre comme Centre de Gravité

```mermaid
erDiagram
    FAIT_OFFRE {
        int     offre_id              PK
        int     produit_id            FK
        int     vendeur_id            FK
        int     acheteur_id           FK
        int     agent_emetteur_id     FK
        int     date_emission_id      FK
        int     date_expiration_id    FK
        int     marche_id             FK
        int     type_offre_id         FK
        int     score_confiance_id    FK
        string  direction
        float   prix_propose
        float   quantite
        float   valeur_totale
        float   prix_marche_reference
        float   ecart_marche_pct
        string  statut
        boolean circuit_breaker_actif
        string  motif_decision
    }

    FAIT_NEGOCIATION {
        int     negociation_id        PK
        int     offre_id              FK
        int     agent_id              FK
        int     date_id               FK
        int     score_confiance_id    FK
        int     round_numero
        float   prix_contre_propose
        float   delta_vs_offre_initiale_pct
        string  type_action
        string  resultat
    }

    FAIT_TRANSACTION {
        int     transaction_id        PK
        int     offre_id              FK
        int     negociation_id        FK
        int     produit_id            FK
        int     vendeur_id            FK
        int     acheteur_id           FK
        int     date_id               FK
        int     marche_id             FK
        float   prix_execution
        float   quantite
        float   valeur_totale
        float   gain_agent_pct
        float   score_confiance_final
        string  mode_execution
    }

    FAIT_SCORE_CONFIANCE {
        int     score_id              PK
        int     entite_id             FK
        int     source_id             FK
        int     modele_id             FK
        int     date_id               FK
        float   score_veracite
        float   score_sentiment
        float   score_anomalie
        float   score_final
        string  niveau_risque
        boolean alerte_declenchee
    }

    FAIT_ALERTE {
        int     alerte_id             PK
        int     score_id              FK
        int     entite_id             FK
        int     offre_id              FK
        int     superviseur_id        FK
        int     date_id               FK
        string  type_alerte
        string  severite
        string  action_agent
        string  statut
    }

    DIM_OFFRE_TYPE {
        int     type_offre_id         PK
        string  nom
        string  direction
        string  mode_prix
        boolean negociable
        string  strategie_defaut
        int     ttl_secondes
    }

    DIM_PRODUIT {
        int     produit_id     PK
        string  nom
        string  categorie
        string  sous_categorie
        string  marque
        string  plateforme_source
        string  devise
    }

    DIM_VENDEUR {
        int     vendeur_id     PK
        string  nom
        string  plateforme
        string  pays
        string  statut
        float   score_historique_moyen
    }

    DIM_AGENT {
        int     agent_id       PK
        string  nom
        string  type
        string  strategie
        float   seuil_confiance_min
        string  mode_operation
        boolean auto_suspend
    }

    DIM_ENTITE {
        int     entite_id      PK
        string  nom
        string  type
        string  categorie
    }

    DIM_SOURCE_INFO {
        int     source_id      PK
        string  nom
        string  type
        string  plateforme
        float   fiabilite
    }

    DIM_MODELE_NLP {
        int     modele_id      PK
        string  nom
        string  version
        string  tache
        float   precision
    }

    DIM_MARCHE {
        int     marche_id      PK
        string  nom
        string  devise
        string  region
        float   seuil_volatilite
    }

    DIM_SUPERVISEUR {
        int     superviseur_id PK
        string  nom
        string  role
        string  organisation
    }

    DIM_DATE {
        int     date_id        PK
        datetime horodatage
        int     heure
        int     minute
        int     jour
        int     mois
        int     annee
        string  session_marche
        string  fenetre_temps
    }

    FAIT_OFFRE        ||--|| DIM_PRODUIT         : "porte sur"
    FAIT_OFFRE        ||--|| DIM_VENDEUR          : "vendeur"
    FAIT_OFFRE        ||--|| DIM_VENDEUR          : "acheteur"
    FAIT_OFFRE        ||--|| DIM_AGENT            : "émis par"
    FAIT_OFFRE        ||--|| DIM_DATE             : "émise à"
    FAIT_OFFRE        ||--|| DIM_DATE             : "expire à"
    FAIT_OFFRE        ||--|| DIM_MARCHE           : "sur marché"
    FAIT_OFFRE        ||--|| DIM_OFFRE_TYPE       : "type"
    FAIT_OFFRE        ||--|| FAIT_SCORE_CONFIANCE : "vérifié via"

    FAIT_NEGOCIATION  ||--|| FAIT_OFFRE           : "round de négociation"
    FAIT_NEGOCIATION  ||--|| DIM_AGENT            : "agent"
    FAIT_NEGOCIATION  ||--|| DIM_DATE             : "à"
    FAIT_NEGOCIATION  ||--|| FAIT_SCORE_CONFIANCE : "score au moment"

    FAIT_TRANSACTION  ||--|| FAIT_OFFRE           : "conclut"
    FAIT_TRANSACTION  ||--|| FAIT_NEGOCIATION     : "issue de"
    FAIT_TRANSACTION  ||--|| DIM_PRODUIT          : "produit"
    FAIT_TRANSACTION  ||--|| DIM_VENDEUR          : "vendeur"
    FAIT_TRANSACTION  ||--|| DIM_DATE             : "date"
    FAIT_TRANSACTION  ||--|| DIM_MARCHE           : "marché"

    FAIT_SCORE_CONFIANCE ||--|| DIM_ENTITE        : "évalue"
    FAIT_SCORE_CONFIANCE ||--|| DIM_SOURCE_INFO   : "basé sur"
    FAIT_SCORE_CONFIANCE ||--|| DIM_MODELE_NLP    : "calculé par"
    FAIT_SCORE_CONFIANCE ||--|| DIM_DATE          : "à"

    FAIT_ALERTE       ||--|| FAIT_SCORE_CONFIANCE : "déclenchée par"
    FAIT_ALERTE       ||--|| FAIT_OFFRE           : "bloque"
    FAIT_ALERTE       ||--|| DIM_ENTITE           : "entité"
    FAIT_ALERTE       ||--|| DIM_SUPERVISEUR      : "assignée à"
    FAIT_ALERTE       ||--|| DIM_DATE             : "à"
```

---

## Zoom sur la Dimension `DIM_OFFRE_TYPE`

Cette dimension est la clé de voûte de la flexibilité du système. Elle définit le comportement attendu de chaque type d'offre.

```mermaid
classDiagram
    class DIM_OFFRE_TYPE {
        +int    type_offre_id
        +string nom
        +string direction
        +string mode_prix
        +bool   negociable
        +string strategie_defaut
        +int    ttl_secondes
    }

    class Exemples {
        OFFRE_ACHAT_IMMEDIAT: direction=achat, mode_prix=fixe, negociable=false
        OFFRE_VENTE_NEGOCIEE: direction=vente, mode_prix=dynamique, negociable=true
        OFFRE_ENCHÈRE: direction=vente, mode_prix=enchère, negociable=false
        CONTRE_OFFRE: direction=mixte, mode_prix=dynamique, negociable=true
        OFFRE_LIQUIDATION: direction=vente, mode_prix=bradé, negociable=false
    }

    DIM_OFFRE_TYPE --> Exemples : contient
```

---

## Flux de Données par Processus Offre

```mermaid
sequenceDiagram
    participant AG as 🤖 Agent
    participant OR as 🔮 L'Oracle
    participant DW as 🏛️ Data Warehouse
    participant SUP as 👤 Superviseur

    AG->>OR: Requête score(produit, vendeur)
    OR-->>DW: INSERT FAIT_SCORE_CONFIANCE
    OR-->>AG: Score = 0.82 ✅

    AG->>DW: INSERT FAIT_OFFRE (statut=PROPOSEE, score_confiance_id=X)
    DW-->>AG: offre_id = 4421

    Note over AG: Contre-offre reçue du vendeur
    AG->>OR: Re-vérification score
    OR-->>DW: INSERT FAIT_SCORE_CONFIANCE (nouveau snapshot)
    AG->>DW: INSERT FAIT_NEGOCIATION (round=1, prix_contre_propose=...)

    alt Score Oracle tombe < seuil
        OR-->>DW: alerte_declenchee=true
        DW-->>AG: circuit_breaker_actif=true
        AG->>DW: UPDATE FAIT_OFFRE (statut=SUSPENDUE)
        DW-->>SUP: INSERT FAIT_ALERTE
        SUP->>DW: UPDATE FAIT_ALERTE (action=approuver_reprise)
    else Accord trouvé
        AG->>DW: UPDATE FAIT_OFFRE (statut=ACCEPTEE)
        AG->>DW: INSERT FAIT_TRANSACTION (offre_id=4421)
    end
```

---

## Métriques Prioritaires — Tableau de Bord Offres

| Métrique | Calcul SQL simplifié | Valeur métier |
|---|---|---|
| **Taux d'acceptation des offres** | `COUNT(statut=ACCEPTEE) / COUNT(*)` | Performance des agents |
| **Délai moyen de négociation** | `AVG(date_transaction - date_offre)` | Efficacité du marché |
| **Écart prix négocié vs marché** | `AVG(ecart_marche_pct)` | Qualité du dynamic pricing |
| **Offres suspendues par Oracle** | `COUNT(circuit_breaker_actif=true)` | Impact sécurité cognitive |
| **Rounds de négociation moyens** | `AVG(round_numero) par offre` | Complexité des deals |
| **Valeur totale des offres actives** | `SUM(valeur_totale) WHERE statut=PROPOSEE` | Exposition du marché |
| **Taux de conversion offre→transaction** | `COUNT(FAIT_TRANSACTION) / COUNT(FAIT_OFFRE)` | KPI central |

---

## ✅ Résumé de la Hiérarchie des Faits

```mermaid
graph LR
    A[FAIT_OFFRE\n⭐ Table Centrale] --> B[FAIT_NEGOCIATION\nRounds de contre-offre]
    B --> C[FAIT_TRANSACTION\nConclusion du deal]
    A --> D[FAIT_SCORE_CONFIANCE\nOracle consulté avant chaque offre]
    D --> E[FAIT_ALERTE\nSi score critique]
    E --> A
```

> [!IMPORTANT]
> L'offre est la **source de vérité**. Une transaction n'est que le résultat d'une offre acceptée. Un score de confiance n'existe que parce qu'une offre va être émise. Une alerte ne se déclenche que si cette offre est en danger. Tout converge vers et depuis `FAIT_OFFRE`.
