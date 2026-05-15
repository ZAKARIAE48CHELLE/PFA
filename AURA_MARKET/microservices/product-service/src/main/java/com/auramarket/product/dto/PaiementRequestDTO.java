package com.auramarket.product.dto;

import com.auramarket.product.entity.Paiement.MethodePaiement;

public class PaiementRequestDTO {
    private MethodePaiement methode;
    private double montant;
    private int quantite;

    public PaiementRequestDTO() {}

    public MethodePaiement getMethode() { return methode; }
    public void setMethode(MethodePaiement methode) { this.methode = methode; }
    public double getMontant() { return montant; }
    public void setMontant(double montant) { this.montant = montant; }
    public int getQuantite() { return quantite; }
    public void setQuantite(int quantite) { this.quantite = quantite; }
}
