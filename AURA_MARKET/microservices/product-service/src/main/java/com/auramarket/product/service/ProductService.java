package com.auramarket.product.service;

import com.auramarket.product.entity.Offre;
import com.auramarket.product.entity.Produit;
import com.auramarket.product.repository.OffreRepository;
import com.auramarket.product.repository.ProduitRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import org.springframework.web.client.RestTemplate;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

@Service
public class ProductService {

    @Autowired
    private ProduitRepository produitRepository;

    @Autowired
    private OffreRepository offreRepository;

    @Autowired
    private RestTemplate restTemplate;

    private final String AUDIT_URL = "http://audit-service:8084/audits";

    private void logAudit(String type, String message, String severite) {
        try {
            Map<String, String> audit = new HashMap<>();
            audit.put("type", type);
            audit.put("message", message);
            audit.put("severite", severite);
            audit.put("agentSource", "ProductService");
            restTemplate.postForObject(AUDIT_URL, audit, Map.class);
        } catch (Exception e) {
            System.err.println("Failed to send audit: " + e.getMessage());
        }
    }

    public List<Produit> getAllProduits() {
        return produitRepository.findAll();
    }

    public Produit createProduit(Produit produit) {
        Produit saved = produitRepository.save(produit);
        logAudit("PRODUCT_CREATE", "Nouveau produit créé: " + saved.getTitre(), "INFO");
        return saved;
    }
    public Produit showProduit(UUID id){
        Optional<Produit> existing = produitRepository.findById(id);
        if (existing.isEmpty()) {
            throw new RuntimeException("Produit introuvable");
        }
        return existing.get();
    }

    public Produit updateProduit(UUID id, Produit updated) {
        try {
            Optional<Produit> existing = produitRepository.findById(id);
            if (existing.isEmpty()) {
                logAudit("PRODUCT_UPDATE", "Echec: Produit " + id + " introuvable", "WARNING");
                throw new RuntimeException("Produit introuvable");
            }
            Produit p = existing.get();
            p.setTitre(updated.getTitre());
            p.setDescription(updated.getDescription());
            p.setPrix(updated.getPrix());
            p.setPrixMin(updated.getPrixMin());
            p.setCategorie(updated.getCategorie());
            p.setStock(updated.getStock());
            p.setImageUrl(updated.getImageUrl());
            p.setPrixOffre(updated.getPrixOffre());
            Produit saved = produitRepository.save(p);
            logAudit("PRODUCT_UPDATE", "Produit mis à jour: " + saved.getTitre(), "INFO");
            return saved;
        } catch (Exception e) {
            logAudit("PRODUCT_UPDATE", "Erreur lors de la mise à jour du produit " + id + ": " + e.getMessage(), "CRITICAL");
            throw e;
        }
    }

    public void deleteProduit(UUID id) {
        produitRepository.deleteById(id);
    }

    public List<Offre> getAllOffres() {
        return offreRepository.findAll();
    }

    public Offre createOffre(Offre offre) {
        return offreRepository.save(offre);
    }

    public List<Offre> getOffresByProduitId(UUID produitId) {
        return offreRepository.findByProduitId(produitId);
    }

    public Offre updateOffre(UUID id, Offre updated) {
        Offre existing = offreRepository.findById(id).orElseThrow(() -> new RuntimeException("Offre introuvable"));
        existing.setPrixPropose(updated.getPrixPropose());
        existing.setPrixFinal(updated.getPrixFinal());
        existing.setDateDebut(updated.getDateDebut());
        existing.setDateFin(updated.getDateFin());
        existing.setStatut(updated.getStatut());
        existing.setPourcentageDiscount(updated.getPourcentageDiscount());
        return offreRepository.save(existing);
    }

    public void deleteOffre(UUID id) {
        offreRepository.deleteById(id);
    }
}
