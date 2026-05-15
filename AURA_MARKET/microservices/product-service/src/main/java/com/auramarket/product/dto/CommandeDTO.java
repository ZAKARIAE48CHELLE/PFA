package com.auramarket.product.dto;

import com.auramarket.product.entity.Commande.StatutCommande;
import java.time.LocalDateTime;
import java.util.UUID;

public class CommandeDTO {
    private UUID id;
    private String reference;
    private UUID offreId;
    private UUID produitId;
    private UUID acheteurId;
    private UUID vendeurId;
    private double prixFinal;
    private StatutCommande statut;
    private LocalDateTime dateCommande;
    private LocalDateTime dateExpiration;
    private UUID paiementId;
    private int quantite;

    public CommandeDTO() {}

    public UUID getId() { return id; }
    public void setId(UUID id) { this.id = id; }
    public String getReference() { return reference; }
    public void setReference(String reference) { this.reference = reference; }
    public UUID getOffreId() { return offreId; }
    public void setOffreId(UUID offreId) { this.offreId = offreId; }
    public UUID getProduitId() { return produitId; }
    public void setProduitId(UUID produitId) { this.produitId = produitId; }
    public UUID getAcheteurId() { return acheteurId; }
    public void setAcheteurId(UUID acheteurId) { this.acheteurId = acheteurId; }
    public UUID getVendeurId() { return vendeurId; }
    public void setVendeurId(UUID vendeurId) { this.vendeurId = vendeurId; }
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

    public int getQuantite() { return quantite; }
    public void setQuantite(int quantite) { this.quantite = quantite; }
}
