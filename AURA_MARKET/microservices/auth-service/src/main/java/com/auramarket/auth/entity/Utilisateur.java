package com.auramarket.auth.entity;

import jakarta.persistence.*;
import java.util.UUID;

@Entity
@Inheritance(strategy = InheritanceType.JOINED)
@Table(name = "utilisateurs")
public class Utilisateur {
    
    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;
    
    @Column(unique = true, nullable = false)
    private String email;
    
    @Column(nullable = false)
    private String mdpHash;
    
    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private Role role;

    public Utilisateur() {}

    public Utilisateur(String email, String mdpHash, Role role) {
        this.email = email;
        this.mdpHash = mdpHash;
        this.role = role;
    }

    public UUID getId() { return id; }
    public void setId(UUID id) { this.id = id; }
    public String getEmail() { return email; }
    public void setEmail(String email) { this.email = email; }
    public String getMdpHash() { return mdpHash; }
    public void setMdpHash(String mdpHash) { this.mdpHash = mdpHash; }
    public Role getRole() { return role; }
    public void setRole(Role role) { this.role = role; }
}
