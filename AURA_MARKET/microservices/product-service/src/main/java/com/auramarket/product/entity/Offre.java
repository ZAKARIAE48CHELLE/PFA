package com.auramarket.product.entity;

import jakarta.persistence.*;
import java.time.LocalDateTime;
import java.util.UUID;

@Entity
@Table(name = "offres")
public class Offre {
    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;
    private String titre;
    private String description;
    private double prixPropose;
    private double prixFinal;

    @Enumerated(EnumType.STRING)
    private StatutOffre statut;
    
    private LocalDateTime dateCreation;
    private LocalDateTime dateExpiration;
    private LocalDateTime dateDebut;
    private LocalDateTime dateFin;
    private UUID produitId;
    private UUID acheteurId;
    private boolean agentGenere;
    private double pourcentageDiscount;

    public enum StatutOffre { EN_ATTENTE, VALIDEE, REJETEE, EXPIREE }

    public Offre() {
        this.dateCreation = LocalDateTime.now();
        this.statut = StatutOffre.EN_ATTENTE;
    }

    public UUID getId() { return id; }
    public void setId(UUID id) { this.id = id; }
    public String getTitre() { return titre; }
    public void setTitre(String titre) { this.titre = titre; }
    public String getDescription() { return description; }
    public void setDescription(String description) { this.description = description; }
    public double getPrixPropose() { return prixPropose; }
    public void setPrixPropose(double prixPropose) { this.prixPropose = prixPropose; }
    public double getPrixFinal() { return prixFinal; }
    public void setPrixFinal(double prixFinal) { this.prixFinal = prixFinal; }
    public StatutOffre getStatut() { return statut; }
    public void setStatut(StatutOffre statut) { this.statut = statut; }
    public LocalDateTime getDateCreation() { return dateCreation; }
    public void setDateCreation(LocalDateTime dateCreation) { this.dateCreation = dateCreation; }
    public LocalDateTime getDateExpiration() { return dateExpiration; }
    public void setDateExpiration(LocalDateTime dateExpiration) { this.dateExpiration = dateExpiration; }
    public LocalDateTime getDateDebut() { return dateDebut; }
    public void setDateDebut(LocalDateTime dateDebut) { this.dateDebut = dateDebut; }
    public LocalDateTime getDateFin() { return dateFin; }
    public void setDateFin(LocalDateTime dateFin) { this.dateFin = dateFin; }
    public UUID getProduitId() { return produitId; }
    public void setProduitId(UUID produitId) { this.produitId = produitId; }
    public UUID getAcheteurId() { return acheteurId; }
    public void setAcheteurId(UUID acheteurId) { this.acheteurId = acheteurId; }
    public boolean isAgentGenere() { return agentGenere; }
    public void setAgentGenere(boolean agentGenere) { this.agentGenere = agentGenere; }
    public double getPourcentageDiscount() { return pourcentageDiscount; }
    public void setPourcentageDiscount(double pourcentageDiscount) { this.pourcentageDiscount = pourcentageDiscount; }
}
