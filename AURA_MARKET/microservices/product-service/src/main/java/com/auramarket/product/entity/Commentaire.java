package com.auramarket.product.entity;

import jakarta.persistence.*;
import java.time.LocalDateTime;
import java.util.UUID;

@Entity
@Table(name = "commentaires")
public class Commentaire {
    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;
    
    private UUID produitId;
    
    @Column(columnDefinition = "TEXT")
    private String texte;
    
    private int note;
    
    private LocalDateTime datePublication;
    
    private UUID auteurId;

    public Commentaire() {
        this.datePublication = LocalDateTime.now();
    }

    // Getters and Setters
    public UUID getId() { return id; }
    public void setId(UUID id) { this.id = id; }
    public UUID getProduitId() { return produitId; }
    public void setProduitId(UUID produitId) { this.produitId = produitId; }
    public String getTexte() { return texte; }
    public void setTexte(String texte) { this.texte = texte; }
    public int getNote() { return note; }
    public void setNote(int note) { this.note = note; }
    public LocalDateTime getDatePublication() { return datePublication; }
    public void setDatePublication(LocalDateTime datePublication) { this.datePublication = datePublication; }
    public UUID getAuteurId() { return auteurId; }
    public void setAuteurId(UUID auteurId) { this.auteurId = auteurId; }
}
