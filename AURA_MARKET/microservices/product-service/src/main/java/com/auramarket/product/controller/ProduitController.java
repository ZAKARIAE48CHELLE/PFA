package com.auramarket.product.controller;

import com.auramarket.product.entity.Offre;
import com.auramarket.product.entity.Produit;
import com.auramarket.product.service.ProductService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/products")
public class ProduitController {

    @Autowired
    private ProductService productService;

    @GetMapping
    public ResponseEntity<List<Produit>> getAllProduits(
            @RequestParam(required = false) String category,
            @RequestParam(required = false) String search,
            @RequestParam(required = false) Double priceMin,
            @RequestParam(required = false) Double priceMax) {
        return ResponseEntity.ok(productService.searchProducts(search, category, priceMin, priceMax));
    }

    @GetMapping("/stats/categories")
    public ResponseEntity<java.util.Map<String, Long>> getProductsCountByCategory() {
        return ResponseEntity.ok(productService.getProductsCountByCategory());
    }

    @PostMapping
    public ResponseEntity<Produit> createProduit(@RequestBody Produit produit) {
        return ResponseEntity.ok(productService.createProduit(produit));
    }

    @PutMapping("/{id}")
    public ResponseEntity<Produit> updateProduit(@PathVariable UUID id, @RequestBody Produit produit) {
        return ResponseEntity.ok(productService.updateProduit(id, produit));
    }
    @GetMapping("/{id}")
    public ResponseEntity<Produit> showProduit(@PathVariable UUID id) {
        return ResponseEntity.ok(productService.showProduit(id));
    }
    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteProduit(@PathVariable UUID id) {
        productService.deleteProduit(id);
        return ResponseEntity.noContent().build();
    }

    @GetMapping("/{id}/offers")
    public ResponseEntity<List<Offre>> getOffersByProduct(@PathVariable UUID id) {
        return ResponseEntity.ok(productService.getOffresByProduitId(id));
    }
}
