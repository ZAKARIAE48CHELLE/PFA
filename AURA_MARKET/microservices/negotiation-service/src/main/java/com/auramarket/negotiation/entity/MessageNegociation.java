package com.auramarket.negotiation.entity;

import jakarta.persistence.*;
import java.time.LocalDateTime;
import java.util.UUID;

@Entity
@Table(name = "messages_negociation")
public class MessageNegociation {
    
    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;
    
    private UUID negociationId;
    private String sender; // "ACHETEUR" or "AGENT"
    private String content;
    private double price;
    private LocalDateTime timestamp;

    public MessageNegociation() {
        this.timestamp = LocalDateTime.now();
    }

    public MessageNegociation(UUID negociationId, String sender, String content, double price) {
        this();
        this.negociationId = negociationId;
        this.sender = sender;
        this.content = content;
        this.price = price;
    }

    // Getters and Setters
    public UUID getId() { return id; }
    public void setId(UUID id) { this.id = id; }
    public UUID getNegociationId() { return negociationId; }
    public void setNegociationId(UUID negociationId) { this.negociationId = negociationId; }
    public String getSender() { return sender; }
    public void setSender(String sender) { this.sender = sender; }
    public String getContent() { return content; }
    public void setContent(String content) { this.content = content; }
    public double getPrice() { return price; }
    public void setPrice(double price) { this.price = price; }
    public LocalDateTime getTimestamp() { return timestamp; }
    public void setTimestamp(LocalDateTime timestamp) { this.timestamp = timestamp; }
}
