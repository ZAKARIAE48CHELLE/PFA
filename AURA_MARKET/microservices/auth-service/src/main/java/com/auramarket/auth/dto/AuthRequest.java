package com.auramarket.auth.dto;

public class AuthRequest {
    private String email;
    private String mdp;

    public String getEmail() { return email; }
    public void setEmail(String email) { this.email = email; }
    public String getMdp() { return mdp; }
    public void setMdp(String mdp) { this.mdp = mdp; }
}
