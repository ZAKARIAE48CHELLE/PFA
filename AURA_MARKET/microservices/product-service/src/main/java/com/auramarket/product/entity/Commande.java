package com.auramarket.product.entity;

import jakarta.persistence.*;
import java.time.LocalDateTime;
import java.util.UUID;

@Entity
@Table(name = "commandes")
public class Commande {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @Column(unique = true, nullable = false)
    private String reference;

    private UUID offreId;
    private UUID acheteurId;
    private UUID vendeurId;
    private UUID produitId;
    private double prixFinal;

    @Enumerated(EnumType.STRING)
    private StatutCommande statut;

    private LocalDateTime dateCommande;
    private LocalDateTime dateExpiration;
    private UUID paiementId;

    public enum StatutCommande {
        EN_ATTENTE_PAIEMENT, PAYEE, EXPIREE, ANNULEE
    }

    public Commande() {
        this.dateCommande = LocalDateTime.now();
        this.dateExpiration = this.dateCommande.plusHours(24);
        this.statut = StatutCommande.EN_ATTENTE_PAIEMENT;
    }

    public UUID getId() { return id; }
    public void setId(UUID id) { this.id = id; }

    public String getReference() { return reference; }
    public void setReference(String reference) { this.reference = reference; }

    public UUID getOffreId() { return offreId; }
    public void setOffreId(UUID offreId) { this.offreId = offreId; }

    public UUID getAcheteurId() { return acheteurId; }
    public void setAcheteurId(UUID acheteurId) { this.acheteurId = acheteurId; }

    public UUID getVendeurId() { return vendeurId; }
    public void setVendeurId(UUID vendeurId) { this.vendeurId = vendeurId; }

    public UUID getProduitId() { return produitId; }
    public void setProduitId(UUID produitId) { this.produitId = produitId; }

    public double getPrixFinal() { return prixFinal; }
    public void setPrixFinal(double prixFinal) { this.prixFinal = prixFinal; }

    public StatutCommande getStatut() { return statut; }
    public void setStatut(StatutCommande statut) { this.statut = statut; }

    public LocalDateTime getDateCommande() { return dateCommande; }
    public void setDateCommande(LocalDateTime dateCommande) { this.dateCommande = dateCommande; }

    public LocalDateTime getDateExpiration() { return dateExpiration; }
    public void setDateExpiration(LocalDateTime dateExpiration) { this.dateExpiration = dateExpiration; }

    public UUID getPaiementId() { return paiementId; }
    public void setPaiementId(UUID paiementId) { this.paiementId = paiementId; }
}
