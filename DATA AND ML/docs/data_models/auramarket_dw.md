# 🏛️ AuraMarket — Data Warehouse Design

AuraMarket fuses two complex systems: a **Multi-Agent Marketplace** (transactions, dynamic pricing, autonomous agents) and a **Cognitive Engine — L'Oracle** (NLP, disinformation detection, trust scores). The DW must serve both.

---

## 🔍 Key Business Processes → Fact Tables

| Business Process | Fact Table | Grain |
|---|---|---|
| Agent executes a transaction | `FAIT_TRANSACTION` | 1 row = 1 buy/sell |
| Agent places/adjusts price offer | `FAIT_OFFRE_PRIX` | 1 row = 1 price offer event |
| Oracle computes a trust score | `FAIT_SCORE_CONFIANCE` | 1 row = 1 score snapshot |
| Oracle ingests an info item | `FAIT_FLUX_INFORMATION` | 1 row = 1 article/tweet/post |
| Oracle raises an alert | `FAIT_ALERTE` | 1 row = 1 alert event |

---

## Option 1 — ⭐ Star Schema: Transaction Analytics Hub

Focus on the core marketplace — agent transactions and price decisions, with flat dimensions.

```mermaid
erDiagram
    FAIT_TRANSACTION {
        int     transaction_id        PK
        int     dim_produit_id        FK
        int     dim_vendeur_id        FK
        int     dim_acheteur_id       FK
        int     dim_agent_id          FK
        int     dim_date_id           FK
        int     dim_marche_id         FK
        float   prix_initial
        float   prix_final_negocie
        float   quantite
        float   score_confiance_active
        string  statut
        string  strategie_agent
        float   savings_pct
    }

    DIM_PRODUIT {
        int     produit_id     PK
        string  nom
        string  categorie
        string  sous_categorie
        string  marque
        string  source_plateforme
    }

    DIM_VENDEUR {
        int     vendeur_id     PK
        string  nom_vendeur
        string  plateforme
        string  pays
        float   score_moyen_historique
        string  statut
    }

    DIM_AGENT {
        int     agent_id       PK
        string  nom_agent
        string  type_agent
        string  strategie_defaut
        float   seuil_confiance_min
    }

    DIM_DATE {
        int     date_id        PK
        datetime horodatage
        int     heure
        int     jour
        int     mois
        int     annee
        string  jour_semaine
        string  session_marche
    }

    DIM_MARCHE {
        int     marche_id      PK
        string  nom
        string  devise
        string  region
        string  type_marche
    }

    FAIT_TRANSACTION ||--|| DIM_PRODUIT  : "concerne"
    FAIT_TRANSACTION ||--|| DIM_VENDEUR  : "vendu par"
    FAIT_TRANSACTION ||--|| DIM_VENDEUR  : "acheté par"
    FAIT_TRANSACTION ||--|| DIM_AGENT    : "piloté par"
    FAIT_TRANSACTION ||--|| DIM_DATE     : "à"
    FAIT_TRANSACTION ||--|| DIM_MARCHE   : "sur"
```

> [!TIP]
> **Usage :** Tableaux de bord de volume transactionnel, marge négociée par agent, taux d'exécution par marché.

---

## Option 2 — ❄️ Snowflake Schema: Cognitive Scoring Layer

Models the Oracle's trust score pipeline with normalized hierarchies for sources, semantic content, and temporal analysis.

```mermaid
erDiagram
    FAIT_SCORE_CONFIANCE {
        int     score_id           PK
        int     dim_entite_id      FK
        int     dim_source_id      FK
        int     dim_date_id        FK
        int     dim_modele_id      FK
        float   score_veracite
        float   score_sentiment
        float   score_anomalie
        float   score_final
        string  niveau_risque
        boolean alerte_declenchee
    }

    FAIT_FLUX_INFORMATION {
        int     flux_id            PK
        int     dim_source_id      FK
        int     dim_date_id        FK
        int     dim_entite_id      FK
        string  contenu_resume
        string  langue
        float   sentiment_score
        float   anomalie_score
        boolean est_desinformation
        string  url
    }

    DIM_ENTITE {
        int     entite_id      PK
        string  nom
        string  type_entite
        int     categorie_id   FK
    }

    DIM_CATEGORIE_ENTITE {
        int     categorie_id   PK
        string  nom
        int     super_cat_id   FK
    }

    DIM_SUPER_CATEGORIE {
        int     super_cat_id   PK
        string  nom
        string  domaine
    }

    DIM_SOURCE_INFO {
        int     source_id      PK
        string  nom_source
        string  type_source
        int     plateforme_id  FK
        float   fiabilite_source
    }

    DIM_PLATEFORME {
        int     plateforme_id  PK
        string  nom
        string  type
        string  url_base
        string  pays
    }

    DIM_MODELE_NLP {
        int     modele_id      PK
        string  nom_modele
        string  version
        string  algorithme
        string  tache
        date    date_entrainement
        float   precision_validation
    }

    DIM_DATE {
        int     date_id        PK
        datetime horodatage
        int     heure
        int     jour
        int     mois
        int     annee
        string  fenetre_temps
    }

    FAIT_SCORE_CONFIANCE  ||--|| DIM_ENTITE         : "évalue"
    FAIT_SCORE_CONFIANCE  ||--|| DIM_SOURCE_INFO     : "basé sur"
    FAIT_SCORE_CONFIANCE  ||--|| DIM_DATE            : "calculé à"
    FAIT_SCORE_CONFIANCE  ||--|| DIM_MODELE_NLP      : "généré par"
    FAIT_FLUX_INFORMATION ||--|| DIM_SOURCE_INFO     : "provient de"
    FAIT_FLUX_INFORMATION ||--|| DIM_DATE            : "capturé à"
    FAIT_FLUX_INFORMATION ||--|| DIM_ENTITE          : "concerne"
    DIM_ENTITE            ||--|| DIM_CATEGORIE_ENTITE : "classé"
    DIM_CATEGORIE_ENTITE  ||--|| DIM_SUPER_CATEGORIE : "appartient"
    DIM_SOURCE_INFO       ||--|| DIM_PLATEFORME      : "hébergé sur"
```

> [!TIP]
> **Usage :** Évolution du score de confiance d'un vendeur dans le temps, détection de campagnes de désinformation coordonnées, audit d'un modèle NLP.

---

## Option 3 — 🌌 Galaxy / Constellation Schema (Architecture Complète AuraMarket)

The full model — all five fact tables sharing dimensions. This is the **production-grade DW** for AuraMarket.

```mermaid
erDiagram
    FAIT_TRANSACTION {
        int     transaction_id       PK
        int     produit_id           FK
        int     vendeur_id           FK
        int     acheteur_id          FK
        int     agent_id             FK
        int     date_id              FK
        int     marche_id            FK
        float   prix_initial
        float   prix_final
        float   quantite
        float   score_confiance_t0
        string  statut
    }

    FAIT_OFFRE_PRIX {
        int     offre_id             PK
        int     produit_id           FK
        int     vendeur_id           FK
        int     agent_id             FK
        int     date_id              FK
        float   prix_propose
        float   prix_precedent
        float   delta_pct
        string  motif_ajustement
        float   score_confiance_t0
        string  decision_agent
    }

    FAIT_SCORE_CONFIANCE {
        int     score_id             PK
        int     entite_id            FK
        int     source_id            FK
        int     modele_id            FK
        int     date_id              FK
        float   score_veracite
        float   score_sentiment
        float   score_final
        string  niveau_risque
        boolean alerte_declenchee
    }

    FAIT_FLUX_INFORMATION {
        int     flux_id              PK
        int     source_id            FK
        int     entite_id            FK
        int     date_id              FK
        float   sentiment_score
        float   anomalie_score
        boolean est_desinformation
        string  langue
    }

    FAIT_ALERTE {
        int     alerte_id            PK
        int     entite_id            FK
        int     superviseur_id       FK
        int     date_id              FK
        int     score_id             FK
        string  type_alerte
        string  severite
        string  statut_traitement
        string  action_prise
        datetime date_resolution
    }

    DIM_PRODUIT {
        int     produit_id     PK
        string  nom
        string  categorie
        string  marque
        string  plateforme_source
    }

    DIM_VENDEUR {
        int     vendeur_id     PK
        string  nom
        string  plateforme
        string  pays
        string  statut
    }

    DIM_AGENT {
        int     agent_id       PK
        string  nom
        string  type
        string  strategie
        float   seuil_confiance
        string  mode_operation
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

    DIM_SUPERVISEUR {
        int     superviseur_id PK
        string  nom
        string  role
        string  organisation
    }

    DIM_MARCHE {
        int     marche_id      PK
        string  nom
        string  devise
        string  region
    }

    DIM_DATE {
        int     date_id        PK
        datetime horodatage
        int     heure
        int     jour
        int     mois
        int     annee
        string  fenetre_temps
        string  session_marche
    }

    FAIT_TRANSACTION     ||--|| DIM_PRODUIT      : "produit"
    FAIT_TRANSACTION     ||--|| DIM_VENDEUR      : "vendeur"
    FAIT_TRANSACTION     ||--|| DIM_AGENT        : "agent"
    FAIT_TRANSACTION     ||--|| DIM_DATE         : "date"
    FAIT_TRANSACTION     ||--|| DIM_MARCHE       : "marché"

    FAIT_OFFRE_PRIX      ||--|| DIM_PRODUIT      : "produit"
    FAIT_OFFRE_PRIX      ||--|| DIM_VENDEUR      : "vendeur"
    FAIT_OFFRE_PRIX      ||--|| DIM_AGENT        : "agent"
    FAIT_OFFRE_PRIX      ||--|| DIM_DATE         : "date"

    FAIT_SCORE_CONFIANCE ||--|| DIM_ENTITE       : "entité évaluée"
    FAIT_SCORE_CONFIANCE ||--|| DIM_SOURCE_INFO  : "source"
    FAIT_SCORE_CONFIANCE ||--|| DIM_MODELE_NLP   : "modèle"
    FAIT_SCORE_CONFIANCE ||--|| DIM_DATE         : "date"

    FAIT_FLUX_INFORMATION ||--|| DIM_SOURCE_INFO : "source"
    FAIT_FLUX_INFORMATION ||--|| DIM_ENTITE      : "entité"
    FAIT_FLUX_INFORMATION ||--|| DIM_DATE        : "date"

    FAIT_ALERTE          ||--|| DIM_ENTITE       : "entité"
    FAIT_ALERTE          ||--|| DIM_SUPERVISEUR  : "superviseur"
    FAIT_ALERTE          ||--|| DIM_DATE         : "date"
    FAIT_ALERTE          ||--|| FAIT_SCORE_CONFIANCE : "déclenchée par"
```

> [!IMPORTANT]
> **Cette architecture est la cible finale pour AuraMarket.** Elle permet de répondre aux exigences du projet : relier chaque décision d'agent à un score de confiance, tracer l'origine informationnelle de chaque alerte, et fournir un historique complet pour les tableaux de bord superviseurs.

---

## Architecture en Couches (Vue Globale)

```mermaid
graph TD
    subgraph SOURCES["🌐 Sources de Données"]
        A1[Amazon / Jumia / Avito\nJSON Scrapers]
        A2[Twitter / Reddit / Forums\nAPI Streams]
        A3[Sites d'actualités\nRSS / Crawlers]
        A4[Agents MAS\nÉvénements internes]
    end

    subgraph STAGING["📥 Couche Staging (Brut)"]
        B1[STG_PRODUITS]
        B2[STG_FLUX_TEXTE]
        B3[STG_TRANSACTIONS]
        B4[STG_SCORES_NLP]
    end

    subgraph ODS["🔄 ODS — Operational Data Store"]
        C1[Nettoyage & Déduplication]
        C2[Normalisation des prix & monnaies]
        C3[Enrichissement NLP\nSentiment / Anomalie]
        C4[Calcul Score de Confiance]
    end

    subgraph DW["🏛️ Data Warehouse — Schéma en Constellation"]
        D1[FAIT_TRANSACTION]
        D2[FAIT_OFFRE_PRIX]
        D3[FAIT_SCORE_CONFIANCE]
        D4[FAIT_FLUX_INFORMATION]
        D5[FAIT_ALERTE]
        D6[DIM_PRODUIT / DIM_VENDEUR\nDIM_AGENT / DIM_DATE\nDIM_SOURCE / DIM_MARCHE]
    end

    subgraph DM["📊 Data Marts"]
        E1[Mart Superviseurs\nAlertes & Traçabilité]
        E2[Mart Agents\nPerformance & Stratégie]
        E3[Mart Oracle\nScores & Désinformation]
    end

    subgraph VIZ["📈 Reporting & Dashboards"]
        F1[Power BI / Metabase\nTableau de bord temps réel]
        F2[Alertes Automatiques\nEmail / Slack]
    end

    SOURCES --> STAGING
    STAGING --> ODS
    ODS --> DW
    DW --> DM
    DM --> VIZ
```

---

## Métriques Clés par Tableau de Bord

### Pour les Superviseurs
| Métrique | Source |
|---|---|
| Score de confiance moyen par vendeur | `FAIT_SCORE_CONFIANCE` |
| Nombre d'alertes actives / résolues | `FAIT_ALERTE` |
| Historique des contenus suspects | `FAIT_FLUX_INFORMATION` |
| Décisions d'agents influencées par Oracle | `FAIT_TRANSACTION.score_confiance_t0` |

### Pour les Agents
| Métrique | Source |
|---|---|
| Volume de transactions par agent | `FAIT_TRANSACTION` |
| Prix moyen négocié vs prix initial | `FAIT_OFFRE_PRIX` |
| Taux de suspension (score trop bas) | `FAIT_OFFRE_PRIX.decision_agent` |
| Économies générées par Dynamic Pricing | `FAIT_OFFRE_PRIX.delta_pct` |

### Pour L'Oracle
| Métrique | Source |
|---|---|
| Distribution des scores de sentiment | `FAIT_FLUX_INFORMATION` |
| Précision des modèles NLP | `DIM_MODELE_NLP` |
| Détection de campagnes coordonnées | `FAIT_FLUX_INFORMATION.est_desinformation` |
| Évolution du score d'une marque dans le temps | `FAIT_SCORE_CONFIANCE` (time-series) |

---

## ✅ Recommandation Finale

> [!IMPORTANT]
> Adoptez l'**Option 3 — Architecture Galaxy** comme modèle cible. Ce n'est pas seulement un choix académique : la séparation en 5 tables de faits reflète exactement les 5 processus métiers d'AuraMarket. La dimension `DIM_DATE` avec `horodatage` (datetime) supporte l'analyse en temps quasi-réel. Implémentez d'abord `FAIT_TRANSACTION` + `FAIT_SCORE_CONFIANCE` pour votre MVP, puis ajoutez les autres tables progressivement via votre pipeline Pentaho/Talend.
