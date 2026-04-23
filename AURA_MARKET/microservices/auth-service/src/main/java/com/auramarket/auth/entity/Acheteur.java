package com.auramarket.auth.entity;

import jakarta.persistence.ElementCollection;
import jakarta.persistence.Entity;
import jakarta.persistence.Table;
import java.util.List;
import java.util.ArrayList;

@Entity
@Table(name = "acheteurs")
public class Acheteur extends Utilisateur {
    
    @ElementCollection
    private List<String> historique = new ArrayList<>();

    public Acheteur() {
        super();
        this.setRole(Role.ACHETEUR);
    }

    public Acheteur(String email, String mdpHash, List<String> historique) {
        super(email, mdpHash, Role.ACHETEUR);
        this.historique = historique;
    }

    public List<String> getHistorique() { return historique; }
    public void setHistorique(List<String> historique) { this.historique = historique; }
}
