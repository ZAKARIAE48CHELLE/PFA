package com.auramarket.negotiation.controller;

import com.auramarket.negotiation.entity.Negociation;
import com.auramarket.negotiation.entity.MessageNegociation;
import com.auramarket.negotiation.service.NegociationService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/negotiations")
public class NegociationController {

    @Autowired
    private NegociationService negociationService;

    @GetMapping
    public ResponseEntity<List<Negociation>> getAllNegociations() {
        return ResponseEntity.ok(negociationService.getAllNegociations());
    }

    @PostMapping
    public ResponseEntity<Negociation> createNegociation(@RequestBody Negociation negociation) {
        return ResponseEntity.ok(negociationService.createNegociation(negociation));
    }

    @GetMapping("/{id}/messages")
    public ResponseEntity<List<MessageNegociation>> getMessages(@PathVariable java.util.UUID id) {
        return ResponseEntity.ok(negociationService.getMessages(id));
    }

    @PostMapping("/messages")
    public ResponseEntity<MessageNegociation> saveMessage(@RequestBody MessageNegociation message) {
        return ResponseEntity.ok(negociationService.saveMessage(message));
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteNegociation(@PathVariable java.util.UUID id) {
        negociationService.deleteNegociation(id);
        return ResponseEntity.noContent().build();
    }
}
