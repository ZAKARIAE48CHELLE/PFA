package com.auramarket.audit.entity;

import jakarta.persistence.*;
import java.util.UUID;

@Entity
@Table(name = "audits")
public class Audit {
    
    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;
    
    private String type;
    
    @Enumerated(EnumType.STRING)
    private Severite severite;
    
    private String message;
    private String agentSource;

    public enum Severite { INFO, WARNING, CRITICAL }

    public Audit() {}

    public UUID getId() { return id; }
    public void setId(UUID id) { this.id = id; }
    public String getType() { return type; }
    public void setType(String type) { this.type = type; }
    public Severite getSeverite() { return severite; }
    public void setSeverite(Severite severite) { this.severite = severite; }
    public String getMessage() { return message; }
    public void setMessage(String message) { this.message = message; }
    public String getAgentSource() { return agentSource; }
    public void setAgentSource(String agentSource) { this.agentSource = agentSource; }
}
