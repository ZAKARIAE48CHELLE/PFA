package com.auramarket.product.controller;

import com.auramarket.product.dto.CommandeDTO;
import com.auramarket.product.dto.PaiementConfirmationDTO;
import com.auramarket.product.dto.PaiementRequestDTO;
import com.auramarket.product.entity.Offre;
import com.auramarket.product.service.CommandeService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping
public class CommandeController {

    @Autowired
    private CommandeService commandeService;

    @PostMapping("/offers/{offreId}/accepter")
    public ResponseEntity<?> accepterOffre(@PathVariable UUID offreId) {
        try {
            return ResponseEntity.ok(commandeService.accepterOffre(offreId));
        } catch (IllegalStateException e) {
            return ResponseEntity.status(HttpStatus.CONFLICT).body(java.util.Map.of("message", e.getMessage()));
        } catch (RuntimeException e) {
            return ResponseEntity.status(HttpStatus.NOT_FOUND).body(java.util.Map.of("message", e.getMessage()));
        }
    }

    @PostMapping("/offers/{offreId}/payer")
    public ResponseEntity<?> payerOffre(
            @PathVariable UUID offreId, 
            @RequestBody PaiementRequestDTO request) {
        try {
            return ResponseEntity.ok(commandeService.payerOffre(offreId, request));
        } catch (IllegalStateException e) {
            return ResponseEntity.status(HttpStatus.CONFLICT).body(java.util.Map.of("message", e.getMessage()));
        } catch (IllegalArgumentException e) {
            return ResponseEntity.badRequest().body(java.util.Map.of("message", e.getMessage()));
        } catch (RuntimeException e) {
            return ResponseEntity.status(HttpStatus.NOT_FOUND).body(java.util.Map.of("message", e.getMessage()));
        }
    }

    @GetMapping("/commandes/{commandeId}")
    public ResponseEntity<CommandeDTO> getCommande(@PathVariable UUID commandeId) {
        try {
            return ResponseEntity.ok(commandeService.getCommande(commandeId));
        } catch (RuntimeException e) {
            return ResponseEntity.notFound().build();
        }
    }

    @GetMapping("/commandes/acheteur/{acheteurId}")
    public ResponseEntity<List<CommandeDTO>> getCommandesByAcheteur(@PathVariable UUID acheteurId) {
        return ResponseEntity.ok(commandeService.getCommandesByAcheteur(acheteurId));
    }

    @GetMapping("/commandes/vendeur/{vendeurId}")
    public ResponseEntity<List<CommandeDTO>> getCommandesByVendeur(@PathVariable UUID vendeurId) {
        return ResponseEntity.ok(commandeService.getCommandesByVendeur(vendeurId));
    }
}
