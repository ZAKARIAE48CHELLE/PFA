package com.auramarket.negotiation.entity;

import jakarta.persistence.*;
import java.util.UUID;

@Entity
@Table(name = "negociations")
public class Negociation {
    
    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;
    
    private int rounds;
    private Double prixInitial;
    private Double prixFinal;
    
    private UUID acheteurId;
    private UUID vendeurId;
    private UUID produitId;
    
    private String status = "OPEN"; // OPEN, ACCEPTED, REJECTED, CLOSED

    public Negociation() {
        this.rounds = 0;
        this.status = "OPEN";
    }

    public UUID getId() { return id; }
    public void setId(UUID id) { this.id = id; }
    public int getRounds() { return rounds; }
    public void setRounds(int rounds) { this.rounds = rounds; }
    public Double getPrixInitial() { return prixInitial; }
    public void setPrixInitial(Double prixInitial) { this.prixInitial = prixInitial; }
    public Double getPrixFinal() { return prixFinal; }
    public void setPrixFinal(Double prixFinal) { this.prixFinal = prixFinal; }
    public UUID getAcheteurId() { return acheteurId; }
    public void setAcheteurId(UUID acheteurId) { this.acheteurId = acheteurId; }
    public UUID getVendeurId() { return vendeurId; }
    public void setVendeurId(UUID vendeurId) { this.vendeurId = vendeurId; }
    public UUID getProduitId() { return produitId; }
    public void setProduitId(UUID produitId) { this.produitId = produitId; }
    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }
}
