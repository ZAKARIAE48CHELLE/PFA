# AuraMarket — Schéma Simplifié (Star Schema)

## Schéma en Étoile — Centré sur les Offres

```mermaid
erDiagram
    FAIT_OFFRE {
        int     offre_id          PK
        int     produit_id        FK
        int     vendeur_id        FK
        int     agent_id          FK
        int     marche_id         FK
        int     date_id           FK
        int     type_offre_id     FK
        float   prix_propose
        float   prix_final
        float   quantite
        float   score_confiance
        string  statut
        string  direction
    }

    DIM_PRODUIT {
        int     produit_id   PK
        string  nom
        string  categorie
        string  marque
        string  plateforme
    }

    DIM_VENDEUR {
        int     vendeur_id   PK
        string  nom
        string  plateforme
        string  pays
        float   score_moyen
    }

    DIM_AGENT {
        int     agent_id     PK
        string  nom
        string  type
        string  strategie
        float   seuil_confiance
    }

    DIM_MARCHE {
        int     marche_id    PK
        string  nom
        string  devise
        string  region
    }

    DIM_DATE {
        int     date_id      PK
        datetime horodatage
        int     jour
        int     mois
        int     annee
        string  session
    }

    DIM_TYPE_OFFRE {
        int     type_offre_id  PK
        string  nom
        string  direction
        boolean negociable
        int     ttl_secondes
    }

    FAIT_OFFRE ||--|| DIM_PRODUIT    : "porte sur"
    FAIT_OFFRE ||--|| DIM_VENDEUR    : "par vendeur"
    FAIT_OFFRE ||--|| DIM_AGENT      : "pilotée par"
    FAIT_OFFRE ||--|| DIM_MARCHE     : "sur"
    FAIT_OFFRE ||--|| DIM_DATE       : "émise le"
    FAIT_OFFRE ||--|| DIM_TYPE_OFFRE : "de type"
```

---

## Statuts possibles d'une offre

```mermaid
stateDiagram-v2
    [*] --> PROPOSEE
    PROPOSEE --> ACCEPTEE
    PROPOSEE --> REJETEE
    PROPOSEE --> SUSPENDUE : Score Oracle trop bas
    SUSPENDUE --> PROPOSEE : Score remonté
    ACCEPTEE --> [*]
    REJETEE --> [*]
```

---

## Métriques principales

| Métrique | Description |
|---|---|
| `score_confiance` | Score Oracle au moment de l'offre |
| `prix_final / prix_propose` | Taux de négociation |
| `statut` | Taux conversion offre → acceptée |
| `direction` | Ratio achat / vente par agent |
