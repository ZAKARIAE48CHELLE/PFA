package com.auramarket.product.dto;

import com.auramarket.product.entity.Paiement.MethodePaiement;
import com.auramarket.product.entity.Paiement.StatutPaiement;
import java.time.LocalDateTime;
import java.util.UUID;

public class PaiementConfirmationDTO {
    private PaiementInfo paiement;
    private CommandeDTO commande;

    public PaiementConfirmationDTO() {}

    public PaiementConfirmationDTO(PaiementInfo paiement, CommandeDTO commande) {
        this.paiement = paiement;
        this.commande = commande;
    }

    public static class PaiementInfo {
        private UUID id;
        private String reference;
        private double montant;
        private MethodePaiement methode;
        private StatutPaiement statut;
        private LocalDateTime datePaiement;
        private LocalDateTime dateConfirmation;

        public PaiementInfo() {}

        public UUID getId() { return id; }
        public void setId(UUID id) { this.id = id; }
        public String getReference() { return reference; }
        public void setReference(String reference) { this.reference = reference; }
        public double getMontant() { return montant; }
        public void setMontant(double montant) { this.montant = montant; }
        public MethodePaiement getMethode() { return methode; }
        public void setMethode(MethodePaiement methode) { this.methode = methode; }
        public StatutPaiement getStatut() { return statut; }
        public void setStatut(StatutPaiement statut) { this.statut = statut; }
        public LocalDateTime getDatePaiement() { return datePaiement; }
        public void setDatePaiement(LocalDateTime datePaiement) { this.datePaiement = datePaiement; }
        public LocalDateTime getDateConfirmation() { return dateConfirmation; }
        public void setDateConfirmation(LocalDateTime dateConfirmation) { this.dateConfirmation = dateConfirmation; }
    }

    public PaiementInfo getPaiement() { return paiement; }
    public void setPaiement(PaiementInfo paiement) { this.paiement = paiement; }
    public CommandeDTO getCommande() { return commande; }
    public void setCommande(CommandeDTO commande) { this.commande = commande; }
}
