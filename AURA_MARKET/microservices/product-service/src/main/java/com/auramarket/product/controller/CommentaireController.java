package com.auramarket.product.controller;

import com.auramarket.product.entity.Commentaire;
import com.auramarket.product.repository.CommentaireRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/products")
public class CommentaireController {

    @Autowired
    private CommentaireRepository commentaireRepository;

    @GetMapping("/{produitId}/comments")
    public ResponseEntity<List<Commentaire>> getCommentsByProduit(@PathVariable UUID produitId) {
        return ResponseEntity.ok(commentaireRepository.findByProduitIdOrderByDatePublicationDesc(produitId));
    }

    @PostMapping("/{produitId}/comments")
    public ResponseEntity<Commentaire> addComment(@PathVariable UUID produitId, @RequestBody Commentaire commentaire) {
        commentaire.setProduitId(produitId);
        return ResponseEntity.ok(commentaireRepository.save(commentaire));
    }
}
