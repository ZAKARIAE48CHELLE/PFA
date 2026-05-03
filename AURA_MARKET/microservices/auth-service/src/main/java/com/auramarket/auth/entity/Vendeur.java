package com.auramarket.auth.entity;

import jakarta.persistence.Entity;
import jakarta.persistence.Table;

@Entity
@Table(name = "vendeurs")
public class Vendeur extends Utilisateur {
    
    private float scoreReputation;

    public Vendeur() {
        super();
        this.setRole(Role.VENDEUR);
    }

    public Vendeur(String email, String mdpHash, float scoreReputation) {
        super(email, mdpHash, Role.VENDEUR);
        this.scoreReputation = scoreReputation;
    }

    public float getScoreReputation() { return scoreReputation; }
    public void setScoreReputation(float scoreReputation) { this.scoreReputation = scoreReputation; }
}
