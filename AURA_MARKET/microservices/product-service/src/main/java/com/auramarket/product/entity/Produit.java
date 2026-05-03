package com.auramarket.product.entity;

import jakarta.persistence.*;
import java.time.LocalDateTime;
import java.util.UUID;

@Entity
@Table(name = "produits")
public class Produit {
    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;
    private String titre;
    @Column(columnDefinition = "TEXT")
    private String description;
    private double prix;
    private double prixMin;
    private String categorie;
    @Column(columnDefinition = "TEXT")
    private String imageUrl;
    private int stock;
    
    @Enumerated(EnumType.STRING)
    private StatutProduit statut;
    
    private LocalDateTime datePublication;
    private UUID vendeurId;

    public enum StatutProduit { ACTIF, BLOQUE, VENDU, EN_ATTENTE }

    public Produit() {
        this.datePublication = LocalDateTime.now();
        this.statut = StatutProduit.ACTIF;
    }

    public UUID getId() { return id; }
    public void setId(UUID id) { this.id = id; }
    public String getTitre() { return titre; }
    public void setTitre(String titre) { this.titre = titre; }
    public String getDescription() { return description; }
    public void setDescription(String description) { this.description = description; }
    public double getPrix() { return prix; }
    public void setPrix(double prix) { this.prix = prix; }
    public double getPrixMin() { return prixMin; }
    public void setPrixMin(double prixMin) { this.prixMin = prixMin; }
    public String getCategorie() { return categorie; }
    public void setCategorie(String categorie) { this.categorie = categorie; }
    public String getImageUrl() { return imageUrl; }
    public void setImageUrl(String imageUrl) { this.imageUrl = imageUrl; }
    public int getStock() { return stock; }
    public void setStock(int stock) { this.stock = stock; }
    public StatutProduit getStatut() { return statut; }
    public void setStatut(StatutProduit statut) { this.statut = statut; }
    public LocalDateTime getDatePublication() { return datePublication; }
    public void setDatePublication(LocalDateTime datePublication) { this.datePublication = datePublication; }
    public UUID getVendeurId() { return vendeurId; }
    public void setVendeurId(UUID vendeurId) { this.vendeurId = vendeurId; }
}
