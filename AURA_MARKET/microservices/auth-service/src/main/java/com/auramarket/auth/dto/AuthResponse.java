package com.auramarket.auth.dto;

import java.util.UUID;

public class AuthResponse {
    private String token;
    private String role;
    private UUID id;

    public AuthResponse(String token, String role, UUID id) {
        this.token = token;
        this.role = role;
        this.id = id;
    }

    public String getToken() { return token; }
    public String getRole() { return role; }
    public UUID getId() { return id; }
}
