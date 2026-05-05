package com.auramarket.product.controller;

import com.auramarket.product.entity.Offre;
import com.auramarket.product.service.ProductService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/offers")
public class OffreController {

    @Autowired
    private ProductService productService;

    @GetMapping
    public ResponseEntity<List<Offre>> getAllOffres() {
        return ResponseEntity.ok(productService.getAllOffres());
    }

    @PostMapping
    public ResponseEntity<Offre> createOffre(@RequestBody Offre offre) {
        return ResponseEntity.ok(productService.createOffre(offre));
    }

    @PutMapping("/{id}")
    public ResponseEntity<Offre> updateOffre(@PathVariable java.util.UUID id, @RequestBody Offre offre) {
        return ResponseEntity.ok(productService.updateOffre(id, offre));
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteOffre(@PathVariable java.util.UUID id) {
        productService.deleteOffre(id);
        return ResponseEntity.noContent().build();
    }
}
