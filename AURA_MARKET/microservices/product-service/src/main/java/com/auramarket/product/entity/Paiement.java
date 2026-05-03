package com.auramarket.product.entity;

import jakarta.persistence.*;
import java.time.LocalDateTime;
import java.util.UUID;

@Entity
@Table(name = "paiements")
public class Paiement {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    private UUID commandeId;
    private double montant;

    @Enumerated(EnumType.STRING)
    private MethodePaiement methode;

    @Enumerated(EnumType.STRING)
    private StatutPaiement statut;

    @Column(unique = true, nullable = false)
    private String reference;

    private LocalDateTime datePaiement;
    private LocalDateTime dateConfirmation;

    public enum MethodePaiement {
        CARTE, VIREMENT, PAYPAL, CRYPTO
    }

    public enum StatutPaiement {
        EN_COURS, CONFIRME, ECHOUE, REMBOURSE
    }

    public Paiement() {
        this.datePaiement = LocalDateTime.now();
        this.statut = StatutPaiement.EN_COURS;
    }

    public UUID getId() { return id; }
    public void setId(UUID id) { this.id = id; }

    public UUID getCommandeId() { return commandeId; }
    public void setCommandeId(UUID commandeId) { this.commandeId = commandeId; }

    public double getMontant() { return montant; }
    public void setMontant(double montant) { this.montant = montant; }

    public MethodePaiement getMethode() { return methode; }
    public void setMethode(MethodePaiement methode) { this.methode = methode; }

    public StatutPaiement getStatut() { return statut; }
    public void setStatut(StatutPaiement statut) { this.statut = statut; }

    public String getReference() { return reference; }
    public void setReference(String reference) { this.reference = reference; }

    public LocalDateTime getDatePaiement() { return datePaiement; }
    public void setDatePaiement(LocalDateTime datePaiement) { this.datePaiement = datePaiement; }

    public LocalDateTime getDateConfirmation() { return dateConfirmation; }
    public void setDateConfirmation(LocalDateTime dateConfirmation) { this.dateConfirmation = dateConfirmation; }
}
