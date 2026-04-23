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

    public Negociation createNegociation(Negociation negociation) {
        Negociation saved = negociationRepository.save(negociation);
        // Initial message from agent
        messageRepository.save(new MessageNegociation(
            saved.getId(), 
            "AGENT", 
            "Bonjour ! Je suis l'agent en charge de ce produit. Quel prix souhaiteriez-vous proposer ?", 
            saved.getPrixFinal()
        ));
        return saved;
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
