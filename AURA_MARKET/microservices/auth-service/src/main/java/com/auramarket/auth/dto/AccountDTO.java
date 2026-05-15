package com.auramarket.auth.dto;

import java.util.List;
import java.util.UUID;

public class AccountDTO {
    private UUID id;
    private String email;
    private String role;
    private Float scoreReputation; // For VENDEUR
    private List<String> historique; // For ACHETEUR

    public AccountDTO() {}

    public AccountDTO(UUID id, String email, String role) {
        this.id = id;
        this.email = email;
        this.role = role;
    }

    public UUID getId() { return id; }
    public void setId(UUID id) { this.id = id; }

    public String getEmail() { return email; }
    public void setEmail(String email) { this.email = email; }

    public String getRole() { return role; }
    public void setRole(String role) { this.role = role; }

    public Float getScoreReputation() { return scoreReputation; }
    public void setScoreReputation(Float scoreReputation) { this.scoreReputation = scoreReputation; }

    public List<String> getHistorique() { return historique; }
    public void setHistorique(List<String> historique) { this.historique = historique; }
}
