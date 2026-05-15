package com.auramarket.product.service;

import com.auramarket.product.entity.Offre;
import com.auramarket.product.entity.Produit;
import com.auramarket.product.repository.OffreRepository;
import com.auramarket.product.repository.ProduitRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.web.client.RestTemplate;
import java.util.Comparator;
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
        return getAllProduits(null, null, null, null);
    }

    public List<Produit> getAllProduits(String category) {
        return getAllProduits(category, null, null, null);
    }

    public List<Produit> getAllProduits(String category, String search) {
        return getAllProduits(category, search, null, null);
    }

    public List<Produit> getAllProduits(String category, String search, Double priceMin, Double priceMax) {
        PageRequest pageRequest = PageRequest.of(0, 100, Sort.by(Sort.Direction.DESC, "datePublication"));
        List<Produit> baseList = produitRepository.findAll(pageRequest).getContent();
        
        return baseList.stream()
            .filter(p -> {
                // 1. Search Text Match (Title OR Description OR Category)
                if (search != null && !search.trim().isEmpty()) {
                    String lowerSearch = search.toLowerCase().trim();
                    boolean titleMatch = p.getTitre() != null && p.getTitre().toLowerCase().contains(lowerSearch);
                    boolean descMatch = p.getDescription() != null && p.getDescription().toLowerCase().contains(lowerSearch);
                    boolean catMatch = p.getCategorie() != null && p.getCategorie().toLowerCase().contains(lowerSearch);
                    
                    // Semantic hardware fallbacks
                    if (!titleMatch && !descMatch && !catMatch) {
                        if (lowerSearch.contains("ordinator") || lowerSearch.contains("computer") || 
                            lowerSearch.contains("laptop") || lowerSearch.contains("pc") || 
                            lowerSearch.contains("portable")) {
                            String sem = "ordinat"; // Match ordinateur/ordinateurs
                            titleMatch = p.getTitre() != null && p.getTitre().toLowerCase().contains(sem);
                            descMatch = p.getDescription() != null && p.getDescription().toLowerCase().contains(sem);
                            catMatch = p.getCategorie() != null && p.getCategorie().toLowerCase().contains(sem);
                        }
                    }
                    
                    if (!titleMatch && !descMatch && !catMatch) return false;
                }
                
                // 2. Explicit Category Filter
                if (category != null && !category.trim().isEmpty()) {
                    if (p.getCategorie() == null || !p.getCategorie().equalsIgnoreCase(category.trim())) {
                        return false;
                    }
                }
                
                // 3. Dynamic Price Bounds
                if (priceMin != null && p.getPrix() < priceMin) return false;
                if (priceMax != null && p.getPrix() > priceMax) return false;
                
                // 4. Business Guardrails (Actif & In-Stock)
                if (p.getStatut() != null && p.getStatut() != Produit.StatutProduit.ACTIF) return false;
                if (p.getStock() <= 0) return false;
                
                return true;
            })
            .toList();
    }

    public List<Produit> searchProducts(String search, String category, Double priceMin, Double priceMax) {
        List<Produit> products = produitRepository.findAll();
        System.out.println("[SEARCH] Input: search=" + search + " category=" + category + " priceMin=" + priceMin + " priceMax=" + priceMax);
        System.out.println("[SEARCH] Total products in DB: " + products.size());

        // Keep only in-stock products
        products = products.stream()
            .filter(p -> p.getStock() > 0)
            .toList();
        System.out.println("[SEARCH] After stock filter: " + products.size());

        if (search != null && !search.isBlank()) {
            String q = normalize(search);
            System.out.println("[SEARCH] Normalized query: '" + q + "' (length=" + q.length() + ")");

            if (!q.isBlank()) {
                final String searchQ = q;
                products = products.stream()
                    .filter(p -> {
                        String title = normalize(p.getTitre());
                        String desc = normalize(p.getDescription());
                        String cat = normalize(p.getCategorie());

                        // For short queries, use word-boundary to avoid substring false positives
                        // e.g. "phone" inside "persephone", "pc" inside "npc"
                        boolean useWordMatch = searchQ.length() <= 6;

                        if (useWordMatch) {
                            if (title.length() >= 2 && wordMatch(title, searchQ)) return true;
                            if (desc.length() >= 2 && wordMatch(desc, searchQ)) return true;
                            if (cat.length() >= 2 && wordMatch(cat, searchQ)) return true;
                        } else {
                            if (title.length() >= 2 && title.contains(searchQ)) return true;
                            if (desc.length() >= 2 && desc.contains(searchQ)) return true;
                            if (cat.length() >= 2 && cat.contains(searchQ)) return true;
                        }

                        // Semantic fallback
                        return matchesSemantic(searchQ, title, desc, cat);
                    })
                    .toList();
                System.out.println("[SEARCH] After text/semantic filter: " + products.size());
            }
        }

        if (category != null && !category.isBlank()) {
            String normCat = normalize(category);
            if (!normCat.isBlank()) {
                List<Produit> catFiltered = products.stream()
                    .filter(p -> {
                        String cat = normalize(p.getCategorie());
                        return cat.contains(normCat) || normCat.contains(cat);
                    })
                    .toList();
                // Only apply category filter if it yields results (don't over-filter)
                if (!catFiltered.isEmpty()) {
                    products = catFiltered;
                }
            }
        }

        if (priceMin != null) {
            products = products.stream()
                .filter(p -> getEffectivePrice(p) >= priceMin)
                .toList();
        }

        if (priceMax != null) {
            products = products.stream()
                .filter(p -> getEffectivePrice(p) <= priceMax)
                .toList();
            System.out.println("[SEARCH] After priceMax=" + priceMax + " filter: " + products.size());
        }

        List<Produit> finalResult = products.stream()
            .sorted(Comparator.comparing(Produit::getDatePublication).reversed())
            .limit(50)
            .toList();
        System.out.println("[SEARCH] Final result count: " + finalResult.size());
        return finalResult;
    }

    private double getEffectivePrice(Produit p) {
        if (p.getPrixOffre() != null && p.getPrixOffre() > 0) {
            return p.getPrixOffre();
        }
        return p.getPrix();
    }

    private String normalize(String s) {
        if (s == null) return "";
        return java.text.Normalizer.normalize(s.toLowerCase(), java.text.Normalizer.Form.NFD)
            .replaceAll("\\p{M}", "")
            .replaceAll("[^a-z0-9 ]", " ")
            .replaceAll("\\s+", " ")
            .trim();
    }

    private boolean matchesSemantic(String q, String title, String desc, String cat) {
        // Guard against empty normalized strings
        if (q.isBlank() || (title.isBlank() && desc.isBlank() && cat.isBlank())) {
            return false;
        }

        // Phone / téléphone family
        if (wordMatch(q, "iphone") || wordMatch(q, "i phone")) {
            return wordMatch(title, "iphone") || wordMatch(desc, "iphone");
        }
        if (wordMatch(q, "phone") || wordMatch(q, "telephone")
            || wordMatch(q, "mobile") || wordMatch(q, "smartphone")) {
            return wordMatch(title, "phone") || wordMatch(title, "telephone")
                || wordMatch(title, "iphone") || wordMatch(title, "samsung")
                || wordMatch(title, "xiaomi") || wordMatch(title, "huawei")
                || wordMatch(title, "oppo") || wordMatch(title, "smartphone")
                || wordMatch(desc, "smartphone") || wordMatch(desc, "telephone")
                || wordMatch(cat, "telephone") || wordMatch(cat, "smartphone")
                || cat.contains("smartphone");
        }

        // Samsung / Galaxy — but NOT game titles like "Guardians of the Galaxy"
        if (wordMatch(q, "samsung") || wordMatch(q, "galaxy")) {
            return wordMatch(title, "samsung") || (wordMatch(title, "galaxy") && !title.contains("guardians"))
                || wordMatch(desc, "samsung");
        }

        // Computer family — use word boundaries for short brand names
        if (q.contains("ordinator") || q.contains("ordinateur") || q.contains("computer")
            || q.contains("laptop") || wordMatch(q, "pc")
            || q.contains("notebook")) {
            return title.contains("ordinateur") || title.contains("laptop")
                || title.contains("macbook") || title.contains("lenovo")
                || title.contains("asus") || title.contains("notebook")
                || desc.contains("ordinateur") || desc.contains("laptop");
        }

        // Shoes family
        if (q.contains("chaussure") || wordMatch(q, "shoe") || q.contains("sneaker")
            || wordMatch(q, "basket")) {
            return title.contains("chaussure") || wordMatch(title, "shoe")
                || title.contains("sneaker") || wordMatch(title, "nike")
                || wordMatch(title, "adidas")
                || cat.contains("chaussure") || cat.contains("vetement");
        }

        return false;
    }

    /** Word-boundary match: checks if 'word' appears as a whole word in 'text' */
    private boolean wordMatch(String text, String word) {
        if (text == null || text.isBlank() || word == null || word.isBlank()) return false;
        return text.matches(".*\\b" + java.util.regex.Pattern.quote(word) + "\\b.*");
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
            p.setPrixPlancher(updated.getPrixPlancher());
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

    public Map<String, Long> getProductsCountByCategory() {
        List<Object[]> results = produitRepository.countProductsByCategory();
        Map<String, Long> map = new HashMap<>();
        for (Object[] row : results) {
            if (row[0] != null) {
                map.put((String) row[0], (Long) row[1]);
            }
        }
        return map;
    }
}
