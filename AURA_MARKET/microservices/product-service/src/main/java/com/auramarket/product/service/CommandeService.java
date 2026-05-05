package com.auramarket.product.service;

import com.auramarket.product.dto.CommandeDTO;
import com.auramarket.product.dto.PaiementConfirmationDTO;
import com.auramarket.product.dto.PaiementRequestDTO;
import com.auramarket.product.entity.Commande;
import com.auramarket.product.entity.Commande.StatutCommande;
import com.auramarket.product.entity.Offre;
import com.auramarket.product.entity.Offre.StatutOffre;
import com.auramarket.product.entity.Paiement;
import com.auramarket.product.entity.Paiement.StatutPaiement;
import com.auramarket.product.entity.Produit;
import com.auramarket.product.entity.Produit.StatutProduit;
import com.auramarket.product.repository.CommandeRepository;
import com.auramarket.product.repository.OffreRepository;
import com.auramarket.product.repository.PaiementRepository;
import com.auramarket.product.repository.ProduitRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.security.SecureRandom;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.UUID;
import java.util.stream.Collectors;

@Service
public class CommandeService {

    @Autowired
    private CommandeRepository commandeRepository;

    @Autowired
    private PaiementRepository paiementRepository;

    @Autowired
    private OffreRepository offreRepository;

    @Autowired
    private ProduitRepository produitRepository;

    private static final SecureRandom random = new SecureRandom();

    @Transactional
    public Offre accepterOffre(UUID offreId) {
        Offre offre = offreRepository.findById(offreId)
                .orElseThrow(() -> new RuntimeException("Offre non trouvée: " + offreId));

        if (offre.getStatut() == StatutOffre.VALIDEE) {
            return offre; // Already validated, just return
        }

        if (offre.getStatut() != StatutOffre.EN_ATTENTE) {
            throw new IllegalStateException("Statut invalide pour acceptation: " + offre.getStatut());
        }

        offre.setStatut(StatutOffre.VALIDEE);
        if (offre.getPrixFinal() <= 0) {
            offre.setPrixFinal(offre.getPrixPropose());
        }
        return offreRepository.save(offre);
    }

    @Transactional
    public PaiementConfirmationDTO payerOffre(UUID offreId, PaiementRequestDTO request) {
        // 1. Load & Validate Offre
        Offre offre = offreRepository.findById(offreId)
                .orElseThrow(() -> new RuntimeException("Offre non trouvée"));
        
        if (offre.getStatut() != StatutOffre.VALIDEE) {
            throw new IllegalStateException("L'offre doit être validée (statut actuel: " + offre.getStatut() + ")");
        }

        // 2. Load Produit
        Produit produit = produitRepository.findById(offre.getProduitId())
                .orElseThrow(() -> new RuntimeException("Produit non trouvé"));

        if (produit.getStock() <= 0) {
            produit.setStatut(StatutProduit.VENDU);
            produitRepository.save(produit);
            throw new IllegalStateException("Désolé, ce produit est en rupture de stock.");
        }

        // 3. GENERATE PAIEMENT
        // ... (paiement logic) ...
        Paiement paiement = new Paiement();
        paiement.setMontant(request.getMontant());
        paiement.setMethode(request.getMethode());
        paiement.setReference(generateReference("PAY"));
        paiement.setStatut(StatutPaiement.CONFIRME);
        paiement.setDateConfirmation(LocalDateTime.now());
        paiement = paiementRepository.save(paiement);

        // 4. GENERATE COMMANDE
        Commande commande = new Commande();
        commande.setOffreId(offre.getId());
        commande.setAcheteurId(offre.getAcheteurId());
        commande.setVendeurId(produit.getVendeurId());
        commande.setProduitId(offre.getProduitId());
        commande.setPrixFinal(offre.getPrixFinal());
        commande.setReference(generateReference("CMD"));
        commande.setStatut(StatutCommande.PAYEE);
        commande.setPaiementId(paiement.getId());
        commande = commandeRepository.save(commande);

        // 5. Link Payment
        paiement.setCommandeId(commande.getId());
        paiementRepository.save(paiement);

        // 6. Update Produit stock & status
        produit.setStock(produit.getStock() - 1);
        if (produit.getStock() <= 0) {
            produit.setStatut(StatutProduit.VENDU);
        }
        produitRepository.save(produit);

        return new PaiementConfirmationDTO(mapToPaiementInfo(paiement), mapToDTO(commande));
    }

    public CommandeDTO getCommande(UUID commandeId) {
        return commandeRepository.findById(commandeId)
                .map(this::mapToDTO)
                .orElseThrow(() -> new RuntimeException("Commande non trouvée"));
    }

    public List<CommandeDTO> getCommandesByAcheteur(UUID acheteurId) {
        return commandeRepository.findByAcheteurId(acheteurId).stream()
                .map(this::mapToDTO)
                .collect(Collectors.toList());
    }

    public List<CommandeDTO> getCommandesByVendeur(UUID vendeurId) {
        return commandeRepository.findByVendeurId(vendeurId).stream()
                .map(this::mapToDTO)
                .collect(Collectors.toList());
    }

    public List<CommandeDTO> getAllCommandes() {
        return commandeRepository.findAll().stream()
                .map(this::mapToDTO)
                .collect(Collectors.toList());
    }

    private String generateReference(String prefix) {
        String datePart = LocalDate.now().format(DateTimeFormatter.ofPattern("yyyyMMdd"));
        int randomPart = random.nextInt(1000000);
        return String.format("%s-%s-%06d", prefix, datePart, randomPart);
    }

    private CommandeDTO mapToDTO(Commande c) {
        CommandeDTO dto = new CommandeDTO();
        dto.setId(c.getId());
        dto.setReference(c.getReference());
        dto.setOffreId(c.getOffreId());
        dto.setProduitId(c.getProduitId());
        dto.setAcheteurId(c.getAcheteurId());
        dto.setVendeurId(c.getVendeurId());
        dto.setPrixFinal(c.getPrixFinal());
        dto.setStatut(c.getStatut());
        dto.setDateCommande(c.getDateCommande());
        dto.setDateExpiration(c.getDateExpiration());
        dto.setPaiementId(c.getPaiementId());
        return dto;
    }

    private PaiementConfirmationDTO.PaiementInfo mapToPaiementInfo(Paiement p) {
        PaiementConfirmationDTO.PaiementInfo info = new PaiementConfirmationDTO.PaiementInfo();
        info.setId(p.getId());
        info.setReference(p.getReference());
        info.setMontant(p.getMontant());
        info.setMethode(p.getMethode());
        info.setStatut(p.getStatut());
        info.setDatePaiement(p.getDatePaiement());
        info.setDateConfirmation(p.getDateConfirmation());
        return info;
    }
}
