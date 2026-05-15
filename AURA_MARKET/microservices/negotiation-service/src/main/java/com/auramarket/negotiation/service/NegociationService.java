package com.auramarket.negotiation.service;

import com.auramarket.negotiation.entity.Negociation;
import com.auramarket.negotiation.entity.MessageNegociation;
import com.auramarket.negotiation.repository.NegociationRepository;
import com.auramarket.negotiation.repository.MessageNegociationRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.UUID;

@Service
public class NegociationService {

    @Autowired
    private NegociationRepository negociationRepository;

    @Autowired
    private MessageNegociationRepository messageRepository;

    public List<Negociation> getAllNegociations() {
        return negociationRepository.findAll();
    }

    public List<MessageNegociation> getMessages(UUID negociationId) {
        return messageRepository.findByNegociationIdOrderByTimestampAsc(negociationId);
    }

    public List<Negociation> getNegociationsByVendeurId(UUID vendeurId) {
        return negociationRepository.findByVendeurId(vendeurId);
    }

    public Negociation createNegociation(Negociation negociation) {
        Negociation saved = negociationRepository.save(negociation);
        messageRepository.save(new MessageNegociation(
            saved.getId(), 
            "SYSTEM", 
            "La négociation a commencé.", 
            saved.getPrixFinal() != null ? saved.getPrixFinal() : 0.0
        ));
        return saved;
    }

    public Negociation acceptNegociation(UUID id, double acceptedPrice) {
        Negociation n = negociationRepository.findById(id).orElseThrow(() -> new RuntimeException("Negotiation not found"));
        n.setStatus("ACCEPTED");
        n.setPrixFinal(acceptedPrice);
        negociationRepository.save(n);
        
        messageRepository.save(new MessageNegociation(
            n.getId(), 
            "SYSTEM", 
            "🎉 Le vendeur a accepté l'offre de " + acceptedPrice + " MAD.", 
            acceptedPrice
        ));
        return n;
    }

    public MessageNegociation saveMessage(MessageNegociation message) {
        negociationRepository.findById(message.getNegociationId()).ifPresent(n -> {
            if ("ACHETEUR".equals(message.getSender())) {
                n.setRounds(n.getRounds() + 1);
            }
            if (message.getPrice() > 0) {
                n.setPrixFinal(message.getPrice());
            }
            negociationRepository.save(n);
        });
        return messageRepository.save(message);
    }

    public void deleteNegociation(java.util.UUID id) {
        messageRepository.deleteByNegociationId(id);
        negociationRepository.deleteById(id);
    }
}
